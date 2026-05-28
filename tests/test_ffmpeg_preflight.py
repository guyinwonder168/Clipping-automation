"""Tests for FFmpeg preflight probe — codec and binary availability checks."""

import subprocess

import pytest
from clipper_agency.core.ffmpeg_preflight import FFmpegPreflight, FFmpegPreflightResult


class TestFFmpegPreflight:
    def test_probe_returns_result_with_all_checks(self, mocker):
        mocker.patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=["ffmpeg"], returncode=0, stdout="ffmpeg version 5.1", stderr="",
            ),
        )
        mocker.patch(
            "subprocess.check_output", return_value=b"libx264\naac\nmp3",
        )

        result = FFmpegPreflight.probe()

        assert isinstance(result, FFmpegPreflightResult)
        assert result.ffmpeg_found is True
        assert result.libx264_available is True
        assert result.aac_available is True
        assert result.mp3_decode_available is True

    def test_probe_ffmpeg_missing(self, mocker):
        mocker.patch("subprocess.run", side_effect=FileNotFoundError)
        result = FFmpegPreflight.probe()
        assert result.ffmpeg_found is False
        assert not result.all_ok()

    def test_probe_missing_codec_flags(self, mocker):
        mocker.patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=["ffmpeg"], returncode=0, stdout="", stderr="",
            ),
        )
        mocker.patch(
            "subprocess.check_output", return_value=b"some other codec",
        )
        result = FFmpegPreflight.probe()
        assert result.libx264_available is False
        assert not result.all_ok()
