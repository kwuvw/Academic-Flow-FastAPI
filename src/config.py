from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Academic Flow"
    DEBUG: bool = True
    
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/Academic-flow-FASTAPI"
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"  # Можно задать дефолтное значение
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Тоже задаем дефолтное значение
    
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

settings = Settings()