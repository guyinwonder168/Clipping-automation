"""Shared fixtures for all tests."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_topic() -> str:
    return "Viral video Ariana Grande di konser Jakarta"


@pytest.fixture
def sample_niche_config() -> dict:
    return {
        "name": "indonesian_artists",
        "language": "id",
        "tone": "casual_tiktok",
        "video_length": {"target": 30, "hard_limit": 60},
        "safety_rules": ["no_defamation", "mark_rumors_as_unconfirmed"],
    }


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    """Temporary SQLite database path."""
    return str(tmp_path / "test.db")
