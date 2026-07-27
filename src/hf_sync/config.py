"""Configuration via pydantic-settings."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Ruta por defecto: ~/.config/hf-sync/.env
# Override via env var: HF_SYNC_CONFIG=/ruta/al/.env
_CONFIG_PATH = os.environ.get(
    "HF_SYNC_CONFIG",
    str(Path.home() / ".config" / "hf-sync" / ".env"),
)


class Settings(BaseSettings):
    """Application settings loaded from .env / environment."""

    hf_token: str = ""
    hf_repo_id: str = ""

    aria2_rpc_url: str = "http://localhost:6800/jsonrpc"
    aria2_rpc_secret: str = ""

    rclone_remote: str = ""
    rclone_path: str = ""

    log_level: str = "INFO"
    db_path: str = str(Path.home() / ".local" / "share" / "hf-sync" / "state.db")
    temp_dir: str = str(Path.home() / ".cache" / "hf-sync" / "temp")

    model_config = SettingsConfigDict(
        env_file=_CONFIG_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # singleton
