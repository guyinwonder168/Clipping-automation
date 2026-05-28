"""Tests for safe filesystem path resolution."""

from clipper_agency.core.safe_paths import resolve_existing_file_under


class TestResolveExistingFileUnder:
    def test_returns_resolved_child_file_inside_base(self, tmp_path):
        base = tmp_path / "job_1"
        base.mkdir()
        video = base / "video.mp4"
        video.write_bytes(b"video")

        resolved = resolve_existing_file_under(base, "video.mp4")

        assert resolved == video.resolve()

    def test_rejects_parent_traversal_outside_base(self, tmp_path):
        base = tmp_path / "job_1"
        base.mkdir()
        outside = tmp_path / "outside.mp4"
        outside.write_bytes(b"video")

        resolved = resolve_existing_file_under(base, "../outside.mp4")

        assert resolved is None

    def test_rejects_absolute_file_outside_base(self, tmp_path):
        base = tmp_path / "job_1"
        base.mkdir()
        outside = tmp_path / "outside.mp4"
        outside.write_bytes(b"video")

        resolved = resolve_existing_file_under(base, outside)

        assert resolved is None

    def test_rejects_missing_file_inside_base(self, tmp_path):
        base = tmp_path / "job_1"
        base.mkdir()

        resolved = resolve_existing_file_under(base, "missing.mp4")

        assert resolved is None
