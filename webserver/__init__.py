"""
General-purpose Web Server 2 (gws2)

Aksite @ akioweh.com
"""

__author__ = 'akioweh'
__all__ = ['create_app', 'parse_cmdline_args', 'run', 'run_async']

from .main import create_app
from .run import parse_cmdline_args, run, run_async
