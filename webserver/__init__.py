"""
General-purpose Web Server 2 (gws2)

Aksite @ akioweh.com
"""

__author__ = 'akioweh'
__all__ = ['create_app', 'parse_cli_args']

from .main import create_app
from .util import parse_cli_args
