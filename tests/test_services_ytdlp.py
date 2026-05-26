"""Tests for yt-dlp media download service."""

from unittest.mock import patch, MagicMock

from clipper_agency.services.ytdlp import YtDlpService, DownloadResult


def test_download_result_model():
    r = DownloadResult(path="/tmp/video.mp4", title="Test", duration=30.0)
    assert r.path == "/tmp/video.mp4"
    assert r.duration == 30.0


@patch("subprocess.run")
def test_download_video(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    svc = YtDlpService()
    out = tmp_path / "video.mp4"
    result = svc.download("https://example.com/video", str(out))
    assert result.path.endswith(".mp4")
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_download_failure(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=1)
    svc = YtDlpService()
    out = tmp_path / "out.mp4"
    result = svc.download("https://invalid-url", str(out))
    assert result is None
