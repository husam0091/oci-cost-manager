"""Application configuration management."""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "OCI Cost Manager"
    app_version: str = "1.0.0"
    debug: bool = False
    demo_mode_default: bool = False
    app_env: str = os.getenv("APP_ENV", "development")
    allow_oci_file_path_mode: bool = False if os.getenv("APP_ENV", "development").lower() == "production" else True
    app_master_key: str = ""
    
    # API
    api_prefix: str = "/api/v1"
    
    # Database
    database_url: str = "sqlite:///./oci_cost_manager.db"
    
    # OCI Configuration
    oci_config_file: str = "~/.oci/config"
    oci_config_profile: str = "DEFAULT"
    
    # OCI Price List API
    oci_price_api_url: str = "https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/"
    
    # Caching
    cache_ttl_compartments: int = 3600  # 1 hour
    cache_ttl_resources: int = 900  # 15 minutes
    cache_ttl_prices: int = 86400  # 24 hours
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Exports
    export_dir: str = "/data/exports"

    # Portal SSL
    portal_ssl_dir: str = "/app/portal-ssl"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @model_validator(mode="after")
    def _validate_production_master_key(self):
        if (self.app_env or "").lower() != "production":
            return self
        raw = (self.app_master_key or "").strip()
        if not raw:
            raise RuntimeError("APP_MASTER_KEY required in production")
        try:
            import base64
            decoded = base64.b64decode(raw, validate=True)
        except Exception:
            decoded = raw.encode("utf-8")
        if len(decoded) < 32:
            raise RuntimeError("APP_MASTER_KEY required in production")
        return self


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience function to get OCI config path
def get_oci_config_path() -> Path:
    """Get the expanded OCI config file path."""
    settings = get_settings()
    return Path(settings.oci_config_file).expanduser()
