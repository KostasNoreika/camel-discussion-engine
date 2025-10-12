"""
Configuration management for CAMEL Discussion API
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8007
    API_WORKERS: int = 4
    DEBUG: bool = False

    # LLM API Keys
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Database
    DATABASE_URL: str = "sqlite:///./data/discussions.db"

    # CAMEL-AI Settings
    CAMEL_MAX_TURNS: int = 20
    CAMEL_CONSENSUS_THRESHOLD: float = 0.85
    CAMEL_TIMEOUT_SECONDS: int = 300

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:8006", "https://chat.noreika.lt"]

    # OpenWebUI Integration
    OPENWEBUI_URL: str = "http://localhost:8006"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
