"""Configuration loader — reads YAML configs + env vars into Pydantic models."""

from pathlib import Path

import yaml

from clipper_agency.config.schema import AppSettings, NicheConfig, TemplateConfig


def load_settings() -> AppSettings:
    """Load application settings from environment / .env file."""
    return AppSettings()  # type: ignore[call-arg]


def load_niche(niche_name: str, niches_dir: Path | None = None) -> NicheConfig:
    """Load a niche profile from YAML."""
    base = niches_dir or Path("niches")
    path = base / f"{niche_name}.yaml"
    if not path.exists():
        msg = f"Niche not found: {path}"
        raise FileNotFoundError(msg)
    with open(path) as f:
        data = yaml.safe_load(f)
    return NicheConfig(**data)


def load_template(template_name: str, templates_dir: Path | None = None) -> TemplateConfig:
    """Load a video template from YAML."""
    base = templates_dir or Path("templates")
    path = base / f"{template_name}.yaml"
    if not path.exists():
        msg = f"Template not found: {path}"
        raise FileNotFoundError(msg)
    with open(path) as f:
        data = yaml.safe_load(f)
    return TemplateConfig(**data)


def load_config(config_path: str | None = None) -> dict:
    """Legacy dict-based loader — delegates to structured loaders.

    Kept for backward compatibility with CLI stubs.
    """
    settings = load_settings()
    result: dict = settings.model_dump()
    if config_path:
        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}
        result.update(user_config)
    return result
