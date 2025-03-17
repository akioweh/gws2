import asyncio
import signal
from argparse import Namespace

from webserver import parse_cli_args


def main(args: Namespace):
    import uvicorn

    conf = uvicorn.Config(
        'webserver.premade.regular:app',
        host=args.host,
        port=args.port,
        ssl_keyfile=args.keyfile,
        ssl_certfile=args.certfile,
        log_level='debug',
        reload=args.reload,
        reload_dirs=['webserver'],
        reload_excludes=['files'],
        timeout_graceful_shutdown=1
    )

    servers = [uvicorn.Server(conf)]
    if args.ssl:
        conf2 = uvicorn.Config(
            'webserver.premade.only_redirector:app',
            host=args.host,
            port=80,
            log_level='debug',
            timeout_graceful_shutdown=1
        )
        servers.append(uvicorn.Server(conf2))

    async def serve_all():
        await asyncio.gather(*(server.serve() for server in servers))

    asyncio.new_event_loop().run_until_complete(serve_all())


if __name__ == '__main__':
    args_ = parse_cli_args()
    # uvicorn itself explicitly captures termination signals...
    # except it raises them again so we get KeyboardInterrupt on exit without this
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    main(args_)
