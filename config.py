"""Application configuration module."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Configuration options for the application."""

    analysis_mode: str = "local"
    backend_base_url: str = "http://127.0.0.1:8000"
    log_level: str = "INFO"


CONFIG = AppConfig()
