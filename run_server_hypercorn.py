import asyncio
import signal
from argparse import Namespace

import hypercorn
from hypercorn.asyncio import serve

from webserver import parse_cmdline_args, create_app


def runner(args: Namespace):
    conf = hypercorn.Config()
    conf.bind = f'{args.host}:{args.port}'
    conf.bind.append(f'{args.host}:80')
    conf.certfile = args.certfile
    conf.keyfile = args.keyfile
    conf.reload = args.reload
    conf.graceful_timeout = 0
    conf.accesslog = '-'
    if args.ssl:
        # conf.insecure_bind = f'{args.host}:80'
        conf.alpn_protocols.append('h3')
        conf.quic_bind = conf.bind.copy()

    async def serve_all():
        signal_event = asyncio.Event()

        def _sig_handler(*_):
            print('Shutdown signal received')
            signal_event.set()

        for sig in ('SIGINT', 'SIGTERM', 'SIGBREAK'):
            if (sig_id := getattr(signal, sig, None)) is None:
                continue
            try:
                # noinspection PyTypeChecker
                asyncio.get_running_loop().add_signal_handler(
                    sig_id, _sig_handler)
            except NotImplementedError:
                # Windows crap
                signal.signal(sig_id, _sig_handler)

        # noinspection PyTypeChecker
        await serve(create_app(args.ssl), conf, shutdown_trigger=signal_event.wait)

    asyncio.new_event_loop().run_until_complete(serve_all())


if __name__ == '__main__':
    args_ = parse_cmdline_args()
    runner(args_)
