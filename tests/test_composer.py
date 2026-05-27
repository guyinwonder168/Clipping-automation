"""Tests for ComposerAgent artifact persistence and output naming."""

import json
from pathlib import Path

import pytest

from clipper_agency.agents.composer import ComposerAgent


class TestComposerArtifacts:
    """Composer writes input/output, FFmpeg diagnostics to agent dir."""

    def test_output_video_named_video_mp4(self, tmp_path, mocker):
        """Output video should be video.mp4, not final.mp4."""
        mocker.patch("subprocess.run")
        agent = ComposerAgent()
        result = agent.execute(
            job_id=30,
            assets=[{"scene": 1, "path": "/tmp/scene_1.mp4"}],
            audio_files=["/tmp/scene_0.mp3"],
            output_dir=str(tmp_path),
        )
        video_path = result["video_path"]
        assert video_path.endswith("video.mp4")
        assert "final.mp4" not in video_path

    def test_persists_input_json(self, tmp_path, mocker):
        mocker.patch("subprocess.run")
        agent = ComposerAgent()
        agent.execute(
            job_id=31,
            assets=[{"scene": 1, "path": "/tmp/a.mp4"}],
            audio_files=["/tmp/voice.mp3"],
            output_dir=str(tmp_path),
            assets_cache=str(tmp_path),
        )

        input_file = tmp_path / "job_31" / "agents" / "composer" / "input.json"
        assert input_file.exists()
        data = json.loads(input_file.read_text())
        assert data["job_id"] == 31
        assert data["video_asset_count"] == 1
        assert data["audio_file_count"] == 1

    def test_persists_ffmpeg_command(self, tmp_path, mocker):
        mock_run = mocker.patch("subprocess.run")
        agent = ComposerAgent()
        agent.execute(
            job_id=32,
            assets=[{"scene": 1, "path": "/tmp/a.mp4"}],
            audio_files=["/tmp/voice.mp3"],
            output_dir=str(tmp_path),
            assets_cache=str(tmp_path),
        )

        cmd_file = tmp_path / "job_32" / "agents" / "composer" / "ffmpeg_command.txt"
        assert cmd_file.exists()
        content = cmd_file.read_text()
        assert "ffmpeg" in content
        assert "-filter_complex" in content

    def test_persists_output_json(self, tmp_path, mocker):
        mocker.patch("subprocess.run")
        agent = ComposerAgent()
        agent.execute(
            job_id=33,
            assets=[{"scene": 1, "path": "/tmp/a.mp4"}],
            audio_files=["/tmp/voice.mp3"],
            output_dir=str(tmp_path),
            assets_cache=str(tmp_path),
        )

        output_file = tmp_path / "job_33" / "agents" / "composer" / "output.json"
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["status"] == "completed"
        assert "video_path" in data

    def test_ffmpeg_stderr_log_on_failure(self, tmp_path, mocker):
        """When ffmpeg fails, stderr should be persisted."""
        import subprocess
        err = subprocess.CalledProcessError(
            1, "ffmpeg",
            stderr=b"File not found: invalid input\n",
        )
        mocker.patch("subprocess.run", side_effect=err)
        agent = ComposerAgent()
        agent.execute(
            job_id=34,
            assets=[{"scene": 1, "path": "/tmp/a.mp4"}],
            audio_files=["/tmp/voice.mp3"],
            output_dir=str(tmp_path),
            assets_cache=str(tmp_path),
        )

        log_file = tmp_path / "job_34" / "agents" / "composer" / "ffmpeg_stderr.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "File not found" in content


class TestComposerOutputNaming:
    """Video output uses video.mp4 naming convention."""

    def test_video_path_includes_job_id(self, mocker):
        mocker.patch("subprocess.run")
        agent = ComposerAgent()
        result = agent.execute(
            job_id=35,
            assets=[{"scene": 1, "path": "/tmp/a.mp4"}],
            audio_files=["/tmp/voice.mp3"],
            output_dir="/tmp/output",
        )
        assert "/job_35/" in result["video_path"]
        assert result["video_path"].endswith("video.mp4")
