"""Tests for OpenRouter LLM client."""

from unittest.mock import patch, MagicMock

import httpx
import pytest

from clipper_agency.llm.client import OpenRouterClient


def test_client_init_requires_key():
    with patch.dict("os.environ", {}, clear=True):
        client = OpenRouterClient()
        assert client.api_key is None


def test_client_init_with_key():
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-v1-test"}):
        client = OpenRouterClient()
        assert client.api_key == "sk-or-v1-test"


def test_chat_no_key_raises():
    client = OpenRouterClient()
    client.api_key = None
    try:
        client.chat("mimo-v2-flash", [{"role": "user", "content": "Hi"}])
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "OPENROUTER_API_KEY" in str(e)


@patch("httpx.Client")
def test_chat_completion(mock_httpx):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello, world!"}}],
        "usage": {"total_tokens": 10},
    }
    mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-v1-test"}):
        client = OpenRouterClient()
        result = client.chat(
            model="mimo-v2-flash",
            messages=[{"role": "user", "content": "Say hello"}],
        )
    assert result["content"] == "Hello, world!"
    assert result["model"] == "mimo-v2-flash"
    assert "usage" in result


@patch("httpx.Client")
def test_chat_http_error_raises(mock_httpx):
    """HTTP error from API raises HTTPStatusError."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limit exceeded"
    mock_response.request = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429", request=mock_response.request, response=mock_response,
    )
    mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-test"}):
        client = OpenRouterClient()
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            client.chat("test-model", [{"role": "user", "content": "Hi"}])

    assert exc_info.value.response.status_code == 429


@patch("httpx.Client")
def test_chat_http_error_logs_detail(mock_httpx):
    """HTTP error logs status code and model name via logger.error."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limit exceeded"
    mock_response.request = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429", request=mock_response.request, response=mock_response,
    )
    mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-test"}):
        client = OpenRouterClient()
        with patch("clipper_agency.llm.client.logger") as mock_logger:
            with pytest.raises(httpx.HTTPStatusError):
                client.chat("test-model", [{"role": "user", "content": "Hi"}])

    mock_logger.error.assert_called_once()
    call_args = mock_logger.error.call_args
    assert call_args[0][0] == "LLM error: HTTP %d model=%s in %.1fs — %s"
    assert call_args[0][1] == 429
    assert call_args[0][2] == "test-model"
