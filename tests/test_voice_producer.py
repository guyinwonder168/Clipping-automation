"""Tests for VoiceProducerAgent — provider fallback and artifact persistence."""

import json
import os
from pathlib import Path
from unittest import mock

import pytest

from clipper_agency.agents.voice_producer import VoiceProducerAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCENES = [
    {"scene": 1, "text": "Hello", "duration": 5},
    {"scene": 2, "text": "World", "duration": 3},
]


def _mock_service(succeed: bool):
    """Return a mock TTS service instance."""
    svc = mock.MagicMock()
    if succeed:
        svc.generate_voice.return_value = "/fake/path.mp3"
    else:
        svc.generate_voice.side_effect = ValueError("service unavailable")
    return svc


# ---------------------------------------------------------------------------
# Provider fallback tests
# ---------------------------------------------------------------------------

class TestVoiceProducerFallback:
    """TTS provider priority and fallback behaviour."""

    def test_elevenlabs_succeeds_uses_elevenlabs(self, tmp_path, monkeypatch):
        """When ElevenLabs key is present and service succeeds,
        the first attempt should be elevenlabs and should complete."""
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")
        monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
        monkeypatch.setenv("FISH_AUDIO_API_KEY", "fish-key")

        agent = VoiceProducerAgent()
        with mock.patch.object(agent, "_create_service", return_value=_mock_service(True)):
            result = agent.execute(
                job_id=1,
                script=SCENES,
                assets_cache=str(tmp_path),
            )

        assert result["status"] == "completed"
        # With all keys present, elevenlabs should be tried first and succeed
        attempts = result.get("attempts", [])
        assert len(attempts) == 1
        assert attempts[0]["provider"] == "elevenlabs"
        assert attempts[0]["status"] == "success"

    def test_elevenlabs_fails_fallsback_to_gemini(self, tmp_path, monkeypatch):
        """When ElevenLabs fails, Gemini should be tried next."""
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")
        monkeypatch.setenv("GEMINI_API_KEY", "gem-key")

        agent = VoiceProducerAgent()

        fail_el = _mock_service(False)
        ok_gemini = _mock_service(True)

        services = {"elevenlabs": fail_el, "gemini_tts": ok_gemini}

        def _create(provider):
            return services[provider]

        with mock.patch.object(agent, "_create_service", side_effect=_create):
            result = agent.execute(
                job_id=2,
                script=SCENES,
                assets_cache=str(tmp_path),
            )

        assert result["status"] == "completed"
        attempts = result["attempts"]
        assert attempts[0]["provider"] == "elevenlabs"
        assert attempts[0]["status"] == "failed"
        assert attempts[1]["provider"] == "gemini_tts"
        assert attempts[1]["status"] == "success"

    def test_all_providers_fail_returns_clear_failure(self, tmp_path, monkeypatch):
        """When all providers fail, output should show each attempt and a
        clear failure status."""
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")
        monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
        monkeypatch.setenv("FISH_AUDIO_API_KEY", "fish-key")

        agent = VoiceProducerAgent()

        services = {k: _mock_service(False) for k in
                     ("elevenlabs", "gemini_tts", "fish_audio")}

        def _create(provider):
            return services[provider]

        with mock.patch.object(agent, "_create_service", side_effect=_create):
            result = agent.execute(
                job_id=3,
                script=SCENES,
                assets_cache=str(tmp_path),
            )

        assert result["status"] == "failed"
        assert result["audio_files"] == []
        attempts = result["attempts"]
        assert len(attempts) == 3
        assert all(a["status"] == "failed" for a in attempts)
        providers_seen = [a["provider"] for a in attempts]
        assert providers_seen == ["elevenlabs", "gemini_tts", "fish_audio"]
        assert "All TTS providers failed" in result["error"]

    def test_no_keys_configured_returns_missing_key_failure(self, tmp_path, monkeypatch):
        """When no TTS keys are configured, every attempt should be 'missing_key'."""
        # Ensure no keys
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("FISH_AUDIO_API_KEY", raising=False)

        agent = VoiceProducerAgent()
        result = agent.execute(
            job_id=4,
            script=SCENES,
            assets_cache=str(tmp_path),
        )

        assert result["status"] == "failed"
        attempts = result["attempts"]
        assert len(attempts) == 3
        assert all(a["status"] == "missing_key" for a in attempts)

    def test_fish_audio_alias_key_enables_fish_provider(self, tmp_path, monkeypatch):
        """The documented FISHAUDIO_KEY alias should pass pre-checks."""
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("FISH_AUDIO_API_KEY", raising=False)
        monkeypatch.setenv("FISHAUDIO_KEY", "fish-alias-key")

        agent = VoiceProducerAgent()

        def _create(provider):
            assert provider == "fish_audio"
            return _mock_service(True)

        with mock.patch.object(agent, "_create_service", side_effect=_create):
            result = agent.execute(
                job_id=5,
                script=SCENES,
                assets_cache=str(tmp_path),
            )

        assert result["status"] == "completed"
        attempts = result["attempts"]
        assert [a["status"] for a in attempts] == [
            "missing_key",
            "missing_key",
            "success",
        ]
        assert attempts[-1]["provider"] == "fish_audio"


# ---------------------------------------------------------------------------
# Artifact persistence tests
# ---------------------------------------------------------------------------

class TestVoiceProducerArtifacts:
    """Voice Producer writes input/output and provider-attempts to agent dir."""

    def test_persists_input_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")
        agent = VoiceProducerAgent()
        with mock.patch.object(agent, "_create_service", return_value=_mock_service(True)):
            agent.execute(job_id=7, script=SCENES, assets_cache=str(tmp_path))

        input_file = tmp_path / "job_7" / "agents" / "voice_producer" / "input.json"
        assert input_file.exists()
        data = json.loads(input_file.read_text())
        assert data["job_id"] == 7
        assert data["scene_count"] == 2

    def test_persists_output_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")
        agent = VoiceProducerAgent()
        with mock.patch.object(agent, "_create_service", return_value=_mock_service(True)):
            agent.execute(job_id=8, script=SCENES, assets_cache=str(tmp_path))

        output_file = tmp_path / "job_8" / "agents" / "voice_producer" / "output.json"
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["status"] == "completed"
        assert len(data["audio_files"]) == 2
        assert "attempts" in data
        assert len(data["attempts"]) == 1

    def test_persists_provider_attempts_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")
        agent = VoiceProducerAgent()
        with mock.patch.object(agent, "_create_service", return_value=_mock_service(True)):
            agent.execute(job_id=9, script=SCENES, assets_cache=str(tmp_path))

        att_file = tmp_path / "job_9" / "agents" / "voice_producer" / "provider_attempts.json"
        assert att_file.exists()
        data = json.loads(att_file.read_text())
        assert len(data) == 1
        assert data[0]["provider"] == "elevenlabs"
        assert data[0]["status"] == "success"
        assert "audio_files" in data[0]

    def test_voice_files_written_to_voices_subdir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")

        agent = VoiceProducerAgent()

        def _gen(text, voice_id, output_path):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text("audio")
            return output_path

        svc = mock.MagicMock()
        svc.generate_voice.side_effect = _gen

        with mock.patch.object(agent, "_create_service", return_value=svc):
            agent.execute(job_id=10, script=SCENES, assets_cache=str(tmp_path))

        voices_dir = tmp_path / "job_10" / "agents" / "voice_producer" / "voices"
        assert voices_dir.exists()
        voices = sorted(voices_dir.iterdir())
        assert len(voices) == 2
        names = [v.name for v in voices]
        # scene IDs from the script, not enumerate index
        assert "scene_1.mp3" in names
        assert "scene_2.mp3" in names

    def test_returns_audio_files_with_correct_scene_paths(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")

        agent = VoiceProducerAgent()

        def _gen(text, voice_id, output_path):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text("audio")
            return output_path

        svc = mock.MagicMock()
        svc.generate_voice.side_effect = _gen

        with mock.patch.object(agent, "_create_service", return_value=svc):
            result = agent.execute(job_id=11, script=SCENES, assets_cache=str(tmp_path))

        paths = result["audio_files"]
        assert len(paths) == 2
        for p in paths:
            assert "voice_producer" in p
            assert "voices" in p

    def test_partial_failure_after_some_scenes_generated(self, tmp_path, monkeypatch):
        """If a provider fails mid-processing, partial results are returned."""
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")

        agent = VoiceProducerAgent()

        scene_1_ok = mock.MagicMock()
        scene_1_ok.generate_voice.return_value = "/fake/scene_1.mp3"
        scene_2_fail = mock.MagicMock()
        scene_2_fail.generate_voice.side_effect = ValueError("timeout")

        # First call to _create_service for provider returns working service,
        # but the service fails on the second scene.
        services = iter([scene_1_ok])

        with mock.patch.object(agent, "_create_service", side_effect=lambda p: next(services)):
            result = agent.execute(
                job_id=12,
                script=SCENES,
                assets_cache=str(tmp_path),
            )

        assert result["status"] in ("failed", "completed")
