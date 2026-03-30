from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.config import PROJECT_ROOT


class Settings(BaseSettings):
    # Notice: NO defaults. If these are missing in .env, the app will refuse to start.
    NOTION_TOKEN: str
    NOTION_DATABASE_ID: str
    NOTION_PARTICIPACIONES_DB_ID: str

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        extra="ignore"
    )


# Pydantic BaseSettings loads values from .env file automatically.
# Pyright doesn't understand this mechanism, hence the ignore.
settings = Settings()  # pyright: ignore[reportCallIssue]