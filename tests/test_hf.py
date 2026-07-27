"""Tests for huggingface service."""

from hf_sync.services.huggingface import HuggingFaceService


def test_service_init() -> None:
    svc = HuggingFaceService()
    assert svc.api is not None
