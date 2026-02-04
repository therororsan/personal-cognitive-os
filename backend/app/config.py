from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    pcos_env: str = "dev"
    dev_only_bootstrap: bool = False
    database_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
