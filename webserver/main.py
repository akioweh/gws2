import time

from fastapi import FastAPI, Request
from starlette.responses import RedirectResponse

from .staticdir import StaticDir

app = FastAPI()


@app.middleware('http')
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start
    response.headers['X-Process-Time'] = str(process_time)
    return response


@app.get('/theform')
async def the_form():
    return RedirectResponse(url='https://forms.gle/pMScdVjYBZZVKezC7')


app.mount('/', StaticDir(directory='files'), name='root')
