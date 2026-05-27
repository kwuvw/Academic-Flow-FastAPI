from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Academic Flow"
    DEBUG: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()