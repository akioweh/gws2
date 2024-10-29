"""
Start the server.
"""

from contextlib import suppress

from webserver import parse_cmdline_args, run, run_async, run_https_redirect_async


def run_https(host: str, port: int, *, keyfile: str, certfile: str, reload: bool = False):
    import asyncio
    import sys
    if 'win' in sys.platform:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def runner():
        loop = asyncio.get_event_loop()
        server = loop.create_task(run_async(host=host, port=port, keyfile=keyfile, certfile=certfile, reload=reload))
        redirector = loop.create_task(run_https_redirect_async(host, 80))
        await asyncio.gather(server, redirector)

    with suppress(KeyboardInterrupt, asyncio.CancelledError, SystemExit):
        asyncio.run(runner())


if __name__ == '__main__':
    args_ = parse_cmdline_args()
    https = False
    if args_.keyfile or args_.certfile:
        if not (args_.keyfile and args_.certfile):
            raise ValueError('Both keyfile and certfile must be provided to enable SSL.')
        https = True
    if args_.host is None:
        args_.host = '0.0.0.0'  # bind to all by default
    if args_.port is None:
        args_.port = 443 if https else 80  # nominal defaults

    if https:
        run_https(host=args_.host, port=args_.port, keyfile=args_.keyfile, certfile=args_.certfile, reload=args_.reload)
    else:
        run(port=args_.port, host=args_.host, reload=args_.reload, keyfile=args_.keyfile, certfile=args_.certfile)
