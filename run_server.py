"""
Start the server.
"""

from sys import argv

from webserver import run

if __name__ == '__main__':
    try:
        port = int(argv[1])
    except (IndexError, ValueError):
        port = 80
    run(port)
