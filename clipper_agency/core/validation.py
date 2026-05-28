"""Artifact validation primitives — deterministic file + JSON checks."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from clipper_agency.core.artifacts import read_json


@dataclass(frozen=True)
class ValidationResult:
    """Immutable result of an artifact validation check."""
    passed: bool
    issues: list[str] = field(default_factory=list)


def validate_research_contract(path: Path | str) -> ValidationResult:
    """Validate research_contract.json: exists, valid JSON, required fields."""
    p = Path(path)
    if not p.exists():
        return ValidationResult(False, [f"research_contract not found: {p}"])
    try:
        data = read_json(p)
    except (ValueError, OSError) as e:
        return ValidationResult(False, [f"research_contract JSON parse error: {e}"])
    required = ["topic", "video_sources", "context_sources",
                "cache_key", "cache_freshness"]
    missing = [k for k in required if k not in data]
    if missing:
        return ValidationResult(False, [f"missing fields: {missing}"])
    return ValidationResult(True)


def validate_research_brief(path: Path | str) -> ValidationResult:
    """Validate research_brief.md: exists, non-empty."""
    p = Path(path)
    if not p.exists():
        return ValidationResult(False, [f"research_brief not found: {p}"])
    if p.stat().st_size == 0:
        return ValidationResult(False, ["research_brief is empty"])
    return ValidationResult(True)


def validate_script(path: Path | str) -> ValidationResult:
    """Validate script.json: valid JSON with scenes list."""
    p = Path(path)
    if not p.exists():
        return ValidationResult(False, [f"script not found: {p}"])
    try:
        data = read_json(p)
    except (ValueError, OSError) as e:
        return ValidationResult(False, [f"script JSON parse error: {e}"])
    if "scenes" not in data:
        return ValidationResult(False, ["missing 'scenes' key"])
    if not isinstance(data["scenes"], list) or len(data["scenes"]) == 0:
        return ValidationResult(False, ["scenes list is empty"])
    return ValidationResult(True)


def validate_voice_files(paths: list[str]) -> ValidationResult:
    """Validate voice files: all exist, non-zero size."""
    if not paths:
        return ValidationResult(False, ["no voice files provided"])
    issues: list[str] = []
    for fp in paths:
        p = Path(fp)
        if not p.exists():
            issues.append(f"voice file not found: {p}")
        elif p.stat().st_size == 0:
            issues.append(f"voice file is empty: {p}")
    return ValidationResult(len(issues) == 0, issues)


def validate_scene_files(paths: list[str]) -> ValidationResult:
    """Validate scene files: all exist, non-zero size."""
    if not paths:
        return ValidationResult(False, ["no scene files provided"])
    issues: list[str] = []
    for fp in paths:
        p = Path(fp)
        if not p.exists():
            issues.append(f"scene file not found: {p}")
        elif p.stat().st_size == 0:
            issues.append(f"scene file is empty: {p}")
    return ValidationResult(len(issues) == 0, issues)


def validate_video_file(path: str) -> ValidationResult:
    """Validate video file: exists, non-zero, minimum size."""
    p = Path(path)
    if not p.exists():
        return ValidationResult(False, [f"video file not found: {p}"])
    size = p.stat().st_size
    if size < 1024:
        return ValidationResult(False, [f"video file too small ({size} bytes)"])
    return ValidationResult(True)
