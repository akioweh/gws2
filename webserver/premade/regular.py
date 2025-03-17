"""
Premade, importable app instance.
"""

__all__ = ['app']

from webserver.main import create_app

app = create_app(redirect_insecure=False)

