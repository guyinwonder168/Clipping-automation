"""Tests for OutputPackager."""

import json
import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from clipper_agency.output.packager import OutputPackager


class TestPackagerFileCopy:
    """File packaging logic."""

    def _job_video(self, tmp_path, job_id: int) -> tuple[Path, str]:
        output_dir = tmp_path / "output"
        video_path = output_dir / f"job_{job_id}" / "video.mp4"
        video_path.parent.mkdir(parents=True)
        video_path.write_text("video")
        return video_path, str(output_dir)

    def test_package_creates_output_directory(self, tmp_path, mocker):
        mocker.patch("clipper_agency.output.packager.probe_video",
                     return_value=Mock(width=1080, height=1920, codec="h264",
                                       duration=30.0, has_audio=True))
        packager = OutputPackager()
        video_path, output_dir = self._job_video(tmp_path, 1)
        caption_path = str(tmp_path / "caption.txt")
        thumbnail_path = str(tmp_path / "thumb.png")

        # Create dummy input files
        Path(caption_path).write_text("caption")
        Path(thumbnail_path).write_text("thumbnail")

        result = packager.package(
            job_id=1,
            video_path=str(video_path),
            caption_path=caption_path,
            thumbnail_path=thumbnail_path,
            metadata={"topic": "Test", "date": "2026-05-27"},
            output_dir=output_dir,
        )
        assert result["status"] == "completed"
        assert Path(result["output_dir"]).exists()
        assert Path(result["video_path"]).exists()
        assert Path(result["caption_path"]).exists()
        assert Path(result["thumbnail_path"]).exists()

    def test_package_writes_metadata_json(self, tmp_path, mocker):
        mocker.patch("clipper_agency.output.packager.probe_video",
                     return_value=Mock(width=1080, height=1920, codec="h264",
                                       duration=30.0, has_audio=True))
        packager = OutputPackager()
        video_path, output_dir = self._job_video(tmp_path, 2)

        result = packager.package(
            job_id=2,
            video_path=str(video_path),
            caption_path="",
            thumbnail_path="",
            metadata={"topic": "K-pop"},
            output_dir=output_dir,
        )
        metadata_file = Path(output_dir) / "job_2" / "metadata.json"
        assert metadata_file.exists()
        data = json.loads(metadata_file.read_text())
        assert data["topic"] == "K-pop"
        assert data["job_id"] == 2

    def test_package_includes_all_expected_fields(self, tmp_path, mocker):
        mocker.patch("clipper_agency.output.packager.probe_video",
                     return_value=Mock(width=1080, height=1920, codec="h264",
                                       duration=30.0, has_audio=True))
        packager = OutputPackager()
        video_path, output_dir = self._job_video(tmp_path, 3)

        result = packager.package(
            job_id=3,
            video_path=str(video_path),
            caption_path="",
            thumbnail_path="",
            metadata={"topic": "Test"},
            output_dir=output_dir,
        )
        expected_files = {"video.mp4", "metadata.json"}
        actual_files = set(os.listdir(str(Path(output_dir) / "job_3")))
        assert expected_files.issubset(actual_files)

    def test_package_skips_copy_when_video_already_final_path(self, tmp_path, mocker):
        """Packaging should succeed when composer already wrote video.mp4."""
        mocker.patch("clipper_agency.output.packager.probe_video",
                     return_value=Mock(width=1080, height=1920, codec="h264",
                                       duration=30.0, has_audio=True))
        packager = OutputPackager()
        output_dir = tmp_path / "output"
        final_video = output_dir / "job_6" / "video.mp4"
        final_video.parent.mkdir(parents=True)
        final_video.write_text("video")

        result = packager.package(
            job_id=6,
            video_path=str(final_video),
            caption_path="",
            thumbnail_path="",
            metadata={"topic": "Same file"},
            output_dir=str(output_dir),
        )

        assert result["status"] == "completed"
        assert result["video_path"] == str(final_video)
        assert final_video.read_text() == "video"

    def test_package_handles_missing_source_files(self, tmp_path):
        packager = OutputPackager()
        output_dir = str(tmp_path / "output")
        result = packager.package(
            job_id=4,
            video_path="/nonexistent/video.mp4",
            caption_path="",
            thumbnail_path="",
            metadata={},
            output_dir=output_dir,
        )
        assert result["status"] == "failed"
        assert "error" in result

    def test_package_handles_unexpected_exception(self, tmp_path, mocker):
        """Lines 65-66: unexpected exception during packaging returns failed."""
        mocker.patch("clipper_agency.output.packager.probe_video",
                     return_value=Mock(width=1080, height=1920, codec="h264",
                                       duration=30.0, has_audio=True))
        mocker.patch("shutil.copy2", side_effect=OSError("disk full"))
        packager = OutputPackager()
        output_dir = tmp_path / "output"
        source_video = output_dir / "job_5" / "source.mp4"
        source_video.parent.mkdir(parents=True)
        source_video.write_text("video")
        result = packager.package(
            job_id=5,
            video_path=str(source_video),
            caption_path="",
            thumbnail_path="",
            metadata={},
            output_dir=output_dir,
        )
        assert result["status"] == "failed"
        assert "disk full" in result["error"]

    def test_package_rejects_video_outside_job_output_dir(self, tmp_path, mocker):
        """Package only accepts Composer video from this job's output directory."""
        probe = mocker.patch("clipper_agency.output.packager.probe_video")
        packager = OutputPackager()
        outside_video = tmp_path / "outside.mp4"
        outside_video.write_text("video")

        result = packager.package(
            job_id=7,
            video_path=str(outside_video),
            caption_path="",
            thumbnail_path="",
            metadata={},
            output_dir=str(tmp_path / "output"),
        )

        assert result["status"] == "failed"
        assert "outside job output directory" in result["error"]
        probe.assert_not_called()


class TestPackageValidation:
    def test_package_validates_video_resolution(self, tmp_path, mocker):
        """Rejects video not 1080x1920."""
        mocker.patch("clipper_agency.output.packager.probe_video",
                     return_value=Mock(width=1920, height=1080, codec="h264",
                                       duration=30.0, has_audio=True))

        packager = OutputPackager()
        video_path = tmp_path / "vid.mp4"
        video_path.write_text("video")
        result = packager._validate_output_media(str(video_path), tmp_path)
        assert result.valid is False
        assert "resolution" in result.message.lower() or "1080" in result.message.lower()

    def test_package_validates_video_duration_too_short(self, tmp_path, mocker):
        """Rejects video under 20s."""
        mocker.patch("clipper_agency.output.packager.probe_video",
                     return_value=Mock(width=1080, height=1920, codec="h264",
                                       duration=10.0, has_audio=True))

        packager = OutputPackager()
        video_path = tmp_path / "vid.mp4"
        video_path.write_text("video")
        result = packager._validate_output_media(str(video_path), tmp_path)
        assert result.valid is False

    def test_package_validates_video_duration_too_long(self, tmp_path, mocker):
        """Rejects video over 60s."""
        mocker.patch("clipper_agency.output.packager.probe_video",
                     return_value=Mock(width=1080, height=1920, codec="h264",
                                       duration=90.0, has_audio=True))

        packager = OutputPackager()
        video_path = tmp_path / "vid.mp4"
        video_path.write_text("video")
        result = packager._validate_output_media(str(video_path), tmp_path)
        assert result.valid is False

    def test_package_validates_audio_track_present(self, tmp_path, mocker):
        """Rejects video without audio."""
        mocker.patch("clipper_agency.output.packager.probe_video",
                     return_value=Mock(width=1080, height=1920, codec="h264",
                                       duration=30.0, has_audio=False))

        packager = OutputPackager()
        video_path = tmp_path / "vid.mp4"
        video_path.write_text("video")
        result = packager._validate_output_media(str(video_path), tmp_path)
        assert result.valid is False

    def test_package_validates_codec(self, tmp_path, mocker):
        """Rejects non-h264 video."""
        mocker.patch("clipper_agency.output.packager.probe_video",
                     return_value=Mock(width=1080, height=1920, codec="vp9",
                                       duration=30.0, has_audio=True))

        packager = OutputPackager()
        video_path = tmp_path / "vid.mp4"
        video_path.write_text("video")
        result = packager._validate_output_media(str(video_path), tmp_path)
        assert result.valid is False
        assert "codec" in result.message.lower()

    def test_package_accepts_valid_video(self, tmp_path, mocker):
        """Accepts valid 1080x1920 h264 video with audio, 20-60s."""
        mocker.patch("clipper_agency.output.packager.probe_video",
                     return_value=Mock(width=1080, height=1920, codec="h264",
                                       duration=30.0, has_audio=True))

        packager = OutputPackager()
        video_path = tmp_path / "vid.mp4"
        video_path.write_text("video")
        result = packager._validate_output_media(str(video_path), tmp_path)
        assert result.valid is True
