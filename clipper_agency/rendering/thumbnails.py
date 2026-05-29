"""Template thumbnail generation — wraps CardGenerator for rendering pipeline use."""

from __future__ import annotations

import tempfile
from pathlib import Path

from clipper_agency.core.card_generator import CardGenerator, CardType
from clipper_agency.rendering.contracts import ThumbnailConfig

_TEMPLATE_CARD_MAP: dict[str, CardType] = {
    "news_card": CardType.HEADLINE,
    "b_roll_narration": CardType.CONTEXT,
    "rapid_update": CardType.FACT,
}


def generate_template_thumbnail(config: ThumbnailConfig) -> Path:
    """Generate a template-driven thumbnail image from ThumbnailConfig.

    Args:
        config: Thumbnail configuration with title, template_name, and optional output_path.

    Returns:
        Path to the generated PNG thumbnail.
    """
    card_type = _TEMPLATE_CARD_MAP.get(config.template_name, CardType.HEADLINE)

    if config.output_path is not None:
        output = Path(config.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
    else:
        output = Path(tempfile.mkdtemp()) / "thumbnail.png"

    generator = CardGenerator()
    generator.generate(card_type=card_type, text=config.title, output_path=str(output))

    return output
