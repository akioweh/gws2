"""
FastAPI mount that has a set response
for all endpoints and requests.
"""

class NullRouter:
    """A FastAPI mount that has a set static response for all endpoints and requests."""

    def __init__(self, response: str = ''):
        self.response = response

    async def __call__(self, scope, receive, send):
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/html'],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': self.response.encode(),
        })
