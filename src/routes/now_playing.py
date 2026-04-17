from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Query
from fastapi.routing import APIRouter
from fastapi.responses import StreamingResponse
from io import BytesIO
import cachetools
from pydantic import BaseModel

from src.config import JammieDiscsConfig, get_config
from src.lib.themes import THEMES
from src.lib.lastfm import get_recently_played_songs
from src.lib.images import generate_now_playing_image

router = APIRouter(prefix="/now_playing", tags=["images"])

SONG_CACHE : dict[str, cachetools.TTLCache] = {}

def get_song_cache_for_user(user : str) -> cachetools.TTLCache:
    global SONG_CACHE

    if user not in SONG_CACHE:
        SONG_CACHE[user] = cachetools.TTLCache(maxsize=1, ttl=10.0)

    return SONG_CACHE[user]

class NowPlayingQueryParams(BaseModel):
    theme: str | None = None
    watermark_override : str | None = None

@router.get("/{username}.gif", operation_id="now_playing")
async def get_current_playing_song_image(
    config : Annotated[JammieDiscsConfig, Depends(get_config)],
    username : str,
    params : Annotated[NowPlayingQueryParams, Query()]
) -> StreamingResponse:
    """Generates an image and returns it"""

    is_user_allowed = config.is_user_allowed(username)

    if not is_user_allowed:
        raise HTTPException(
            status_code=403,
            detail = "You are not whitelisted on this jammie disc instance :("
        )

    theme = THEMES[params.theme or config.default_theme]

    song_cache = get_song_cache_for_user(user=username)

    cached_song = song_cache.get("song")

    if cached_song is None:
        recently_played_song = get_recently_played_songs(username, config.lastfm_api_key)

        song_cache["song"] = recently_played_song[0]
        cached_song = recently_played_song[0]

    disk_frames = generate_now_playing_image(
        frame_count = 32,
        song = cached_song,
        theme = theme,
        watermark_override = params.watermark_override
    )

    out_bytes = BytesIO()

    disk_frames[0].save(
        out_bytes,
        append_images=disk_frames[1:],
        save_all=True,
        format="gif",
        duration=120,
        loop=0,
        disposal=2,
        optimize=False
    )

    out_bytes.seek(0)


    headers = {}
    if config.no_cache_control:
        headers["cache-control"] = "no-cache"

    return StreamingResponse(
        content=out_bytes,
        media_type="image/gif",
        headers=headers
    )
