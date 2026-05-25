"""Tests for config schema models and loader."""

import pytest
from pydantic import ValidationError

from clipper_agency.config.hierarchy import AgentDefaults, ConfigHierarchy
from clipper_agency.config.schema import AgentLLMConfig, AppConfig, NicheConfig


def test_niche_config_valid():
    data = {
        "name": "indonesian_artists",
        "language": "id",
        "tone": "casual_tiktok",
        "video_length": {"target": 30, "hard_limit": 60},
        "safety_rules": ["no_defamation"],
    }
    cfg = NicheConfig(**data)
    assert cfg.name == "indonesian_artists"
    assert cfg.video_length.target == 30


def test_niche_config_invalid_missing_name():
    data = {"language": "id"}
    with pytest.raises(ValidationError):
        NicheConfig(**data)


def test_app_config_defaults():
    cfg = AppConfig()
    assert cfg.database_path == "data/clipper.db"
    assert cfg.assets_cache_dir == "assets/cache"


def test_agent_llm_config():
    cfg = AgentLLMConfig(model="glm-4-9b", temperature=0.3)
    assert cfg.model == "glm-4-9b"
    assert cfg.temperature == 0.3


# --- Task 5: Config Hierarchy ---


def test_config_hierarchy_defaults():
    hierarchy = ConfigHierarchy()
    assert hierarchy.get("researcher", "model") == "mimo-v2-flash"


def test_config_hierarchy_niche_override():
    hierarchy = ConfigHierarchy()
    hierarchy.set_niche_override("researcher", "model", "qwen3-32b")
    assert hierarchy.get("researcher", "model") == "qwen3-32b"


def test_config_hierarchy_job_override_wins():
    hierarchy = ConfigHierarchy()
    hierarchy.set_niche_override("researcher", "model", "qwen3-32b")
    hierarchy.set_job_override("researcher", "model", "deepseek-v3.2")
    assert hierarchy.get("researcher", "model") == "deepseek-v3.2"


def test_agent_defaults_preset():
    ad = AgentDefaults()
    assert "researcher" in ad.agents
    assert ad.agents["researcher"]["model"] == "mimo-v2-flash"
