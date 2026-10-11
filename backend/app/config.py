from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///./network_intent.db"
    api_key: str = "dev_api_key_123"
    debug: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
