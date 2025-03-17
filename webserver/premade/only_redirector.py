"""
Featureless, dedicated app instance
that redirects all HTTP traffic to HTTPS.
"""

from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()

# noinspection PyTypeChecker
app.add_middleware(HTTPSRedirectMiddleware)
