"""Tests for config YAML loader (load_niche, load_template, load_config)."""

from pathlib import Path

import pytest

from clipper_agency.config.loader import load_niche, load_template, load_config, load_settings
from clipper_agency.config.schema import NicheConfig, TemplateConfig


class TestLoadSettings:
    """load_settings() — returns AppSettings from environment."""

    def test_load_settings_returns_app_settings(self):
        settings = load_settings()
        assert settings.data_dir == Path("data")
        assert settings.debug is False


class TestLoadNiche:
    """load_niche() — reads niche YAML into NicheConfig."""

    def test_load_niche_from_fixture(self, fixtures_dir):
        niche = load_niche("test_niche", niches_dir=fixtures_dir)
        assert isinstance(niche, NicheConfig)
        assert niche.name == "indonesian_artists"
        assert niche.language == "id"
        assert niche.video_length.target == 30
        assert "no_defamation" in niche.safety_rules

    def test_load_niche_file_not_found(self, fixtures_dir):
        with pytest.raises(FileNotFoundError, match="Niche not found"):
            load_niche("nonexistent_niche", niches_dir=fixtures_dir)


class TestLoadTemplate:
    """load_template() — reads template YAML into TemplateConfig."""

    def test_load_template_from_fixture(self, fixtures_dir):
        template = load_template("test_template", templates_dir=fixtures_dir)
        assert isinstance(template, TemplateConfig)
        assert template.name == "rapid_update"
        assert template.type == "rapid_update"
        assert template.duration == 30
        assert "b_roll" in template.assets_required

    def test_load_template_file_not_found(self, fixtures_dir):
        with pytest.raises(FileNotFoundError, match="Template not found"):
            load_template("nonexistent_template", templates_dir=fixtures_dir)


class TestLoadConfig:
    """load_config() — legacy dict loader."""

    def test_load_config_returns_dict_with_settings(self):
        config = load_config()
        assert isinstance(config, dict)
        assert "data_dir" in config
        assert config["debug"] is False

    def test_load_config_merges_user_yaml(self, fixtures_dir, monkeypatch):
        user_yaml = fixtures_dir / "test_niche.yaml"
        config = load_config(config_path=str(user_yaml))
        assert isinstance(config, dict)
        # Should contain niche config merged in
        assert config.get("name") == "indonesian_artists"
        # Still has app settings
        assert "data_dir" in config
