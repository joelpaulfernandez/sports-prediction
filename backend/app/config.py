from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    sports_api_key: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    redis_url: str = "redis://localhost:6379"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = {"env_file": ".env", "case_sensitive": False}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
