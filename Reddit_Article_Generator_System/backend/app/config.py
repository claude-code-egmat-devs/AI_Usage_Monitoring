"""
Application configuration using Pydantic Settings
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # AI APIs
    anthropic_api_key: str
    openai_api_key: str

    # Airtable
    airtable_pat: str
    airtable_base_id: str = "app1QhwgXE2neWore"
    airtable_input_table_id: str = "tbllyjGKHOQixiDWu"
    airtable_output_table_id: str = "tbloI9ylGx7IloshU"
    airtable_doubts_table_id: str = "tblyRAeSpoEd5hOT9"

    # Google Drive
    google_service_account_path: Optional[str] = None
    google_service_account_json: Optional[str] = None  # Base64 encoded
    gdrive_images_folder_id: str = "17mLbQLnb5FLYTGPpReIoYv8L55Q5DREO"

    # Application
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    debug: bool = True

    # Storage
    temp_storage_path: str = "./tmp/images"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Model Configuration
    claude_model: str = "claude-sonnet-4-5-20250929"
    openai_image_model: str = "gpt-image-1.5"
    thinking_budget: int = 8000
    max_tokens: int = 20000

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
