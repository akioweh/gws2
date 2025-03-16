"""
Run the webserver.
This file should be able to run the webserver from anywhere (any cwd).
Alternatively, run run_server.py (in the parent (project) directory).

To execute directly from the terminal, use uvicorn::

    $ uvicorn webserver:app

from the project root directory.
"""

__all__ = ['run', 'parse_cmdline_args', 'run_async']

import argparse
from os.path import abspath, dirname, join as path_join


def run(
        port: int = None,
        host: str = None,
        *,
        working_dir: str = None,
        reload: bool = False,
        keyfile: str = None,
        certfile: str = None,
):
    """Runs the webserver.

    ``host`` and ``port`` default to ``127.0.0.1:443``
    or ``0.0.0.0:80`` if SSL is not enabled.
    (``0.0.0.0`` is accessible from LAN/beyond while ``127.0.0.1`` is not.)

    ``working_dir`` shouldn't ever need setting.

    If both ``keyfile`` and ``certfile`` are provided,
    the server will run in HTTPS mode.
    Remember: port 80/8080 for HTTP, port 443/8443 for HTTPS.
    """

    import uvicorn

    if port is None:
        port = 443 if keyfile and certfile else 80
    if host is None:
        host = '127.0.0.1' if keyfile and certfile else '0.0.0.0'
    if keyfile or certfile and not (keyfile and certfile):
        raise ValueError('Both keyfile and certfile must be provided to enable SSL.')

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


async def run_async(
        port: int = None,
        host: str = None,
        *,
        reload: bool = False,
        keyfile: str = None,
        certfile: str = None,
):
    """Asynchronous version of ``run()``"""

    import uvicorn

    if port is None:
        port = 443 if keyfile and certfile else 80
    if host is None:
        host = '127.0.0.1' if keyfile and certfile else '0.0.0.0'
    if (keyfile or certfile) and not (keyfile and certfile):
        raise ValueError('Both keyfile and certfile must be provided to enable SSL.')

    config = uvicorn.Config(
        'webserver:app',
        host=host,
        port=port,
        reload=reload,
        log_level='debug',
        loop='asyncio',
        reload_dirs=abspath(dirname(__file__)),
        reload_excludes=['files/'],
        ssl_keyfile=keyfile,
        ssl_certfile=certfile,
    )
    server = uvicorn.Server(config)
    await server.serve()


def parse_cmdline_args():
    """Helper function to parse standard command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0', help='Host address to run the server on.')
    parser.add_argument('-p', '--port', type=int, help='Port number to run the server on.')
    parser.add_argument('-r', '--reload', action='store_true', help='Enable auto-reload.')
    parser.add_argument('--keyfile', help='SSL key file path.')
    parser.add_argument('--certfile', help='SSL certificate file path.')
    _args = parser.parse_args()
    if bool(_args.keyfile) != bool(_args.certfile):
        parser.error('Both keyfile and certfile must be provided to enable SSL.')
    _args.ssl = bool(_args.keyfile)
    if _args.port is None:
        _args.port = 443 if _args.ssl else 80  # nominal defaults
    return _args


if __name__ == '__main__':
    print('Direct execution of ``run.py`` in webserver package.')
    # in order for Python's relative imports to work, we need to set the working directory
    # to the project root directory (the directory containing the webserver package)
    target_cwd = abspath(path_join(dirname(__file__), '..'))
    args = parse_cmdline_args()
    run(port=args.port, host=args.host, working_dir=target_cwd, reload=args.reload,
        keyfile=args.keyfile, certfile=args.certfile)

    input('Press enter to exit')
