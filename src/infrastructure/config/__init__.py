from .env import EnvironSettings
from .logger import logger

settings = EnvironSettings()

__all__ = ["settings", "logger"]
