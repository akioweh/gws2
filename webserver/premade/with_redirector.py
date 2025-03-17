"""
Premade, importable app instance
with builtin HTTP->HTTPS redirection.
"""

__all__ = ['app']

from webserver.main import create_app

app = create_app(redirect_insecure=True)
