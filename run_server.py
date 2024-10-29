"""
Start the server.
"""

from webserver import parse_args, run

if __name__ == '__main__':
    args = parse_args()
    if args.host is None:
        args.host = '0.0.0.0'
    if args.port is None:
        args.port = 443 if args.certfile else 80
    run(port=args.port, host=args.host, reload=args.reload, keyfile=args.keyfile, certfile=args.certfile)
