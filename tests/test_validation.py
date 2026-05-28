"""Tests for artifact validation primitives."""

import json
from pathlib import Path

import pytest

from clipper_agency.core.validation import (
    ValidationResult,
    validate_research_contract,
    validate_research_brief,
    validate_script,
    validate_voice_files,
    validate_scene_files,
    validate_video_file,
)


class TestValidationResult:
    """Tests for ValidationResult data structure."""

    def test_valid_result(self):
        """Valid result should have passed=True and no issues."""
        result = ValidationResult(passed=True)
        assert result.passed is True
        assert result.issues == []

    def test_invalid_result(self):
        """Invalid result should have passed=False with issues."""
        result = ValidationResult(passed=False, issues=["file missing"])
        assert result.passed is False
        assert result.issues == ["file missing"]


class TestValidateResearchContract:
    """Tests for research_contract.json validation."""

    def test_valid_contract(self, tmp_path: Path):
        """Valid research contract should pass all checks."""
        contract = {
            "topic": "Ariana Grande",
            "video_sources": ["https://example.com"],
            "context_sources": ["https://wikipedia.org"],
            "cache_key": "ariana-grande-2024",
            "cache_freshness": "24h",
        }
        path = tmp_path / "research_contract.json"
        path.write_text(json.dumps(contract))

        result = validate_research_contract(path)
        assert result.passed is True

    def test_missing_file(self, tmp_path: Path):
        """Missing file should fail with clear issue."""
        path = tmp_path / "nonexistent.json"
        result = validate_research_contract(path)
        assert result.passed is False
        assert any("not found" in i.lower() or "missing" in i.lower()
                    for i in result.issues)

    def test_invalid_json(self, tmp_path: Path):
        """Invalid JSON should fail with parse error."""
        path = tmp_path / "research_contract.json"
        path.write_text("not json {{{")
        result = validate_research_contract(path)
        assert result.passed is False
        assert any("json" in i.lower() for i in result.issues)

    def test_missing_required_field(self, tmp_path: Path):
        """Contract missing required field should fail."""
        contract = {"topic": "Test"}  # missing video_sources, etc.
        path = tmp_path / "research_contract.json"
        path.write_text(json.dumps(contract))

        result = validate_research_contract(path)
        assert result.passed is False
        assert any("video_sources" in i for i in result.issues)


class TestValidateResearchBrief:
    """Tests for research_brief.md validation."""

    def test_valid_brief(self, tmp_path: Path):
        """Existing non-empty brief should pass."""
        path = tmp_path / "research_brief.md"
        path.write_text("# Research Findings\n\nSome content here.")
        result = validate_research_brief(path)
        assert result.passed is True

    def test_missing_file(self, tmp_path: Path):
        """Missing brief file should fail."""
        path = tmp_path / "nonexistent.md"
        result = validate_research_brief(path)
        assert result.passed is False

    def test_empty_file(self, tmp_path: Path):
        """Empty brief file should fail."""
        path = tmp_path / "research_brief.md"
        path.write_text("")
        result = validate_research_brief(path)
        assert result.passed is False


class TestValidateScript:
    """Tests for script.json validation."""

    def test_valid_script(self, tmp_path: Path):
        """Valid script with scenes and text should pass."""
        script = {
            "scenes": [{"scene": 1, "text": "Hello world"}],
            "text": "Hello world",
            "caption": "Test caption",
        }
        path = tmp_path / "script.json"
        path.write_text(json.dumps(script))

        result = validate_script(path)
        assert result.passed is True

    def test_missing_scenes_key(self, tmp_path: Path):
        """Script without scenes key should fail."""
        script = {"text": "Hello", "caption": "Test"}
        path = tmp_path / "script.json"
        path.write_text(json.dumps(script))

        result = validate_script(path)
        assert result.passed is False
        assert any("scenes" in i for i in result.issues)

    def test_empty_scenes(self, tmp_path: Path):
        """Script with empty scenes list should fail."""
        script = {"scenes": [], "text": "", "caption": ""}
        path = tmp_path / "script.json"
        path.write_text(json.dumps(script))

        result = validate_script(path)
        assert result.passed is False


class TestValidateVoiceFiles:
    """Tests for voice file validation."""

    def test_valid_files(self, tmp_path: Path):
        """Existing non-zero voice files should pass."""
        f1 = tmp_path / "scene_1.mp3"; f1.write_bytes(b"x" * 100)
        f2 = tmp_path / "scene_2.mp3"; f2.write_bytes(b"x" * 100)

        result = validate_voice_files([str(f1), str(f2)])
        assert result.passed is True

    def test_empty_list(self):
        """Empty file list should fail."""
        result = validate_voice_files([])
        assert result.passed is False

    def test_missing_file(self, tmp_path: Path):
        """Missing voice file should fail."""
        result = validate_voice_files([str(tmp_path / "missing.mp3")])
        assert result.passed is False

    def test_zero_size_file(self, tmp_path: Path):
        """Zero-size voice file should fail."""
        f = tmp_path / "empty.mp3"; f.write_bytes(b"")
        result = validate_voice_files([str(f)])
        assert result.passed is False


class TestValidateSceneFiles:
    """Tests for scene file validation."""

    def test_valid_files(self, tmp_path: Path):
        """Existing non-zero scene files should pass."""
        f1 = tmp_path / "scene_1.mp4"; f1.write_bytes(b"x" * 100)
        result = validate_scene_files([str(f1)])
        assert result.passed is True

    def test_missing_file(self, tmp_path: Path):
        """Missing scene file should fail."""
        result = validate_scene_files([str(tmp_path / "missing.mp4")])
        assert result.passed is False


class TestValidateVideoFile:
    """Tests for video file validation."""

    def test_valid_video(self, tmp_path: Path):
        """Existing non-zero video file should pass."""
        f = tmp_path / "video.mp4"; f.write_bytes(b"x" * 2048)
        result = validate_video_file(str(f))
        assert result.passed is True

    def test_missing_file(self, tmp_path: Path):
        """Missing video file should fail."""
        result = validate_video_file(str(tmp_path / "missing.mp4"))
        assert result.passed is False

    def test_too_small(self, tmp_path: Path):
        """Very small video file should fail (likely corrupt)."""
        f = tmp_path / "tiny.mp4"; f.write_bytes(b"x" * 10)
        result = validate_video_file(str(f))
        assert result.passed is False
