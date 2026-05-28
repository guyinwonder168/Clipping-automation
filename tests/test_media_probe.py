"""Tests for media probing utilities."""
import json

from clipper_agency.core.media_probe import probe_video


class TestProbeVideo:
    def test_probe_returns_resolution_codec_duration(self, tmp_path, mocker):
        video = tmp_path / "test.mp4"
        video.write_bytes(b"x" * 2048)

        mocker.patch("subprocess.check_output", return_value=json.dumps({
            "streams": [{"codec_type": "video", "width": 720, "height": 1280,
                         "codec_name": "h264", "pix_fmt": "yuv420p"}],
            "format": {"duration": "5.0"},
        }).encode())

        info = probe_video(str(video), tmp_path)
        assert info is not None
        assert info.width == 720
        assert info.height == 1280
        assert info.codec == "h264"
        assert info.duration == 5.0

    def test_probe_returns_none_for_missing_file(self, tmp_path):
        info = probe_video(str(tmp_path / "missing.mp4"), tmp_path)
        assert info is None

    def test_probe_returns_none_for_ffprobe_failure(self, tmp_path, mocker):
        video = tmp_path / "broken.mp4"
        video.write_bytes(b"x")
        mocker.patch("subprocess.check_output", side_effect=OSError("ffprobe not found"))
        info = probe_video(str(video), tmp_path)
        assert info is None

    def test_probe_detects_audio_stream(self, tmp_path, mocker):
        video = tmp_path / "av.mp4"
        video.write_bytes(b"x" * 2048)

        mocker.patch("subprocess.check_output", return_value=json.dumps({
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920,
                 "codec_name": "h264", "pix_fmt": "yuv420p"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
            "format": {"duration": "30.0"},
        }).encode())

        info = probe_video(str(video), tmp_path)
        assert info is not None
        assert info.has_audio is True

    def test_probe_no_audio_stream(self, tmp_path, mocker):
        video = tmp_path / "novoice.mp4"
        video.write_bytes(b"x" * 2048)

        mocker.patch("subprocess.check_output", return_value=json.dumps({
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920,
                 "codec_name": "h264", "pix_fmt": "yuv420p"},
            ],
            "format": {"duration": "30.0"},
        }).encode())

        info = probe_video(str(video), tmp_path)
        assert info is not None
        assert info.has_audio is False

    def test_probe_handles_missing_format_section(self, tmp_path, mocker):
        video = tmp_path / "noformat.mp4"
        video.write_bytes(b"x" * 2048)

        mocker.patch("subprocess.check_output", return_value=json.dumps({
            "streams": [
                {"codec_type": "video", "width": 640, "height": 480,
                 "codec_name": "h264", "pix_fmt": "yuv420p"},
            ],
        }).encode())

        info = probe_video(str(video), tmp_path)
        assert info is not None
        assert info.duration is None

    def test_probe_accepts_file_inside_allowed_base(self, tmp_path, mocker):
        video = tmp_path / "inside.mp4"
        video.write_bytes(b"x" * 2048)
        check_output = mocker.patch("subprocess.check_output", return_value=json.dumps({
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920,
                 "codec_name": "h264", "pix_fmt": "yuv420p"},
            ],
            "format": {"duration": "30.0"},
        }).encode())

        info = probe_video(str(video), allowed_base_dir=tmp_path)

        assert info is not None
        assert info.path == str(video.resolve())
        assert str(video.resolve()) in check_output.call_args.args[0]

    def test_probe_rejects_file_outside_allowed_base(self, tmp_path, mocker):
        base = tmp_path / "base"
        base.mkdir()
        outside = tmp_path / "outside.mp4"
        outside.write_bytes(b"x" * 2048)
        check_output = mocker.patch("subprocess.check_output")

        info = probe_video(str(outside), allowed_base_dir=base)

        assert info is None
        check_output.assert_not_called()
