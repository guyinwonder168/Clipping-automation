"""Tests for ElevenLabs voice generation service."""

from unittest.mock import patch, MagicMock

import pytest

from clipper_agency.services.elevenlabs import ElevenLabsService


def test_service_init():
    with patch.dict("os.environ", {}, clear=True):
        svc = ElevenLabsService()
        assert svc.api_key is None


@patch("httpx.Client")
def test_generate_voice(mock_httpx, tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake_audio_data"
    mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response

    with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}):
        svc = ElevenLabsService()
        output_path = tmp_path / "voice.mp3"
        result = svc.generate_voice(
            text="Halo, ini suara uji coba",
            voice_id="test-voice-id",
            output_path=str(output_path),
        )
    assert result == str(output_path)
    assert output_path.read_bytes() == b"fake_audio_data"


def test_generate_voice_no_key(tmp_path):
    with patch.dict("os.environ", {}, clear=True):
        svc = ElevenLabsService()
        with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
            svc.generate_voice("test", "voice", str(tmp_path / "v.mp3"))
