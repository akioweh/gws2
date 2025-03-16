import asyncio
import logging
import signal
from argparse import Namespace

import hypercorn
from hypercorn.asyncio import serve

from webserver import parse_cmdline_args, app, https_redirect_app


def runner(args: Namespace):
    conf = hypercorn.Config()
    conf.bind = f'{args.host}:{args.port}'
    conf.certfile = args.certfile
    conf.keyfile = args.keyfile
    conf.reload = args.reload
    if args.ssl:
        conf.alpn_protocols.append('h3')
        conf.alt_svc_headers.append('h3-29=":443", h3=":443", h2=":443"')
        conf.quic_bind = conf.bind

    conf2 = hypercorn.Config()
    conf2.bind = f'{args.host}:80'
    conf2.keep_alive_timeout = 0

    async def serve_all():
        signal_event = asyncio.Event()

        def _sig_handler(*_):
            print('Shutdown signal received')
            signal_event.set()

        for sig in ('SIGINT', 'SIGTERM', 'SIGBREAK'):
            if (sig_id := getattr(signal, sig, None)) is None:
                continue
            try:
                asyncio.get_running_loop().add_signal_handler(
                    sig_id, _sig_handler)
            except NotImplementedError:
                # Windows crap
                signal.signal(sig_id, _sig_handler)

        async with asyncio.TaskGroup() as tg:
            # noinspection PyTypeChecker
            tg.create_task(serve(app, conf, shutdown_trigger=signal_event.wait))
            if args.ssl:
                print('Running in HTTPS mode; HTTP -> HTTPS redirector started')
                # noinspection PyTypeChecker
                tg.create_task(serve(https_redirect_app, conf2, shutdown_trigger=signal_event.wait))

    asyncio.new_event_loop().run_until_complete(serve_all())


if __name__ == '__main__':
    args_ = parse_cmdline_args()
    logging.basicConfig(level=logging.INFO)
    runner(args_)
