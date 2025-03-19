"""
Custom mountable FastAPI app based on Starlette's StaticFiles
that auto-generates directory listings and does some other simple stuff.

It strips .htm(l) file extensions,
renders Markdown as HTML,
and allows access to files without their extensions in the URL.
"""

__all__ = ['StaticDir']

import asyncio
import os
import posixpath
import stat
import urllib.parse
from collections.abc import Sequence, Callable
from email.utils import parsedate
from os import PathLike
from pathlib import Path
from typing import Final, AnyStr

import mistletoe
from fastapi import HTTPException
from fastapi.templating import Jinja2Templates
from starlette.datastructures import Headers, URL
from starlette.requests import Request
from starlette.responses import FileResponse, Response, HTMLResponse, RedirectResponse
from starlette.staticfiles import NotModifiedResponse
from starlette.types import Scope, Receive, Send


class StaticDir:
    _DEFAULT_IMPLICIT_EXTS: Final[tuple[str]] = (
        # basic text markup
        '.html', '.htm', '.txt', '.md',
        # Office files
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        # other documents
        '.pdf', '.csv', '.json', '.xml', '.yaml', '.yml',
        # images
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.bmp', '.webp', '.tif', '.tiff', '.dng',
        # audio
        '.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma', '.m4a', '.aiff', '.ape', '.alac',
        # video
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.vob', '.ogv', '.3gp', '.3g2', '.m4v',
        # archives
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.lz', '.lzma', '.lzo', '.zst', '.zstd',
    )

    @staticmethod
    def _default_hidden_predicate(item: os.DirEntry[str]) -> bool:
        """Predicate to whether an FS object should be shown in directory listings."""
        if not (item.is_file() or item.is_dir()):
            return True  # hide non-standard FS objects
        if item.name.startswith('.') and not (item.is_dir() and item.name == '.well-known'):
            return True  # hide dotted dirs/files (except .well-known dirs)
        if item.is_dir() and (item.name.endswith('_files') or os.path.isfile(os.path.join(item.path, '.nolist'))):
            return True  # hide dirs with a ".nolist" file in them
        return False

    def __init__(
            self,
            directory: PathLike[AnyStr] | str,
            list_dirs: bool = True,
            listing_template_dir: PathLike[AnyStr] | str = None,
            listing_template_file: PathLike[AnyStr] | str = 'list_dir.html',
            implicit_exts: Sequence[str] = _DEFAULT_IMPLICIT_EXTS,
            hidden_predicate: Callable[[os.DirEntry[str]], bool] = _default_hidden_predicate,
    ):
        directory = os.path.realpath(os.path.abspath(directory))
        listing_template_file = str(listing_template_file)
        if not os.path.isdir(directory):
            raise FileNotFoundError(f'"{directory}" does not exist or is not a directory')
        if listing_template_dir is None:
            listing_template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        if not os.path.isfile(os.path.join(listing_template_dir, listing_template_file)):
            raise FileNotFoundError(f'Template file "{listing_template_file}" not found in "{listing_template_dir}"')
        self.root_dir = Path(directory)
        self.list_dirs = list_dirs
        self.implicit_exts = implicit_exts
        self.templates = Jinja2Templates(listing_template_dir)
        self.template_file = listing_template_file
        self.should_hide = hidden_predicate

    @staticmethod
    def convert_path(scope: Scope) -> str:
        """Converts an HTTP path from the ASGI scope to a relative API path"""
        path: str = scope['path']
        root = scope.get('root_path', '')
        if not root.endswith('/'):
            root += '/'
        assert path.startswith(root)  # should not happen if routing is correct
        rel_path = path[len(root):]
        return rel_path

    def resolve_path(self, rel_path: str) -> tuple[Path, os.stat_result] | tuple[None, None]:
        """Resolves a relative API path to an absolute OS FS path
        while also checking for existence and legality.

        Returns ``pathlib.Path`` and ``os.stat_result``, or two Nones if resolution failed.
        """
        if rel_path.startswith('/'):
            return None, None  # happens if request is like "GET //"
        abs_path = self.root_dir / rel_path
        try:
            path = abs_path.resolve()
            # first, check for existence
            if not path.exists() and not rel_path.endswith('/'):  # could still be valid if extension is implicit
                parent_dir = path.parent
                if not parent_dir.is_dir():
                    return None, None
                # prioritize checking for .html files
                if os.path.isfile(path.with_suffix('.html')):
                    path = path.with_suffix('.html')
                elif os.path.isfile(path.with_suffix('.htm')):
                    path = path.with_suffix('.htm')
                else:
                    base_name = path.name
                    for candidate in parent_dir.glob(f'{base_name}.*', case_sensitive=True):
                        if candidate.suffix in self.implicit_exts:
                            path = candidate
                            break
            stat_result = path.lstat()
        except (PermissionError, FileNotFoundError, OSError):
            return None, None
        # then, check for legality
        if not path.is_relative_to(self.root_dir):
            return None, None  # directory traversal!
        return path, stat_result

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive, send)
        rel_path = self.convert_path(scope)
        response = await self.handle_request(rel_path, request)
        await response(scope, receive, send)

    async def handle_request(self, rel_path: str, request: Request) -> Response:
        if request.method not in ('GET', 'HEAD'):
            raise HTTPException(status_code=405)
        path, stat_result = self.resolve_path(rel_path)
        if stat_result is None:
            return self.get_response_404()

        if stat.S_ISREG(stat_result.st_mode):
            return await self.get_response_file(path, stat_result, request)
        elif stat.S_ISDIR(stat_result.st_mode):
            if not self.list_dirs:
                return self.get_response_404()
            if rel_path and not rel_path.endswith('/'):  # directory URLs should redirect to always end in "/"
                url = URL(scope=request.scope)
                url = url.replace(path=url.path + '/')
                return RedirectResponse(url=url)
            return await self.get_response_dir(path, rel_path, request)
        else:
            raise RuntimeError('wtf')

    async def get_response_file(self, path: Path, stat_result: os.stat_result, request: Request) -> Response:
        if path.suffix == '.md':
            rendered = mistletoe.markdown(path.read_text())  # todo: cache rendered HTML
            return HTMLResponse(rendered)
        response = FileResponse(path, stat_result=stat_result)
        if self.is_not_modified(request.headers, response.headers):
            return NotModifiedResponse(response.headers)
        if (assets_dir := path.parent / (path.stem + '_files')).is_dir():
            await self.push_asset_dir(assets_dir, request)
        return response

    async def get_response_dir(self, path: Path, rel_path: str, request: Request) -> Response:
        # check if we have 'index.html' file to serve
        index_path = path / 'index.html'
        if index_path.is_file():
            return await self.get_response_file(index_path, index_path.stat(), request)

        # otherwise, list the directory
        # list[tuple[link, display_name]]
        listing = [('../', '../')]  # always include a link to the parent directory
        for item in os.scandir(path):
            if self.should_hide(item):
                continue
            file_name = item.name
            if item.is_dir():
                file_name += '/'
            else:
                file_name = file_name.removesuffix('.html').removesuffix('.htm')
            file_url = urllib.parse.quote(file_name)
            listing.append((file_url, file_name))

        return self.templates.TemplateResponse(
            request,
            self.template_file,
            {
                'title': f'Things in {rel_path}',
                'files': listing,
            }
        )

    def get_response_404(self) -> Response:
        path = self.root_dir / '404.html'
        try:
            stat_result = path.stat()
        except (FileNotFoundError, PermissionError, OSError):
            pass
        else:
            if stat.S_ISREG(stat_result.st_mode):
                return FileResponse(path, stat_result=stat_result, status_code=404)
        raise HTTPException(status_code=404)

    async def push_asset_dir(self, dir_path: Path, request: Request) -> None:
        # i am probably doing this horribly wrong
        if 'http.response.push' not in request.scope.get('extensions', ()):
            return
        assert dir_path.is_dir()
        rel_path = dir_path.relative_to(self.root_dir).as_posix()
        rel_path = posixpath.join('/', request.scope['root_path'], rel_path)
        paths = (f'{rel_path}/{item}' for item in os.listdir(dir_path))
        promises = (request.send_push_promise(path) for path in paths)
        await asyncio.gather(*promises)

    @staticmethod
    def is_not_modified(request_headers: Headers, response_headers: Headers) -> bool:
        # etag matching
        if (reqs_etag_header := request_headers.get('If-None-Match')) is None:
            return False
        if (etag := response_headers.get('ETag')) is None:
            return False
        etag = etag.strip()
        match_etags = (tag.strip() for tag in reqs_etag_header.lstrip('W/ ').split(','))
        if any(tag == etag for tag in match_etags):
            return True

        # modification timestamp check
        if_modified_since = parsedate(request_headers.get('If-Modified-Since'))
        last_modified = parsedate(response_headers.get('Last-Modified'))
        if (if_modified_since and last_modified) and if_modified_since >= last_modified:
            return True

        return False
