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


def run(
        port: int = None,
        host: str = None,
        working_dir: str = None,
        reload: bool = False,
        keyfile: str = None,
        certfile: str = None,
):
    """Runs the webserver.
    ``working_dir`` shouldn't ever need setting.
    """
    if port is None:
        port = 443 if keyfile and certfile else 80
    if host is None:
        host = '127.0.0.1' if keyfile and certfile else '0.0.0.0'

    uvicorn.run(
        'webserver:app',
        host=host,
        port=port,
        reload=reload,
        log_level='debug',
        loop='asyncio',
        app_dir=working_dir,
        reload_dirs=abspath(dirname(__file__)),
        reload_excludes=['files/'],
        ssl_keyfile=keyfile,
        ssl_certfile=certfile,
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, help='Host address to run the server on.')
    parser.add_argument('-p', '--port', type=int, help='Port number to run the server on.')
    parser.add_argument('-r', '--reload', action='store_true', help='Enable auto-reload.')
    parser.add_argument('--keyfile', type=str, help='SSL key file path.')
    parser.add_argument('--certfile', type=str, help='SSL certificate file path.')
    parser.add_argument('--ssl', action='store_true', help='Enable SSL.')
    return parser.parse_args()


if __name__ == '__main__':
    print('Direct execution of ``run.py`` in webserver package.')
    # in order for Python's relative imports to work, we need to set the working directory
    # to the project root directory (the directory containing the webserver package)
    target_cwd = abspath(path_join(dirname(__file__), '..'))
    args = parse_args()
    run(port=args.port, host=args.host, working_dir=target_cwd, reload=args.reload,
        keyfile=args.keyfile, certfile=args.certfile)

    input('Press enter to exit')
