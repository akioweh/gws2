"""
General-purpose Web Server 2 (gws2)

Aksite @ akioweh.com
"""

__author__ = 'akioweh'
__all__ = ['run', 'app', 'parse_cmdline_args', 'run_https_redirect', 'https_redirect_app', 'run_async',
           'run_https_redirect_async']

from .httpsredirect import app as https_redirect_app, bind_to as run_https_redirect, \
    bind_to_async as run_https_redirect_async
from .main import app
from .run import parse_cmdline_args, run, run_async
