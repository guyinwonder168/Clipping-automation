"""Tests for ComposerAgent."""

import pytest

from clipper_agency.agents.composer import ComposerAgent


class TestComposerName:
    """Agent name property."""

    def test_composer_agent_name(self):
        agent = ComposerAgent()
        assert agent.agent_name == "composer"


class TestComposerBuildFilter:
    """FFmpeg filter graph construction."""

    def test_build_filter_creates_concat_and_overlay(self):
        agent = ComposerAgent()
        assets = [
            {"scene": 1, "path": "/tmp/scene_1.mp4"},
            {"scene": 2, "path": "/tmp/scene_2.mp4"},
        ]
        audio_files = ["/tmp/scene_0.mp3", "/tmp/scene_1.mp3"]
        filter_str = agent._build_filter(assets, audio_files)
        assert "concat" in filter_str
        assert "amix" in filter_str
        assert "[outv]" in filter_str


class TestComposerExecute:
    """Full execute() with mocked subprocess."""

    def test_execute_returns_output_paths(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        agent = ComposerAgent()
        result = agent.execute(
            job_id=5,
            assets=[
                {"scene": 1, "path": "/tmp/scene_1.mp4"},
                {"scene": 2, "path": "/tmp/scene_2.mp4"},
            ],
            audio_files=["/tmp/scene_0.mp3", "/tmp/scene_1.mp3"],
            output_dir="/tmp/output",
        )
        assert result["status"] == "completed"
        assert result["video_path"].endswith(".mp4")
        assert result["thumbnail_path"].endswith(".png")
        # ffmpeg should be called twice: video + thumbnail
        assert mock_run.call_count == 2

    def test_execute_ffmpeg_video_command(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        agent = ComposerAgent()
        agent.execute(
            job_id=5,
            assets=[{"scene": 1, "path": "/tmp/scene_1.mp4"}],
            audio_files=["/tmp/scene_0.mp3"],
            output_dir="/tmp/output",
        )
        # First call should be video assembly
        args = mock_run.call_args_list[0][0][0]
        assert "ffmpeg" in args[0]
        assert "-filter_complex" in args

    def test_execute_handles_empty_inputs(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        agent = ComposerAgent()
        result = agent.execute(
            job_id=5,
            assets=[],
            audio_files=[],
            output_dir="/tmp/output",
        )
        assert result["status"] == "completed"
        mock_run.assert_not_called()

    def test_execute_handles_ffmpeg_failure(self, mocker):
        mocker.patch("subprocess.run", side_effect=Exception("ffmpeg not found"))
        agent = ComposerAgent()
        result = agent.execute(
            job_id=5,
            assets=[{"scene": 1, "path": "/tmp/scene_1.mp4"}],
            audio_files=["/tmp/scene_0.mp3"],
            output_dir="/tmp/output",
        )
        assert result["status"] == "failed"
        assert "error" in result
        assert "ffmpeg" in result["error"].lower()

    def test_execute_thumbnail_uses_first_frame(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        agent = ComposerAgent()
        result = agent.execute(
            job_id=5,
            assets=[{"scene": 1, "path": "/tmp/scene_1.mp4"}],
            audio_files=["/tmp/scene_0.mp3"],
            output_dir="/tmp/output",
        )
        # Second ffmpeg call is thumbnail generation from the output video
        thumb_args = mock_run.call_args_list[1][0][0]
        assert result["video_path"] in thumb_args
        assert "-frames:v" in thumb_args
        assert "1" in thumb_args

    def test_build_filter_no_video_assets_returns_null(self):
        """Line 60: empty assets list returns 'null' filter string."""
        agent = ComposerAgent()
        result = agent._build_filter([], [])
        assert result == "null"

    def test_build_filter_no_audio_uses_silent_source(self):
        """Line 77: no audio files → uses anullsrc for silent audio."""
        agent = ComposerAgent()
        assets = [{"scene": 1, "path": "/tmp/scene_1.mp4"}]
        result = agent._build_filter(assets, [])
        assert "anullsrc[outa]" in result
        assert "concat" in result

    def test_assemble_video_empty_inputs_returns_early(self, mocker):
        """Line 86: no video inputs → early return, no ffmpeg call."""
        mock_run = mocker.patch("subprocess.run")
        agent = ComposerAgent()
        agent._assemble_video([], [], "/tmp/output.mp4")
        mock_run.assert_not_called()
