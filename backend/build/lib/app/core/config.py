from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Deepsight"
    database_url: str = "sqlite+aiosqlite:///./deepsight.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-only-secret"
    bootstrap_admin_email: str = "admin@deepsight.local"
    bootstrap_admin_password: str = "ChangeMe123!"
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
