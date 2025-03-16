from . import parse_cmdline_args, run

args = parse_cmdline_args()
run(port=args.port, host=args.host, reload=args.reload, keyfile=args.keyfile, certfile=args.certfile)
