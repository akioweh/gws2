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
from collections.abc import Sequence, Callable, Iterable
from contextlib import suppress
from email.utils import parsedate
from itertools import filterfalse
from os import PathLike
from pathlib import Path
from typing import Final, AnyStr

import mistletoe
from starlette.datastructures import Headers, URL
from starlette.exceptions import HTTPException
from starlette.requests import Request, SERVER_PUSH_HEADERS_TO_COPY
from starlette.responses import FileResponse, Response, HTMLResponse, RedirectResponse
from starlette.staticfiles import NotModifiedResponse
from starlette.templating import Jinja2Templates
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
    HTML_EXTENSIONS: Final[tuple[str]] = '.html', '.htm'

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
    def get_rel_path(scope: Scope) -> str:
        """Converts an HTTP path from the ASGI scope to a relative API path"""
        path: str = scope['path']
        root = scope.get('root_path', '')
        if not root.endswith('/'):
            root += '/'
        if not path.startswith(root):  # should not happen if routing is correct
            raise HTTPException(status_code=404)
        rel_path = path[len(root):]
        return rel_path

    def resolve_path(self, rel_path: str) -> tuple[Path, os.stat_result] | tuple[None, None]:
        """Resolves a relative API path to an absolute OS FS path
        while also checking for existence and legality.

        Returns ``pathlib.Path`` and ``os.stat_result``, or two Nones if resolution failed.
        """
        if rel_path.startswith('/'):
            return None, None  # happens if request is like "GET //..." and root is "/"
        raw_path = self.root_dir / rel_path

        try:  # 1:1 FS path matching
            path = raw_path.resolve(strict=True)
            stat_result = path.lstat()
        except (OSError, PermissionError, FileNotFoundError):
            # maybe extension is implicit?
            if not (name := rel_path.rpartition('/')[-1]):
                return None, None  # nope, slash-endings cannot be files
            if not (parent_dir := raw_path.parent).is_dir():
                return None, None  # nope, more than just the file does not resolve
            if any(  # check for .htm* files
                    (new_path := Path(parent_dir, f'{name}{ext}')).is_file()
                    for ext in self.HTML_EXTENSIONS
            ) or any(  # check for other implicit extensions
                (new_path := file).suffix in self.implicit_exts and file.is_file()
                for file in parent_dir.glob(f'{name}.*', case_sensitive=True)
            ):
                path = new_path
            else:
                return None, None
            stat_result = path.lstat()

        # finally, check for legality
        if not path.is_relative_to(self.root_dir):
            return None, None  # directory traversal!
        return path, stat_result

    def path_for(self, scope: Scope, fs_path: Path, trim_ext: bool = False) -> str:
        """Gets the absolute HTTP path for a given file.
        Assumes the input path is valid and exists.
        """
        api_root = scope.get('root_path', '')
        rel_path = fs_path.relative_to(self.root_dir).as_posix()
        if fs_path.suffix in self.HTML_EXTENSIONS or (trim_ext and fs_path.suffix in self.implicit_exts):
            rel_path = rel_path.removesuffix(fs_path.suffix)
        return posixpath.join('/', api_root, rel_path)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive, send)
        rel_path = self.get_rel_path(scope)
        response = self.handle_request(rel_path, request)
        await response(scope, receive, send)

    def handle_request(self, rel_path: str, request: Request) -> Response:
        if request.method not in ('GET', 'HEAD'):
            raise HTTPException(status_code=405)
        path, stat_result = self.resolve_path(rel_path)
        if stat_result is None:
            return self.get_response_404()

        if stat.S_ISREG(stat_result.st_mode):
            return self.get_response_file(path, stat_result, request)
        elif stat.S_ISDIR(stat_result.st_mode):
            if not self.list_dirs:
                return self.get_response_404()
            if rel_path and not rel_path.endswith('/'):  # directory URLs should redirect to always end in "/"
                url = URL(scope=request.scope)
                url = url.replace(path=url.path + '/')
                return RedirectResponse(url=url)
            return self.get_response_dir(path, rel_path, request)

        raise HTTPException(status_code=404)  # some other FS object

    def get_response_file(self, path: Path, stat_result: os.stat_result, request: Request) -> Response:
        if path.suffix == '.md':
            rendered = mistletoe.markdown(path.read_text())  # todo: cache rendered HTML
            return HTMLResponse(rendered)
        response = FileResponse(path, stat_result=stat_result)
        if self.is_not_modified(request.headers, response.headers):
            return NotModifiedResponse(response.headers)
        return response

    def get_response_dir(self, path: Path, rel_path: str, request: Request) -> Response:
        if any(  # check if we have 'index.htm?' file to serve
                (index_path := (path / f'index{ext}')).is_file()
                for ext in self.HTML_EXTENSIONS
        ):
            return self.get_response_file(index_path, index_path.stat(), request)

        # otherwise, list the directory
        # list[tuple[link, display_name]]
        listing = [('../', '../')]  # always include a link to the parent directory
        for item in filterfalse(self.should_hide, os.scandir(path)):
            file_name = item.name
            if item.is_dir():
                file_name += '/'
            elif any(file_name.endswith(ext := ext_) for ext_ in self.HTML_EXTENSIONS):
                file_name = file_name.removesuffix(ext)
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
        for ext in self.HTML_EXTENSIONS:
            path = self.root_dir / f'404{ext}'
            with suppress(FileNotFoundError, PermissionError, OSError):
                if stat.S_ISREG((stat_result := path.stat()).st_mode):
                    return FileResponse(path, stat_result=stat_result, status_code=404)
        raise HTTPException(status_code=404)

    async def push_assets(self, paths: Iterable[Path], scope: Scope, send: Send) -> None:
        urls = (self.path_for(scope, path) for path in paths)
        headers = Headers(scope=scope)
        headers_filtered = tuple(
            (k.encode('latin-1'), v.encode('latin-1'))
            for k in SERVER_PUSH_HEADERS_TO_COPY
            for v in headers.getlist(k)
        )
        promises = (send({'type': 'http.response.push', 'path': url, 'headers': headers_filtered}) for url in urls)
        await asyncio.gather(*promises)

    def asset_dependencies(self, path: Path, stat_result: os.stat_result) -> list[Path]:
        """Returns a list of asset dependencies for the given path, if any."""
        if not stat.S_ISREG(stat_result.st_mode) or path.suffix not in self.HTML_EXTENSIONS:
            return []
        # we only deal with HTML files
        # ...and for now we shortcut on MS-Office generated htm formats
        asset_dir = path.parent / (path.stem + '_files')
        try:
            return [asset_dir / item for item in os.listdir(asset_dir)]
        except (FileNotFoundError, PermissionError, OSError):
            return []

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
