"""Database configuration."""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class DatabaseConfig:
    """Database configuration."""

    url: str | None
    pool_size: int
    max_overflow: int


_database_config: DatabaseConfig | None = None


def load_database_config_from_dict(config_dict: dict) -> DatabaseConfig:
    """Load database configuration from a dictionary."""
    global _database_config
    url = config_dict.get("url")
    if url and isinstance(url, str) and url.startswith("$"):
        url = os.getenv(url[1:])

    _database_config = DatabaseConfig(
        url=url,
        pool_size=config_dict.get("pool_size", 10),
        max_overflow=config_dict.get("max_overflow", 20),
    )
    return _database_config


def get_database_config() -> DatabaseConfig:
    """Get database configuration from config.yaml."""
    global _database_config
    if _database_config is not None:
        return _database_config

    from deerflow.config.app_config import AppConfig

    config_path = AppConfig.resolve_config_path()
    with open(config_path, encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    db_config = config_data.get("database", {})
    return load_database_config_from_dict(db_config)
