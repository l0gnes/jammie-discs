from fastapi import FastAPI
from dotenv import load_dotenv

from src.routes.now_playing import router as now_playing_router
from src.routes.ping import router as ping_router

load_dotenv()

app = FastAPI(
    title = "Jammie Discs"
)

app.include_router(now_playing_router)
app.include_router(ping_router)