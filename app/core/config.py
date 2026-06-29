"""
Core application configuration management.
Provides environment-based settings utilizing Pydantic for strict validation.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application-wide configuration schema.
    Validates and maps environment variables to strongly typed Python attributes.
    """
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 4096

    nvidia_api_key: str = Field(..., env="NVIDIA_API_KEY")
    nvidia_model: str = Field(default="moonshotai/kimi-k2.6", env="NVIDIA_MODEL")

    github_token: str = Field(..., env="GITHUB_TOKEN")
    github_webhook_secret: str = Field(..., env="GITHUB_WEBHOOK_SECRET")
    github_repo_owner: str = Field(..., env="GITHUB_REPO_OWNER")
    github_repo_name: str = Field(..., env="GITHUB_REPO_NAME")

    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    app_env: str = Field(default="development", env="APP_ENV")
    app_port: int = Field(default=8000, env="APP_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Retrieves the application configuration singleton.
    Utilizes LRU caching to prevent repeated disk I/O for environment file parsing.
    
    Returns:
        Settings: The validated configuration object.
    """
    return Settings()