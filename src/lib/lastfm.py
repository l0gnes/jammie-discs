from pydantic import BaseModel, Field
from datetime import datetime, UTC
import requests

class RecentlyPlayedSong(BaseModel):
    title: str
    artist: str
    is_now_playing: bool
    played_date: datetime
    cover_art: str

def get_recently_played_songs(
    username: str,
    api_key: str
) -> list[RecentlyPlayedSong]:
    
    with requests.get(
        "https://ws.audioscrobbler.com/2.0/",
        params={
            "user" : username,
            "api_key" : api_key,
            "format" : "json",
            "method" : "user.getrecenttracks",
            "limit" : 1
        }
    ) as resp:
        json_data = resp.json()

        if resp.status_code != 200:
            raise ValueError(f"Failed to retrieve recently played songs, got status code: {resp.status_code}")

    return [
        RecentlyPlayedSong(
            title=track["name"],
            artist=track["artist"]["#text"],
            is_now_playing=track.get("@attr", {}).get("nowplaying", None) == "true",
            played_date=track.get("date", {}).get("uts", datetime.now(tz=UTC)),
            cover_art=track["image"][-1]["#text"]
        )
        for track in json_data["recenttracks"]["track"]
    ]