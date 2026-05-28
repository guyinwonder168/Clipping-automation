"""Tests for scene normalization to 1080x1920."""
import pytest
from clipper_agency.core.scene_normalizer import SceneNormalizer, NormalizeResult


class TestSceneNormalizer:
    def test_normalize_scales_to_1080x1920(self, tmp_path, mocker):
        """Non-9:16 input gets scaled/padded to 1080x1920."""
        mock_run = mocker.patch("subprocess.run", return_value=mocker.Mock(
            returncode=0, stderr=b"", stdout=b""))
        # Also mock check_output so ffprobe probe doesn't call real subprocess
        mocker.patch("subprocess.check_output", return_value=b"")

        input_file = tmp_path / "input.mp4"
        input_file.write_bytes(b"x" * 10000)
        input_path = str(input_file)
        output_path = str(tmp_path / "output.mp4")

        normalizer = SceneNormalizer()
        result = normalizer.normalize(input_path, output_path)

        assert result.success is True
        # Assert ffmpeg was called at least once (probe may call check_output too)
        mock_run.assert_called()
        # Find the ffmpeg call (first arg is 'ffmpeg')
        ffmpeg_calls = [c for c in mock_run.call_args_list
                        if c[0][0] and c[0][0][0] == "ffmpeg"]
        assert len(ffmpeg_calls) == 1
        cmd_args = " ".join(ffmpeg_calls[0][0][0])
        assert "scale=1080:1920" in cmd_args
        assert "pad=1080:1920" in cmd_args
        assert "libx264" in cmd_args
        assert "yuv420p" in cmd_args

    def test_normalize_already_1080x1920_skips(self, tmp_path, mocker):
        """Already correct resolution — no ffmpeg call needed."""
        # Mock probe to report already-correct dimensions
        # probe_video is imported inside normalize() via lazy import from media_probe
        mocker.patch("clipper_agency.core.media_probe.probe_video",
                     return_value=mocker.Mock(width=1080, height=1920))

        mock_run = mocker.patch("subprocess.run")
        # Create a real file so the isfile check passes
        input_file = tmp_path / "in.mp4"
        input_file.write_bytes(b"x" * 10000)
        
        normalizer = SceneNormalizer()
        result = normalizer.normalize(str(input_file), str(tmp_path / "out.mp4"))

        assert result.success is True
        mock_run.assert_not_called()

    def test_normalize_strips_audio_from_source(self, tmp_path, mocker):
        """Source audio is stripped (-an flag)."""
        mock_run = mocker.patch("subprocess.run", return_value=mocker.Mock(
            returncode=0, stderr=b"", stdout=b""))

        input_file = tmp_path / "in.mp4"
        input_file.write_bytes(b"x" * 10000)

        normalizer = SceneNormalizer()
        normalizer.normalize(str(input_file), str(tmp_path / "out.mp4"))

        cmd_args = " ".join(mock_run.call_args[0][0])
        assert "-an" in cmd_args

    def test_normalize_handles_missing_input(self, tmp_path, mocker):
        """Missing input returns failure."""
        normalizer = SceneNormalizer()
        result = normalizer.normalize(str(tmp_path / "nonexistent.mp4"), str(tmp_path / "out.mp4"))
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_normalize_handles_ffmpeg_error(self, tmp_path, mocker):
        """FFmpeg non-zero exit returns failure."""
        mocker.patch("subprocess.run", return_value=mocker.Mock(
            returncode=1, stderr=b"ffmpeg error", stdout=b""))

        input_file = tmp_path / "in.mp4"
        input_file.write_bytes(b"x" * 10000)

        normalizer = SceneNormalizer()
        result = normalizer.normalize(str(input_file), str(tmp_path / "out.mp4"))
        assert result.success is False
        assert result.stderr is not None

    def test_normalize_uses_force_original_aspect_ratio(self, tmp_path, mocker):
        """Scale filter includes force_original_aspect_ratio=decrease."""
        mock_run = mocker.patch("subprocess.run", return_value=mocker.Mock(
            returncode=0, stderr=b"", stdout=b""))

        input_file = tmp_path / "in.mp4"
        input_file.write_bytes(b"x" * 10000)

        normalizer = SceneNormalizer()
        normalizer.normalize(str(input_file), str(tmp_path / "out.mp4"))

        cmd_args = " ".join(mock_run.call_args[0][0])
        assert "force_original_aspect_ratio" in cmd_args
