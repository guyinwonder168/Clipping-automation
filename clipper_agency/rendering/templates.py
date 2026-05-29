"""Strict rendering template loader.

Loads and validates YAML rendering templates, returning typed config objects.
Template names are validated against a strict pattern to prevent path traversal.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

_TEMPLATE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class TemplateLoadError(ValueError):
    """Raised when a render template cannot be loaded or validated."""


class TemplateLayout(BaseModel):
    """Layout configuration for a rendering template."""

    resolution: str = "1080x1920"
    background_color: str | None = None
    title_font_size: int | None = None
    subtitle_font_size: int | None = None
    caption_position: str | None = None
    caption_style: str | None = None
    clip_duration: str | None = None


class TemplateTransition(BaseModel):
    """Transition configuration for a rendering template."""

    type: str = "cut"
    duration: str = "0s"


class RenderTemplateConfig(BaseModel):
    """Validated configuration for a rendering template."""

    name: str
    type: str
    style: str | None = None
    description: str | None = None
    layout: TemplateLayout = Field(default_factory=TemplateLayout)
    transitions: TemplateTransition = Field(default_factory=TemplateTransition)


def load_render_template(
    template_name: str,
    templates_dir: Path | str = Path("templates"),
) -> RenderTemplateConfig:
    """Load and validate a rendering template by name.

    Args:
        template_name: Template identifier matching ``^[a-z][a-z0-9_]*$``.
        templates_dir: Directory containing ``{name}.yaml`` template files.

    Returns:
        Validated ``RenderTemplateConfig``.

    Raises:
        TemplateLoadError: If the name is invalid, file is missing, or
            the YAML content fails schema validation.
    """
    if not _TEMPLATE_NAME_PATTERN.fullmatch(template_name):
        raise TemplateLoadError(f"Invalid template name: {template_name!r}")

    template_path = Path(templates_dir) / f"{template_name}.yaml"

    if not template_path.is_file():
        raise TemplateLoadError(f"Template not found: {template_name}")

    try:
        data = yaml.safe_load(template_path.read_text(encoding="utf-8")) or {}
        return RenderTemplateConfig.model_validate(data)
    except (OSError, ValidationError, yaml.YAMLError) as exc:
        raise TemplateLoadError(
            f"Invalid template {template_name}: {exc}"
        ) from exc
