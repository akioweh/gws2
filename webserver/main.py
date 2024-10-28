import time

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()


@app.middleware('http')
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start
    response.headers['X-Process-Time'] = str(process_time)
    return response


@app.get('/')
async def home():
    return FileResponse('files/index.html')


@app.get('/favicon.ico')
async def favicon():
    return FileResponse('files/favicon.ico')


app.mount('/shared/', StaticFiles(directory='files/shared', html=True), name='files')
app.mount('/apps/', StaticFiles(directory='files/apps', html=True), name='apps')
