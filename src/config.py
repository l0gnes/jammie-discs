from os import getenv
from typing import Literal

ACTIVE_CONFIG : "JammieDiscsConfig | None" = None

class JammieDiscsConfig(object):

    lastfm_api_key : str
    allowed_users : list[str] | Literal["*"]
    no_cache_control : bool

    default_theme : str

    @classmethod
    def from_env(cls) -> "JammieDiscsConfig":

        tmp = cls()

        is_api_key_set = getenv("LASTFM_API_KEY")

        if not is_api_key_set:
            raise ValueError("Missing LASTFM_API_KEY env variable")

        tmp.lastfm_api_key = is_api_key_set

        tmp.allowed_users = [u.lower() for u in getenv("LASTFM_ALLOWED_USERS", "").split(",")]
        tmp.default_theme = getenv("DEFAULT_THEME", "dark")
        tmp.no_cache_control = getenv("USE_NO_CACHE_HEADER", "false").lower() == "true"

        return tmp

    def is_user_allowed(self, username : str) -> bool:
        
        # If the allowed users key is set to "*", then allow all users
        if self.allowed_users == "*":
            return True
        
        # Otherwise, check the array
        return username.lower() in self.allowed_users
    
def get_config() -> JammieDiscsConfig:
    """Returns a reference to the app's config."""

    global ACTIVE_CONFIG

    if ACTIVE_CONFIG is None:
        ACTIVE_CONFIG = JammieDiscsConfig.from_env()

    return ACTIVE_CONFIG