"""News Card render adapter — pure RenderPlan builder.

Builds a ``RenderPlan`` for the ``news_card`` template from source paths,
a headline caption, and a title.  No FFmpeg, no file probing — purely
composes contracts and primitives into a valid plan.
"""

from __future__ import annotations

from pathlib import Path

from clipper_agency.rendering.contracts import (
    RenderPlan,
    RenderScene,
    ThumbnailConfig,
)
from clipper_agency.rendering.primitives import (
    make_caption_overlays,
    transition_duration_for_template,
    transition_for_template,
)
from clipper_agency.rendering.templates import RenderTemplateConfig

# Sensible default clip duration in seconds for news-style quick cuts.
_DEFAULT_CLIP_DURATION = 5.0


def build_news_card_plan(
    *,
    template: RenderTemplateConfig,
    source_paths: list[Path],
    caption: str,
    title: str,
    diagnostics_dir: Path,
) -> RenderPlan:
    """Build a ``RenderPlan`` for the *news_card* template.

    Creates one ``RenderScene`` per source file, each with evenly-timed
    caption overlays generated via :func:`make_caption_overlays`.  Scene
    transitions mirror the template configuration.  A ``ThumbnailConfig``
    is attached, targeting ``diagnostics_dir/thumbnails/news_card.png``.

    Args:
        template: Validated ``RenderTemplateConfig`` for ``news_card``.
        source_paths: Ordered source clips (one scene each).
        caption: Full caption text split into per-scene word groups.
        title: Thumbnail title text.
        diagnostics_dir: Root directory for thumbnail output path.

    Returns:
        Fully populated ``RenderPlan`` ready for the render engine.
    """
    transition = transition_for_template(template)
    transition_dur = transition_duration_for_template(template)
    position = template.layout.caption_position or "bottom"
    style = template.layout.caption_style or "default"

    scenes: list[RenderScene] = []
    for source in source_paths:
        caption_overlays = make_caption_overlays(
            caption,
            duration_seconds=_DEFAULT_CLIP_DURATION,
            position=position,
            style=style,
        )
        scenes.append(
            RenderScene(
                source_path=str(source),
                duration_seconds=_DEFAULT_CLIP_DURATION,
                captions=caption_overlays,
                transition=transition,
                transition_duration_seconds=transition_dur,
            )
        )

    thumbnail = ThumbnailConfig(
        title=title,
        template_name="news_card",
        output_path=str(diagnostics_dir / "thumbnails" / "news_card.png"),
    )

    return RenderPlan(
        template_name="news_card",
        scenes=scenes,
        thumbnail=thumbnail,
    )
