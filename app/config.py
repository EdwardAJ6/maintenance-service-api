"""
Configuration module for the Maintenance Service API.
Uses os.environ for environment variable management.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from dotenv import load_dotenv

# Load .env file if exists
load_dotenv()


@dataclass
class Settings:
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = os.environ.get("DATABASE_URL", "sqlite:///./maintenance.db")
    
    # AWS S3 Configuration
    aws_access_key_id: str = os.environ.get("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    aws_region: str = os.environ.get("AWS_REGION", "us-east-1")
    s3_bucket_name: str = os.environ.get("S3_BUCKET_NAME", "maintenance-images-bucket")
    
    # CORS Configuration
    allowed_origins: str | None = os.environ.get("ALLOWED_ORIGINS", None)
    
    # Application
    debug: bool = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")
    app_name: str = os.environ.get("APP_NAME", "Maintenance Service API")
    app_version: str = os.environ.get("APP_VERSION", "1.0.0")
    
    # JWT Configuration
    secret_key: str = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
    
    # Admin Configuration
    admin_email: str = os.environ.get("ADMIN_EMAIL", "admin@maintenance.api")
    admin_password: str = os.environ.get("ADMIN_PASSWORD", "admin123")


@lru_cache()
def get_settings() -> Settings:
    """
    Returns cached settings instance.
    Using lru_cache ensures settings are only loaded once.
    """
    return Settings()
