import time

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from .staticdir import StaticDir

app = FastAPI()

templates = Jinja2Templates(directory='templates')


@app.middleware('http')
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start
    response.headers['X-Process-Time'] = str(process_time)
    return response


app.mount('/', StaticDir(directory='files'), name='root')
