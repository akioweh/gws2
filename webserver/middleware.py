__all__ = ['ServerTimingMiddleware', 'HTTPSRedirectMiddleware']

import time
from collections.abc import Awaitable

# noinspection PyProtectedMember
from starlette.middleware import _MiddlewareFactory
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.types import Scope, Receive, Send, Message, ASGIApp

# we gotta do this because either I or the type checker is absolutely useless
# basically, without this abomination of type "hinting" (more like smashing than hinting)
# we get type errors when these classes are passed into app.add_middleware()... :(
# noinspection PyTypeChecker
HTTPSRedirectMiddleware: _MiddlewareFactory = HTTPSRedirectMiddleware
ServerTimingMiddleware: _MiddlewareFactory


class ServerTimingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        def wrapped_send(message: Message) -> Awaitable[None]:
            if message['type'] == 'http.response.start':
                elapsed = (time.perf_counter_ns() - start) / 1_000_000_000
                message['headers'].append((b'X-Server-Time', str(elapsed).encode()))
            return send(message)

        start = time.perf_counter_ns()
        await self.app(scope, receive, wrapped_send)
