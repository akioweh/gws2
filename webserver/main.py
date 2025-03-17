__all__ = ['create_app']

import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from .staticdir import StaticDir


def create_app(redirect_insecure: bool = True) -> FastAPI:
    """We use an app "factory" instead of a standard
    module-level variable because we need to control
    whether the ``HTTPSRedirectMiddleware`` is added
    to our app depending on external factors.
    """

    app = FastAPI()

    if redirect_insecure:
        # noinspection PyTypeChecker
        app.add_middleware(HTTPSRedirectMiddleware)

    @app.middleware('http')
    async def add_process_time_header(request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start
        response.headers['X-Process-Time'] = str(process_time)
        return response

    app.mount('/', StaticDir(directory='files'), name='root')

    return app
