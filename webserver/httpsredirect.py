"""
Used when running in HTTPS mode to
redirect all HTTP requests to HTTPS.
"""

__all__ = ['app', 'bind_to', 'bind_to_async']

import argparse

from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

from .nullrouter import NullRouter

app = FastAPI()

app.mount('/', NullRouter(), name='null-root')
# noinspection PyTypeChecker
app.add_middleware(HTTPSRedirectMiddleware)


def bind_to(host: str, port: int = 80):
    """Bind the redirector server to a host and port."""
    import uvicorn
    uvicorn.run(app, host=host, port=port, timeout_keep_alive=0)


async def bind_to_async(host: str, port: int = 80):
    """Bind the redirector server to a host and port.

    This is an async function that can be awaited.
    """
    import uvicorn
    config = uvicorn.Config(app, host=host, port=port, timeout_keep_alive=0)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, help='Host address to run the server on.')
    parser.add_argument('-p', '--port', type=int, help='Port number to run the server on.')
    args = parser.parse_args()

    host_ = args.host if args.host else '127.0.0.1'
    port_ = args.port if args.port else 80
    print(f'Redirecting HTTP to HTTPS on {host_}:{port_}')
    bind_to(host=host_, port=port_)

    input('Press enter to exit')
