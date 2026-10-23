from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    database_url: str = "sqlite:///./network_intent.db"
    api_key: str = "dev_api_key_123"
    admin_password: str = "admin"
    debug: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

def get_settings() -> Settings:
    return settings

