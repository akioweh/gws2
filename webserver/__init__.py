"""
General-purpose Web Server 2 (gws2)

Aksite @ akioweh.com
"""

__author__ = 'akioweh'

from .main import app
from .run import parse_args, run

__all__ = ['run', 'app', 'parse_args']
