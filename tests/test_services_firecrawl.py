"""Tests for Firecrawl web search service."""

from unittest.mock import patch, MagicMock

import pytest

from clipper_agency.services.firecrawl_service import FirecrawlService


def test_service_init():
    with patch.dict("os.environ", {}, clear=True):
        svc = FirecrawlService()
        assert svc.api_key is None


def test_search_no_key():
    with patch.dict("os.environ", {}, clear=True):
        svc = FirecrawlService()
        with pytest.raises(ValueError, match="FIRECRAWL_API_KEY"):
            svc.search("test query")


@patch("httpx.Client")
def test_search(mock_httpx):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {
                "url": "https://example.com",
                "title": "Example Page",
                "description": "An example",
                "content": "Full content here",
            }
        ]
    }
    mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response

    with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"}):
        svc = FirecrawlService()
        results = svc.search("test query")

    assert len(results) == 1
    assert results[0]["url"] == "https://example.com"
    assert results[0]["title"] == "Example Page"


@patch("httpx.Client")
def test_scrape(mock_httpx):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {"markdown": "# Scraped Content"}
    }
    mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response

    svc = FirecrawlService()
    svc.api_key = "test-key"
    result = svc.scrape("https://example.com")

    assert result is not None
    assert result["markdown"] == "# Scraped Content"


@patch("httpx.Client")
def test_scrape_not_found(mock_httpx):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response

    svc = FirecrawlService()
    svc.api_key = "test-key"
    result = svc.scrape("https://nonexistent.example.com")

    assert result is None
