from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Smart Investor Pro"
    APP_ENV: str = "development"
    VERSION: str = "0.2.0"
    DEBUG: bool = True

    SECRET_KEY: str = "change-me-in-prod-32chars-minimum!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    DEFAULT_PROVIDER: str = "deepseek"
    PARALLEL_ANALYSIS: bool = False
    LLM_COST_BUDGET: float = 0.50
    USE_MOCK_DATA: bool = True

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    MAX_REQUESTS_PER_MINUTE: int = 5

    DATABASE_URL: str = ""
    API_SECRET: str = ""
    REDIS_URL: str = ""
    REDIS_TTL_MARKET: int = 86400
    REDIS_TTL_LLM: int = 3600
    CACHE_ENABLED: bool = True


def get_settings() -> Settings:
    env = __import__("os").environ.get("APP_ENV", "development")
    if env == "production":
        return ProductionSettings()
    return Settings()


class ProductionSettings(Settings):
    DEBUG: bool = False
    USE_MOCK_DATA: bool = False
    LOG_LEVEL: str = "WARNING"
    MAX_REQUESTS_PER_MINUTE: int = 20
