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
        mocker.patch("subprocess.check_output", return_value=b"libx264\naac\nmp3")
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
        # ffmpeg called 4 times: 2 preflight + 1 video + 1 thumbnail
        assert mock_run.call_count == 4

    def test_execute_ffmpeg_video_command(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mocker.patch("subprocess.check_output", return_value=b"libx264\naac\nmp3")
        agent = ComposerAgent()
        agent.execute(
            job_id=5,
            assets=[{"scene": 1, "path": "/tmp/scene_1.mp4"}],
            audio_files=["/tmp/scene_0.mp3"],
            output_dir="/tmp/output",
        )
        # Preflight calls occupy indices 0-1; video assembly is index 2
        args = mock_run.call_args_list[2][0][0]
        assert "ffmpeg" in args[0]
        assert "-filter_complex" in args

    def test_execute_handles_empty_inputs(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mocker.patch("subprocess.check_output", return_value=b"libx264\naac\nmp3")
        agent = ComposerAgent()
        result = agent.execute(
            job_id=5,
            assets=[],
            audio_files=[],
            output_dir="/tmp/output",
        )
        assert result["status"] == "completed"
        # Preflight calls subprocess.run for ffmpeg + ffprobe version checks,
        # but assembly should not be called (empty inputs)
        assert mock_run.call_count == 2  # only preflight calls

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
        mocker.patch("subprocess.check_output", return_value=b"libx264\naac\nmp3")
        agent = ComposerAgent()
        result = agent.execute(
            job_id=5,
            assets=[{"scene": 1, "path": "/tmp/scene_1.mp4"}],
            audio_files=["/tmp/scene_0.mp3"],
            output_dir="/tmp/output",
        )
        # Preflight (0-1), video assembly (2), thumbnail (3)
        thumb_args = mock_run.call_args_list[3][0][0]
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


class TestComposerPreflight:
    """ComposerAgent.execute() runs FFmpeg preflight and persists diagnostics."""

    def test_execute_runs_preflight_and_persists_diagnostics(self, tmp_path, mocker):
        """ComposerAgent.execute() persists preflight.json diagnostics."""
        # Mock subprocess so FFmpegPreflight.probe() doesn't actually run
        mocker.patch(
            "subprocess.run",
            return_value=mocker.Mock(returncode=0, stdout="ffmpeg version 5.1", stderr=""),
        )
        mocker.patch(
            "subprocess.check_output", return_value=b"libx264\naac\nmp3"
        )

        from clipper_agency.agents.composer import ComposerAgent

        agent = ComposerAgent()
        mocker.patch.object(agent, "_assemble_video", return_value=["ffmpeg", "-y", "out.mp4"])
        mocker.patch.object(agent, "_generate_thumbnail", return_value=None)

        assets_dir = tmp_path / "assets_cache"
        assets_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        result = agent.execute(
            job_id=99,
            assets=[{"scene": 1, "path": str(assets_dir / "scene_1.mp4")}],
            audio_files=[str(audio_dir / "voice.mp3")],
            output_dir=str(output_dir),
            assets_cache=str(assets_dir),
        )

        preflight_file = output_dir / "job_99" / "agents" / "composer" / "preflight.json"
        assert preflight_file.exists()
        assert result["status"] == "completed"

    def test_execute_fails_when_preflight_not_ok(self, tmp_path, mocker):
        """ComposerAgent.execute() fails when FFmpeg preflight fails."""
        # Mock subprocess to simulate missing ffmpeg
        mocker.patch("subprocess.run", side_effect=FileNotFoundError)

        from clipper_agency.agents.composer import ComposerAgent

        agent = ComposerAgent()

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = agent.execute(
            job_id=98,
            assets=[{"scene": 1, "path": "/tmp/a.mp4"}],
            audio_files=[],
            output_dir=str(output_dir),
            assets_cache=str(tmp_path),
        )
        assert result["status"] == "failed"
        assert any("preflight" in str(v).lower() for v in result.values())
