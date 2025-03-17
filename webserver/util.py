__all__ = ['parse_cli_args']

from argparse import ArgumentParser, Namespace


def parse_cli_args() -> Namespace:
    """Helper function to parse standard command line arguments."""
    parser = ArgumentParser(prog='python -m webserver', description='gws2')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host address to run the server on. Default: %(default)s')
    parser.add_argument('-p', '--port', type=int,
                        help='Port number to run the server on. Default: 443 if SSL; else 80')
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
