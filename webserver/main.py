from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()


@app.get("/")
async def home():
    return FileResponse("files/index.html")


app.mount("/shared/", StaticFiles(directory="files/shared"), name="files")
app.mount("/apps/", StaticFiles(directory="files/apps"), name="apps")
