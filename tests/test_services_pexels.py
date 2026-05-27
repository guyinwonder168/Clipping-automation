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
    result = svc.download_video("https://example.com/video.mp4", str(out))

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
    result = svc.download_video("https://broken.example.com/video.mp4", "/tmp/test.mp4")
    assert result is None
