"""Tests for card-to-video conversion."""
import subprocess

import pytest
from clipper_agency.core.card_to_video import card_to_video, CardVideoResult


class TestCardToVideo:
    def test_convert_card_to_5s_video(self, tmp_path, mocker):
        """PNG card → 5s MP4 video with silent audio."""
        from PIL import Image
        card_path = tmp_path / "card.png"
        Image.new("RGB", (1080, 1920), (0, 0, 0)).save(card_path)
        
        mock_run = mocker.patch("subprocess.run", return_value=mocker.Mock(
            returncode=0, stderr=b"", stdout=b""))
        mock_probe = mocker.patch("subprocess.check_output", return_value=b"")
        
        output = tmp_path / "card_video.mp4"
        result = card_to_video(str(card_path), str(output))
        
        assert result.success is True
        mock_run.assert_called_once()
        cmd_args = " ".join(mock_run.call_args[0][0])
        assert "-loop 1" in cmd_args
        assert "-t 5" in cmd_args
        assert "anullsrc" in cmd_args

    def test_converted_video_is_1080x1920(self, tmp_path, mocker):
        """Output video maintains 1080x1920 resolution."""
        from PIL import Image
        card_path = tmp_path / "card.png"
        Image.new("RGB", (1080, 1920), (0, 0, 0)).save(card_path)
        
        mocker.patch("subprocess.run", return_value=mocker.Mock(
            returncode=0, stderr=b"", stdout=b""))
        
        import json
        mocker.patch("subprocess.check_output", return_value=json.dumps({
            "streams": [{"codec_type": "video", "width": 1080, "height": 1920}],
            "format": {"duration": "5.0"},
        }).encode())
        
        output = tmp_path / "card.mp4"
        output.write_bytes(b"x" * 2048)  # probe_video needs file to exist
        result = card_to_video(str(card_path), str(output))
        
        assert result.success is True
        assert result.width == 1080
        assert result.height == 1920

    def test_custom_duration_respected(self, tmp_path, mocker):
        """Custom duration flag is passed to ffmpeg."""
        from PIL import Image
        card_path = tmp_path / "card.png"
        Image.new("RGB", (1080, 1920), (0, 0, 0)).save(card_path)
        
        mock_run = mocker.patch("subprocess.run", return_value=mocker.Mock(
            returncode=0, stderr=b"", stdout=b""))
        mocker.patch("subprocess.check_output", return_value=b"")
        
        output = tmp_path / "card.mp4"
        card_to_video(str(card_path), str(output), duration=8)
        
        cmd_args = " ".join(mock_run.call_args[0][0])
        assert "-t 8" in cmd_args

    def test_missing_card_returns_failure(self, tmp_path):
        """Missing source PNG returns failure."""
        result = card_to_video(str(tmp_path / "missing.png"), str(tmp_path / "out.mp4"))
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_ffmpeg_error_returns_failure(self, tmp_path, mocker):
        """FFmpeg non-zero exit returns failure with stderr."""
        from PIL import Image
        card_path = tmp_path / "card.png"
        Image.new("RGB", (1080, 1920), (0, 0, 0)).save(card_path)
        
        mocker.patch("subprocess.run", return_value=mocker.Mock(
            returncode=1, stderr=b"encoder error", stdout=b""))
        
        output = tmp_path / "card.mp4"
        result = card_to_video(str(card_path), str(output))
        assert result.success is False
        assert result.stderr is not None

    def test_output_uses_h264_yuv420p(self, tmp_path, mocker):
        """Output codec is libx264 with yuv420p pixel format."""
        from PIL import Image
        card_path = tmp_path / "card.png"
        Image.new("RGB", (1080, 1920), (0, 0, 0)).save(card_path)
        
        mock_run = mocker.patch("subprocess.run", return_value=mocker.Mock(
            returncode=0, stderr=b"", stdout=b""))
        mocker.patch("subprocess.check_output", return_value=b"")
        
        output = tmp_path / "card.mp4"
        card_to_video(str(card_path), str(output))
        
        cmd_args = " ".join(mock_run.call_args[0][0])
        assert "libx264" in cmd_args
        assert "yuv420p" in cmd_args

    def test_ffmpeg_not_found(self, tmp_path, mocker):
        """FileNotFoundError from subprocess.run returns failure."""
        from PIL import Image
        card_path = tmp_path / "card.png"
        Image.new("RGB", (1080, 1920), (0, 0, 0)).save(card_path)

        mocker.patch("subprocess.run", side_effect=FileNotFoundError)
        output = tmp_path / "card.mp4"
        result = card_to_video(str(card_path), str(output))

        assert result.success is False
        assert "FFmpeg not found" in result.error

    def test_ffmpeg_timeout(self, tmp_path, mocker):
        """TimeoutExpired from subprocess.run returns failure."""
        from PIL import Image
        card_path = tmp_path / "card.png"
        Image.new("RGB", (1080, 1920), (0, 0, 0)).save(card_path)

        mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=60))
        output = tmp_path / "card.mp4"
        result = card_to_video(str(card_path), str(output))

        assert result.success is False
        assert "timed out" in result.error

    def test_probe_failure_returns_success_without_dimensions(self, tmp_path, mocker):
        """Probe exception is swallowed; result still succeeds with no dimensions."""
        from PIL import Image
        card_path = tmp_path / "card.png"
        Image.new("RGB", (1080, 1920), (0, 0, 0)).save(card_path)

        mocker.patch("subprocess.run", return_value=mocker.Mock(
            returncode=0, stderr=b"", stdout=b""))
        mocker.patch("clipper_agency.core.media_probe.probe_video", side_effect=RuntimeError("probe crashed"))

        output = tmp_path / "card.mp4"
        result = card_to_video(str(card_path), str(output))

        assert result.success is True
        assert result.width is None
        assert result.height is None