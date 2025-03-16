"""
Run the webserver.
This file should be able to run the webserver from anywhere (any cwd).
"""

__all__ = ['run', 'parse_cmdline_args', 'run_async']

import argparse
from os.path import abspath, dirname

from webserver.main import create_app


def run(
        port: int = None,
        host: str = None,
        *,
        reload: bool = False,
        keyfile: str = None,
        certfile: str = None,
):
    """Runs the webserver with ``uvicorn``.

    ``host`` and ``port`` default to ``127.0.0.1:80``
    or ``0.0.0.0:443`` if SSL is enabled.

    If both ``keyfile`` and ``certfile`` are provided,
    the server will run with SSL in HTTPS mode.

    Note that ``uvicorn`` doesn't seem to support
    binding to more than one interface, so we actually
    cannot achieve HTTP -> HTTPS redirection with just
    one server instance.

    So...
    do port remapping on the OS/proxy/router/firewall level :)
    """

    import uvicorn

    if bool(certfile) != bool(certfile):
        raise ValueError('Both keyfile and certfile must be provided to enable SSL.')
    ssl = bool(keyfile)
    if port is None:
        port = 443 if ssl else 80
    if host is None:
        host = '0.0.0.0' if ssl else '127.0.0.1'

    uvicorn.run(
        create_app(ssl),
        host=host,
        port=port,
        reload=reload,
        log_level='debug',
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

    if bool(certfile) != bool(certfile):
        raise ValueError('Both keyfile and certfile must be provided to enable SSL.')
    ssl = bool(keyfile)
    if port is None:
        port = 443 if ssl else 80
    if host is None:
        host = '0.0.0.0' if ssl else '127.0.0.1'

    config = uvicorn.Config(
        create_app(ssl),
        host=host,
        port=port,
        reload=reload,
        log_level='debug',
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
    args = parse_cmdline_args()
    run(port=args.port, host=args.host, reload=args.reload, keyfile=args.keyfile, certfile=args.certfile)
