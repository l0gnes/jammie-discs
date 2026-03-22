from fastapi.routing import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()

@router.get("/ping")
def get_ping() -> PlainTextResponse:
    return PlainTextResponse(
        content="ok",
        status_code = 200
    )