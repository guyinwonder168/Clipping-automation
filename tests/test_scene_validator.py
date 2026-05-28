"""Tests for scene validation."""
import pytest
from clipper_agency.core.scene_validator import SceneValidator, SceneValidationResult


class TestSceneValidator:
    def test_valid_scene_passes(self, tmp_path):
        scene = tmp_path / "scene_1.mp4"
        scene.write_bytes(b"x" * 10000)
        result = SceneValidator.validate(str(scene))
        assert result.valid is True
        assert len(result.issues) == 0

    def test_missing_file_fails(self, tmp_path):
        result = SceneValidator.validate(str(tmp_path / "missing.mp4"))
        assert result.valid is False
        assert any("not found" in i.lower() for i in result.issues)

    def test_zero_byte_file_fails(self, tmp_path):
        scene = tmp_path / "empty.mp4"
        scene.write_bytes(b"")
        result = SceneValidator.validate(str(scene))
        assert result.valid is False
        assert any("empty" in i.lower() or "zero" in i.lower() for i in result.issues)

    def test_tiny_file_fails(self, tmp_path):
        scene = tmp_path / "tiny.mp4"
        scene.write_bytes(b"x" * 10)
        result = SceneValidator.validate(str(scene))
        assert result.valid is False
        assert any("small" in i.lower() or "corrupt" in i.lower() for i in result.issues)

    def test_custom_min_bytes_respected(self, tmp_path):
        scene = tmp_path / "medium.mp4"
        scene.write_bytes(b"x" * 2000)
        result = SceneValidator.validate(str(scene), min_bytes=5000)
        assert result.valid is False
        result2 = SceneValidator.validate(str(scene), min_bytes=1000)
        assert result2.valid is True

    def test_validate_accepts_multiple_scenes(self, tmp_path):
        """validate_all returns results for each scene."""
        valid = tmp_path / "valid.mp4"
        valid.write_bytes(b"x" * 10000)
        missing = tmp_path / "missing.mp4"
        results = SceneValidator.validate_all([str(valid), str(missing)])
        assert len(results) == 2
        assert results[0].valid is True
        assert results[1].valid is False
