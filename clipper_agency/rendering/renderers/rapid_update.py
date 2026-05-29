"""Rapid Update render adapter — punchy captions with hard cut transitions.

Pure plan builder: constructs a ``RenderPlan`` from template configuration
and source paths without calling FFmpeg or probing files.
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
    transition_for_template,
)
from clipper_agency.rendering.templates import RenderTemplateConfig

# Defaults derived from rapid_update.yaml: clip_duration 1.5–3s, fast cuts.
_DEFAULT_CLIP_DURATION = 2.5  # seconds — midpoint of template's 1.5–3 s range
_PUNCHY_WORDS_PER_CAPTION = 2  # tight 2-word groups for fast-paced punchy feel


def build_rapid_update_plan(
    *,
    template: RenderTemplateConfig,
    source_paths: list[Path],
    caption: str,
    title: str,
    diagnostics_dir: Path,
) -> RenderPlan:
    """Build a render plan for the rapid_update template.

    Each source clip becomes one scene with centred, punchy captions and
    hard-cut transitions.  This is a pure plan constructor — it never calls
    FFmpeg or probes source media.

    Args:
        template: Validated ``RenderTemplateConfig`` for the rapid_update style.
        source_paths: Ordered list of clip file paths (one ``RenderScene`` each).
        caption: Caption text distributed across punchy word-group overlays.
        title: Primary text for the generated thumbnail card.
        diagnostics_dir: Root folder for diagnostic outputs
            (thumbnail written to ``diagnostics_dir / "thumbnails" / "rapid_update.png"``).

    Returns:
        Complete ``RenderPlan`` ready for the rendering engine.
    """
    transition = transition_for_template(template)

    scenes: list[RenderScene] = []
    for source_path in source_paths:
        captions = make_caption_overlays(
            text=caption,
            duration_seconds=_DEFAULT_CLIP_DURATION,
            words_per_caption=_PUNCHY_WORDS_PER_CAPTION,
            position="center",
            style="punchy_centered",
        )
        scenes.append(
            RenderScene(
                source_path=str(source_path),
                duration_seconds=_DEFAULT_CLIP_DURATION,
                captions=captions,
                transition=transition,
            )
        )

    thumbnail = ThumbnailConfig(
        title=title,
        template_name="rapid_update",
        output_path=str(diagnostics_dir / "thumbnails" / "rapid_update.png"),
    )

    return RenderPlan(
        template_name="rapid_update",
        scenes=scenes,
        thumbnail=thumbnail,
    )
