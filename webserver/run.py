"""
Run the webserver.
This file should be able to run the webserver from anywhere (any cwd).
Alternatively, run run_server.py (in the parent (project) directory).

To execute directly from the terminal, use uvicorn::

    $ uvicorn webserver:app

from the project root directory.
"""

import argparse
from os.path import abspath, dirname, join as path_join

import uvicorn

__all__ = ['run', 'parse_args']


def run(port: int = 8000, host: str = '0.0.0.0', working_dir: str = None, reload: bool = False):
    """Runs the webserver.
    ``working_dir`` shouldn't ever need setting.
    """
    if port is None:
        port = 8000
    if host is None:
        host = '127.0.0.1'
    uvicorn.run(
        'webserver:app',
        host=host,
        port=port,
        reload=reload,
        log_level='debug',
        loop='asyncio',
        app_dir=working_dir,
        reload_dirs=abspath(dirname(__file__)),
        reload_excludes=[
            'files/'
        ]  # changes to resources should not trigger a reload
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, help='Host address to run the server on.')
    parser.add_argument('-p', '--port', type=int, help='Port number to run the server on.')
    parser.add_argument('-r', '--reload', action='store_true', help='Enable auto-reload.')
    return parser.parse_args()


if __name__ == '__main__':
    print('Direct execution of ``run.py`` in webserver package.')
    # in order for Python's relative imports to work, we need to set the working directory
    # to the project root directory (the directory containing the webserver package)
    target_cwd = abspath(path_join(dirname(__file__), '..'))
    args = parse_args()
    run(port=args.port, host=args.host, working_dir=target_cwd, reload=args.reload)

    input('Press enter to exit')
