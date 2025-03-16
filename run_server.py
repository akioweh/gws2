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
    args = parse_cmdline_args()
    if args.ssl:
        run_https(host=args.host, port=args.port, keyfile=args.keyfile, certfile=args.certfile, reload=args.reload)
    else:
        run(port=args.port, host=args.host, reload=args.reload, keyfile=args.keyfile, certfile=args.certfile)
