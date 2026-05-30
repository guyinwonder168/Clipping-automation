"""Tests for VoiceProducerAgent."""

from unittest import mock

import pytest

from clipper_agency.agents.voice_producer import VoiceProducerAgent


class TestVoiceProducerName:
    """Agent name property."""

    def test_voice_producer_agent_name(self):
        agent = VoiceProducerAgent()
        assert agent.agent_name == "voice_producer"


class TestVoiceProducerGenerate:
    """Voice generation with mocked ElevenLabs."""

    def test_execute_generates_voice_files(self, mocker, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")
        mock_generate = mocker.patch(
            "clipper_agency.services.elevenlabs.ElevenLabsService.generate_voice",
            return_value="/tmp/output/job_1/scene_1.mp3",
        )
        agent = VoiceProducerAgent()
        script = [
            {"scene": 1, "text": "Hey TikTok!", "duration": 3},
            {"scene": 2, "text": "Did you hear about this?", "duration": 5},
        ]
        result = agent.execute(
            job_id=1,
            script=script,
            output_dir="/tmp/output",
            voice_id="21m00Tcm4TlvDq8ikWAM",
        )
        assert result["status"] == "completed"
        assert mock_generate.call_count == 2
        assert len(result["audio_files"]) == 2
        attempts = result.get("attempts", [])
        assert len(attempts) == 1
        assert attempts[0]["provider"] == "elevenlabs"

    def test_generate_passes_correct_params(self, mocker, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")
        mock_generate = mocker.patch(
            "clipper_agency.services.elevenlabs.ElevenLabsService.generate_voice",
            return_value="/tmp/output/job_1/scene_1.mp3",
        )
        agent = VoiceProducerAgent()
        agent.execute(
            job_id=1,
            script=[{"scene": 1, "text": "Hello world", "duration": 5}],
            output_dir="/tmp/output",
            voice_id="voice123",
        )
        mock_generate.assert_called_once_with(
            "Hello world",
            "voice123",
            mock.ANY,
        )

    def test_execute_defaults_voice_id(self, mocker, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")
        mock_generate = mocker.patch(
            "clipper_agency.services.elevenlabs.ElevenLabsService.generate_voice",
            return_value="/tmp/output/job_1/scene_1.mp3",
        )
        agent = VoiceProducerAgent()
        result = agent.execute(
            job_id=1,
            script=[{"scene": 1, "text": "Test", "duration": 3}],
            output_dir="/tmp/output",
        )
        assert result["status"] == "completed"
        call_kwargs = mock_generate.call_args
        assert call_kwargs[0][1] == "21m00Tcm4TlvDq8ikWAM"

    def test_execute_handles_empty_script(self, mocker, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")
        mock_generate = mocker.patch(
            "clipper_agency.services.elevenlabs.ElevenLabsService.generate_voice",
        )
        agent = VoiceProducerAgent()
        result = agent.execute(
            job_id=1,
            script=[],
            output_dir="/tmp/output",
        )
        assert result["status"] == "completed"
        assert result["audio_files"] == []
        mock_generate.assert_not_called()

    def test_execute_handles_elevenlabs_failure(self, mocker, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")

        def failing_generate(text, voice_id, output_path):
            raise Exception("ElevenLabs API error")

        mocker.patch(
            "clipper_agency.services.elevenlabs.ElevenLabsService.generate_voice",
            side_effect=failing_generate,
        )
        # Ensure no other keys are present so fallback doesn't kick in
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("FISHAUDIO_API_KEY", raising=False)

        agent = VoiceProducerAgent()
        result = agent.execute(
            job_id=1,
            script=[{"scene": 1, "text": "Test", "duration": 3}],
            output_dir="/tmp/output",
        )
        assert result["status"] == "failed"
        assert "error" in result
        assert "All TTS providers failed" in result["error"]
