"""Tests for Pexels stock media service."""

from unittest.mock import patch, MagicMock

import pytest

from clipper_agency.services.pexels import PexelsService


def test_service_init():
    with patch.dict("os.environ", {}, clear=True):
        svc = PexelsService()
        assert svc.api_key is None


def test_search_videos_no_key():
    with patch.dict("os.environ", {}, clear=True):
        svc = PexelsService()
        with pytest.raises(ValueError, match="PEXELS_API_KEY"):
            svc.search_videos("concert")


@patch("httpx.Client")
def test_search_videos(mock_httpx):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "videos": [
            {
                "id": 1,
                "url": "https://example.com/video",
                "duration": 10,
                "video_files": [],
            }
        ]
    }
    mock_httpx.return_value.__enter__.return_value.get.return_value = mock_response

    with patch.dict("os.environ", {"PEXELS_API_KEY": "test-key"}):
        svc = PexelsService()
        results = svc.search_videos("concert")

    assert len(results) == 1
    assert results[0]["id"] == 1


@patch("httpx.Client")
def test_download_video(mock_httpx, tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake_video_data"
    mock_httpx.return_value.__enter__.return_value.get.return_value = mock_response

    svc = PexelsService()
    out = tmp_path / "stock.mp4"
    result = svc.download_video("https://example.com/video.mp4", str(tmp_path), "stock.mp4")

    assert result == str(out)
    assert out.read_bytes() == b"fake_video_data"


@patch("httpx.Client")
def test_download_video_handles_http_error(mock_httpx):
    """Lines 70-71: download returns None on httpx error."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("HTTP 500")
    mock_httpx.return_value.__enter__.return_value.get.return_value = mock_response

    svc = PexelsService()
    result = svc.download_video("https://broken.example.com/video.mp4", "/tmp", "test.mp4")
    assert result is None


class TestPexelsPhotoSearch:
    """Photo search method for text card images."""

    def test_search_photos_returns_list(self):
        """search_photos returns list of photo dicts with id and src."""
        service = PexelsService()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "photos": [
                {"id": 1, "src": {"medium": "https://images.pexels.com/1.jpg"}},
                {"id": 2, "src": {"medium": "https://images.pexels.com/2.jpg"}},
            ]
        }
        with patch.object(service, "api_key", "test-key"):
            with patch("clipper_agency.services.pexels.httpx.Client") as MockClient:
                mock_client = MagicMock()
                mock_client.get.return_value = mock_resp
                MockClient.return_value.__enter__ = lambda s: mock_client
                MockClient.return_value.__exit__ = MagicMock(return_value=False)
                result = service.search_photos("courtroom", per_page=3)

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert "src" in result[0]

    def test_search_photos_raises_without_api_key(self):
        """search_photos raises ValueError if PEXELS_API_KEY not set."""
        service = PexelsService()
        service.api_key = None
        with pytest.raises(ValueError, match="PEXELS_API_KEY"):
            service.search_photos("test")
