import os
from functools import lru_cache
from pydantic_settings import BaseSettings

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class Settings(BaseSettings):
    sports_api_key: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    redis_url: str = "redis://localhost:6379"
    frontend_url: str = ""
    model_path: str = os.path.join(_DATA_DIR, "model.pkl")
    f1_admin_token: str = "f1-refresh"
    allowed_origin_regex: str = ""

    model_config = {"env_file": ".env", "case_sensitive": False}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
