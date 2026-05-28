"""Tests for Gemini text-to-speech service."""

import base64
import wave
from unittest.mock import MagicMock, patch

import pytest

from clipper_agency.services.gemini_tts import GeminiTTSService


def test_gemini_tts_missing_key():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            GeminiTTSService()


@patch("httpx.Client")
def test_gemini_tts_wraps_pcm_response_as_wav(mock_httpx, tmp_path):
    pcm = b"\x00\x00\x01\x00"
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "audio/L16;codec=pcm;rate=24000",
                                "data": base64.b64encode(pcm).decode("ascii"),
                            }
                        }
                    ]
                }
            }
        ]
    }
    mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}, clear=True):
        output_path = tmp_path / "voice.wav"
        result = GeminiTTSService().generate_voice(
            text="Tes suara singkat.",
            voice_id="Kore",
            output_path=str(output_path),
        )

    assert result == str(output_path)
    with wave.open(str(output_path), "rb") as wav_file:
        assert wav_file.getframerate() == 24000
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.readframes(2) == pcm

    post_call = mock_httpx.return_value.__enter__.return_value.post.call_args
    assert "gemini-2.5-flash-preview-tts:generateContent" in post_call.args[0]
    assert post_call.kwargs["headers"]["x-goog-api-key"] == "test-key"
    assert post_call.kwargs["json"]["generationConfig"]["responseModalities"] == ["AUDIO"]
