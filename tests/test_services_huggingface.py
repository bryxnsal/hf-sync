"""Tests for HuggingFaceService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from hf_sync.services.huggingface import HuggingFaceService


class TestInit:
    def test_without_token(self):
        svc = HuggingFaceService()
        assert svc.api is not None

    def test_with_token(self):
        svc = HuggingFaceService(token="hf_test123")
        assert svc.api is not None


class TestLogin:
    @patch("hf_sync.services.huggingface.HfApi")
    def test_login_creates_new_api(self, mock_hf_api: MagicMock):
        svc = HuggingFaceService()
        svc.login("hf_newtoken")
        mock_hf_api.assert_called_with(token="hf_newtoken")


class TestRepoInfo:
    @patch("hf_sync.services.huggingface.HfApi")
    def test_repo_info(self, mock_hf_api: MagicMock):
        mock_instance = MagicMock()
        mock_instance.repo_info.return_value = MagicMock(id="org/repo", private=False)
        mock_hf_api.return_value = mock_instance
        svc = HuggingFaceService(token="hf_test")
        info = svc.repo_info("org/repo")
        assert info["id"] == "org/repo"
        assert info["private"] is False


class TestListFiles:
    @patch("hf_sync.services.huggingface.HfApi")
    def test_list_files(self, mock_hf_api: MagicMock):
        mock_instance = MagicMock()
        mock_instance.list_repo_files.return_value = ["f1.bin", "f2.bin"]
        mock_repo_info = MagicMock()
        mock_repo_info.siblings = [
            MagicMock(rfilename="f1.bin", size=100),
            MagicMock(rfilename="f2.bin", size=200),
        ]
        mock_instance.repo_info.return_value = mock_repo_info
        mock_hf_api.return_value = mock_instance

        svc = HuggingFaceService(token="hf_test")
        files = svc.list_files("org/repo")
        assert len(files) == 2
        assert files[0]["filename"] == "f1.bin"
        assert files[0]["size"] == 100
        assert files[1]["filename"] == "f2.bin"
        assert files[1]["size"] == 200

    @patch("hf_sync.services.huggingface.HfApi")
    def test_list_files_empty(self, mock_hf_api: MagicMock):
        mock_instance = MagicMock()
        mock_instance.list_repo_files.return_value = []
        mock_hf_api.return_value = mock_instance
        svc = HuggingFaceService()
        files = svc.list_files("org/repo")
        assert files == []


class TestGetSignedUrl:
    @patch("hf_sync.services.huggingface.hf_hub_url")
    def test_get_signed_url(self, mock_url: MagicMock):
        mock_url.return_value = "https://huggingface.co/org/repo/resolve/main/f.bin"
        svc = HuggingFaceService()
        url = svc.get_signed_url("org/repo", "f.bin")
        assert url == "https://huggingface.co/org/repo/resolve/main/f.bin"
