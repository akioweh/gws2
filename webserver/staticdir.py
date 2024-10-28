"""
Custom mountable FastAPI app based on Starlette's StaticFiles
that auto-generates directory listings and strips file extensions from URLs.

E.g., if a file is named `example.html`, it can be accessed via ``/example``.
`folder/document.pdf` can be accessed via ``/folder/document``.
"""
import errno
import os
import stat
import urllib.parse

import anyio
import anyio.to_thread
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles as _StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import URL
from starlette.responses import FileResponse, RedirectResponse, Response
from starlette.staticfiles import PathLike
from starlette.types import Scope


class StaticDir(_StaticFiles):
    _ALLOWED_EXTS = [  # basic text markup
        '.html', '.htm', '.txt', '.md',
    ]
    _ALLOWED_EXTS.extend([  # Office files
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    ])
    _ALLOWED_EXTS.extend([  # other documents
        '.pdf', '.csv', '.json', '.xml', '.yaml', '.yml',
    ])
    _ALLOWED_EXTS.extend([  # images
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.bmp', '.webp', '.tif', '.tiff', '.dng',
    ])
    _ALLOWED_EXTS.extend([  # audio
        '.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma', '.m4a', '.aiff', '.ape', '.alac',
    ])
    _ALLOWED_EXTS.extend([  # video
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.vob', '.ogv', '.3gp', '.3g2', '.m4v',
    ])
    _ALLOWED_EXTS.extend([  # archives
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.lz', '.lzma', '.lzo', '.zst', '.zstd',
    ])

    @staticmethod
    def _default_hidden_predicate(file: str) -> bool:
        # hide files and directories starting with a dot
        if file.startswith('.'):
            return True
        # hide directories ending with '_files'
        if os.path.isdir(file) and file.endswith('_files'):
            return True
        # hide directories with a '.nolist' file inside
        if os.path.isdir(file) and os.path.isfile(os.path.join(file, '.nolist')):
            return True
        return False

    def __init__(
            self,
            directory: str,
            list_dirs: bool = True,
            template_dir: str = None,
            template: str = 'list_dir.html',
            allowed_exts: list[str] = None,
            hidden_predicate: callable = _default_hidden_predicate,
            **kwargs
    ):
        if kwargs.get('html', None) is not None:
            raise ValueError('StaticDir does not support the "html" argument. (It is always True)')
        if kwargs.get('packages', None) is not None:
            raise ValueError('StaticDir does not support the "packages" argument. It only works with a single directory.')
        super().__init__(directory=directory, html=True, **kwargs)

        self.list_dirs = list_dirs
        self.allowed_exts = allowed_exts or self._ALLOWED_EXTS.copy()
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.templates = Jinja2Templates(directory=template_dir)
        self.template_file = template
        self.should_hide = hidden_predicate
        # check if the template file exists
        if not os.path.exists(os.path.join(template_dir, template)):
            raise FileNotFoundError(f'Template file "{template}" not found in "{template_dir}"')

    def get_directories(
        self,
        directory: PathLike | None = None,
        packages: list[str | tuple[str, str]] | None = None,
    ) -> list[PathLike]:
        # overridden to return only the one main directory
        return [directory]

    def get_path(self, scope: Scope) -> str:
        # overridden to preserve trailing slashes
        route_path = scope['path']
        cleaned = os.path.normpath(os.path.join('', *route_path.split('/')))
        if route_path.endswith('/'):
            cleaned += '/'
        return cleaned

    async def get_response(self, path: str, scope: Scope) -> Response:
        # overridden to handle directory listings

        if scope['method'] not in ('GET', 'HEAD'):
            raise HTTPException(status_code=405)

        try:
            full_path, stat_result = await anyio.to_thread.run_sync(self.lookup_path, path)
        except PermissionError:
            raise HTTPException(status_code=401)
        except OSError as exc:
            # Filename is too long, so it can't be a valid static file.
            if exc.errno == errno.ENAMETOOLONG:
                raise HTTPException(status_code=404)
            # uh oh
            raise exc

        # file
        if stat_result is not None and stat.S_ISREG(stat_result.st_mode):
            return self.file_response(full_path, stat_result, scope)

        # directory
        elif stat_result is not None and stat.S_ISDIR(stat_result.st_mode):
            if not scope['path'].endswith('/'):
                # Directory URLs should redirect to always end in "/".
                url = URL(scope=scope)
                url = url.replace(path=url.path + '/')
                return RedirectResponse(url=url)

            # Check if we have 'index.html' file to serve.
            index_path = os.path.join(path, 'index.html')
            _full_path, _stat_result = await anyio.to_thread.run_sync(self.lookup_path, index_path)
            if _stat_result is not None and stat.S_ISREG(_stat_result.st_mode):
                return self.file_response(_full_path, _stat_result, scope)

            # time to list the directory
            dirlist = os.listdir(full_path)
            dirlist.sort()
            dirlist = filter(lambda x: not self.should_hide(os.path.join(full_path, x)), dirlist)

            files_to_list = [('../', '../')]  # always include a link to the parent directory
            for file_name in dirlist:
                file_url = file_name  # can just do this and have browsers handle relative paths
                if os.path.isdir(file_url):
                    file_url += '/'
                    file_name += '/'
                else:
                    # strip html/htm extension
                    for ext in ['.html', '.htm']:
                        if file_name.endswith(ext):
                            file_name = file_name[:-len(ext)]
                            file_url = file_url[:-len(ext)]
                            break
                file_url = urllib.parse.quote(file_url)  # escape special characters in URLs
                files_to_list.append((file_url, file_name))

            return self.templates.TemplateResponse(
                self.template_file,
                {
                    'request': scope,
                    'title': f'Things in {path.replace("\\", "/",)}',
                    'files': files_to_list,
                }
            )

        # not found
        full_path, stat_result = await anyio.to_thread.run_sync(self.lookup_path, '404.html')
        if stat_result is not None and stat.S_ISREG(stat_result.st_mode):
            return FileResponse(full_path, stat_result=stat_result, status_code=404)
        raise HTTPException(status_code=404)

    def lookup_path(self, path: str) -> tuple[str, os.stat_result | None]:
        """Given an API-friendly path, return the full OS FS path
        to the target static file and its stat result.

        Returns an empty string and None if the file is not found.
        """
        joined_path = os.path.join(self.directory, path)
        if self.follow_symlink:
            full_path = os.path.abspath(joined_path)
        else:
            full_path = os.path.realpath(joined_path)
        directory = os.path.realpath(self.directory)
        if os.path.commonpath([full_path, directory]) != os.path.commonpath([directory]):
            return '', None  # prevent directory traversal

        # check if the path exists
        if os.path.exists(full_path):
            # directory
            if os.path.isdir(full_path):
                if self.should_hide(full_path):
                    return '', None  # hidden directory
                return full_path, os.stat(full_path, follow_symlinks=False)
            # explicit file
            return full_path, os.stat(full_path, follow_symlinks=False)

        elif not path.endswith('/'):  # slash-endings are reserved for directories
            # possible implicit file
            for ext in self.allowed_exts:
                if os.path.isfile(full_path + ext):
                    return full_path + ext, os.stat(full_path + ext, follow_symlinks=False)

        return '', None
