from fastapi import FastAPI
from dotenv import load_dotenv

from src.routes.images import router as images_router

load_dotenv()

app = FastAPI(
    title = "Jammie Discs"
)


app.include_router(images_router)