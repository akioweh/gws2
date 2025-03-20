__all__ = ['create_app']

from fastapi import FastAPI

from .middleware import ServerTimingMiddleware, HTTPSRedirectMiddleware
from .staticdir import StaticDir


def create_app(redirect_insecure: bool = True) -> FastAPI:
    """We use an app "factory" instead of a standard
    module-level variable because we need to control
    whether the ``HTTPSRedirectMiddleware`` is added
    to our app depending on external factors.
    """

    app = FastAPI()

    if redirect_insecure:
        app.add_middleware(HTTPSRedirectMiddleware)

    app.add_middleware(ServerTimingMiddleware)

    app.mount('/', StaticDir(directory='files'), name='root')

    return app
