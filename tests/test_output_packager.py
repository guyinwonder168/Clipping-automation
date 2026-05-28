"""Tests for OutputPackager."""

import json
import os
from pathlib import Path

import pytest

from clipper_agency.output.packager import OutputPackager


class TestPackagerFileCopy:
    """File packaging logic."""

    def test_package_creates_output_directory(self, tmp_path):
        packager = OutputPackager()
        video_path = str(tmp_path / "test.mp4")
        caption_path = str(tmp_path / "caption.txt")
        thumbnail_path = str(tmp_path / "thumb.png")

        # Create dummy input files
        Path(video_path).write_text("video")
        Path(caption_path).write_text("caption")
        Path(thumbnail_path).write_text("thumbnail")

        output_dir = str(tmp_path / "output")
        result = packager.package(
            job_id=1,
            video_path=video_path,
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

    def test_package_writes_metadata_json(self, tmp_path):
        packager = OutputPackager()
        video_path = str(tmp_path / "test.mp4")
        Path(video_path).write_text("video")

        output_dir = str(tmp_path / "output")
        result = packager.package(
            job_id=2,
            video_path=video_path,
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

    def test_package_includes_all_expected_fields(self, tmp_path):
        packager = OutputPackager()
        video_path = str(tmp_path / "test.mp4")
        Path(video_path).write_text("video")

        output_dir = str(tmp_path / "output")
        result = packager.package(
            job_id=3,
            video_path=video_path,
            caption_path="",
            thumbnail_path="",
            metadata={"topic": "Test"},
            output_dir=output_dir,
        )
        expected_files = {"video.mp4", "metadata.json"}
        actual_files = set(os.listdir(str(Path(output_dir) / "job_3")))
        assert expected_files.issubset(actual_files)

    def test_package_skips_copy_when_video_already_final_path(self, tmp_path):
        """Packaging should succeed when composer already wrote video.mp4."""
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
        mocker.patch("shutil.copy2", side_effect=OSError("disk full"))
        packager = OutputPackager()
        video_path = str(tmp_path / "test.mp4")
        Path(video_path).write_text("video")
        output_dir = str(tmp_path / "output")
        result = packager.package(
            job_id=5,
            video_path=video_path,
            caption_path="",
            thumbnail_path="",
            metadata={},
            output_dir=output_dir,
        )
        assert result["status"] == "failed"
        assert "disk full" in result["error"]
