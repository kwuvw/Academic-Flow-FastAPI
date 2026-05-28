from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Academic Flow"
    DEBUG: bool = True
    
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/Academic-flow-FASTAPI"
    
    
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

settings = Settings()