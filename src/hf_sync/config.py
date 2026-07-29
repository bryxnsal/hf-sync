"""Configuration via pydantic-settings."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from hf_sync.database import sync_get_config


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

    model_config: SettingsConfigDict = SettingsConfigDict(  # pyright: ignore[reportIncompatibleVariableOverride]
        env_file=_CONFIG_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # singleton


# ── DB fallback for configurable settings ──────────────────────────────────
# Keys whose value can be overridden from the DB `config` table.
# Maps: settings field name → hardcoded default (empty means 'no default').
_DB_CONFIG_KEYS: dict[str, str] = {
    "hf_token": "",
    "hf_repo_id": "",
    "aria2_rpc_url": "http://localhost:6800/jsonrpc",
    "aria2_rpc_secret": "",
    "rclone_remote": "",
    "rclone_path": "",
}


def _apply_db_overrides(s: Settings) -> None:
    """Override settings from DB if env/.env didn't provide values."""
    for _field, _default in _DB_CONFIG_KEYS.items():
        _current = getattr(s, _field, "")
        if _current == _default:
            _val = sync_get_config(s.db_path, _field)
            if _val:
                setattr(s, _field, _val)


_apply_db_overrides(settings)
