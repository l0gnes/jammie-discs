from fastapi.routing import APIRouter
from fastapi.responses import StreamingResponse
from os import getenv
from io import BytesIO
import cachetools

from src.lib.lastfm import get_recently_played_songs
from src.lib.images import generate_disk_frames, generate_now_playing_image

router = APIRouter(prefix="/images", tags=["images"])

song_cache = cachetools.TTLCache(maxsize=1, ttl=10.0)

@router.get("/current")
async def get_current_playing_song_image() -> StreamingResponse:
    """Generates an image and returns it"""

    username, api_key = getenv("LASTFM_USERNAME"), getenv("LASTFM_API_KEY")

    if username is None or api_key is None:
        raise Exception("You forgot to set your environment variables")

    global song_cache

    cached_song = song_cache.get("song")

    if cached_song is None:
        recently_played_song = get_recently_played_songs(username, api_key)

        song_cache["song"] = recently_played_song[0]
        cached_song = recently_played_song[0]

    disk_frames = generate_now_playing_image(
        frame_count = 32,
        song = cached_song
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

    return StreamingResponse(
        content=out_bytes,
        media_type="image/gif"
    )
