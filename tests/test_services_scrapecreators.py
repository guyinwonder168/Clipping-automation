"""Tests for ScrapeCreators TikTok data service."""

from unittest.mock import patch, MagicMock

import pytest

from clipper_agency.services.scrapecreators import ScrapeCreatorsService


def test_service_init():
    with patch.dict("os.environ", {}, clear=True):
        svc = ScrapeCreatorsService()
        assert svc.api_key is None


def test_search_no_key():
    with patch.dict("os.environ", {}, clear=True):
        svc = ScrapeCreatorsService()
        with pytest.raises(ValueError, match="SCRAPECREATORS_API_KEY"):
            svc.search_tiktok_videos("artist news")


@patch("httpx.Client")
def test_search_tiktok_videos(mock_httpx):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "search_item_list": [
            {
                "aweme_id": "video123",
                "desc": "Artist Profile",
                "statistics": {
                    "digg_count": 10000,
                    "play_count": 50000,
                },
            }
        ]
    }
    mock_httpx.return_value.__enter__.return_value.get.return_value = mock_response

    with patch.dict("os.environ", {"SCRAPECREATORS_API_KEY": "test-key"}):
        svc = ScrapeCreatorsService()
        results = svc.search_tiktok_videos("artist news")

    assert len(results) == 1
    assert results[0]["aweme_id"] == "video123"
