import os
from .base import Settings, ProductionSettings

_env = os.environ.get("APP_ENV", "development")

if _env == "production":
    settings = ProductionSettings()
else:
    settings = Settings()

__all__ = ["settings"]
