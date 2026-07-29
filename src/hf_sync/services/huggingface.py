"""Hugging Face Hub integration.

Exposes: login, list files, get signed URL, repo info.
"""

from __future__ import annotations

from typing import Any

from huggingface_hub import HfApi, hf_hub_url


class HuggingFaceService:
    """Wrapper around huggingface_hub for repo operations."""

    api: HfApi

    def __init__(self, token: str = "") -> None:
        self.api = HfApi(token=token) if token else HfApi()

    def login(self, token: str) -> None:
        """Authenticate with the given token."""
        self.api = HfApi(token=token)

    def repo_info(self, repo_id: str) -> dict[str, Any]:
        """Return basic repository metadata."""
        info = self.api.repo_info(repo_id, files_metadata=False)
        return {"id": info.id, "private": info.private}

    def list_files(self, repo_id: str) -> list[dict[str, Any]]:
        """List all files in the repository."""
        paths = self.api.list_repo_files(repo_id)
        out: list[dict[str, Any]] = []
        for p in paths:
            meta = self.api.repo_info(repo_id, files_metadata=True)
            size = 0
            for sibling in getattr(meta, "siblings", []):
                if sibling.rfilename == p:
                    size = getattr(sibling, "size", 0) or 0
                    break
            out.append({"filename": p, "size": size})
        return out

    def get_signed_url(self, repo_id: str, filename: str) -> str:
        """Get a signed (download) URL for a file."""
        return hf_hub_url(repo_id, filename)

    def validate_token(self) -> bool:
        """Check if the configured token is valid by calling whoami().
        Returns True if valid, False otherwise."""
        try:
            self.api.whoami()
            return True
        except Exception:
            return False
