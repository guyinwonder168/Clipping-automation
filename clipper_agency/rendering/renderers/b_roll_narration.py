"""B-Roll Narration rendering adapter — pure plan builder.

Builds a RenderPlan for the b_roll_narration template: multiple source clips
with crossfade transitions and dynamic captions distributed across scenes.
"""

from __future__ import annotations

from pathlib import Path

from clipper_agency.rendering.contracts import (
    CaptionOverlay,
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

# Template clip_duration is "3-5s" — use the upper bound as default since
# adapters do not probe source files.
_DEFAULT_CLIP_DURATION_S = 5.0


def _split_caption_across_scenes(
    caption: str, n_scenes: int
) -> list[str]:
    """Split caption words deterministically into *n_scenes* groups.

    Words are distributed as evenly as possible: earlier scenes may
    receive one extra word when the total word count is not evenly
    divisible by the number of scenes.
    """
    words = caption.split()
    if not words:
        return [""] * n_scenes

    base_count = len(words) // n_scenes
    remainder = len(words) % n_scenes

    groups: list[str] = []
    idx = 0
    for i in range(n_scenes):
        count = base_count + (1 if i < remainder else 0)
        groups.append(" ".join(words[idx : idx + count]))
        idx += count
    return groups


def build_b_roll_narration_plan(
    *,
    template: RenderTemplateConfig,
    source_paths: list[Path],
    caption: str,
    title: str,
    diagnostics_dir: Path,
) -> RenderPlan:
    """Build a render plan for the b_roll_narration template.

    Creates one ``RenderScene`` per source path, each using the template's
    crossfade transition.  Captions are split deterministically across
    scenes using the template's dynamic caption style.

    Args:
        template: Validated b_roll_narration template config.
        source_paths: One or more source media file paths (not probed).
        caption: Full caption text, split evenly across scenes.
        title: Thumbnail title text.
        diagnostics_dir: Base directory for diagnostic output (thumbnail
            path is ``diagnostics_dir/thumbnails/b_roll_narration.png``).

    Returns:
        A ``RenderPlan`` ready for the rendering engine.

    Raises:
        ValueError: If *source_paths* is empty.
    """
    if not source_paths:
        raise ValueError("source_paths must not be empty")

    transition = transition_for_template(template)
    transition_dur = transition_duration_for_template(template)
    caption_style = template.layout.caption_style or "dynamic"
    n_scenes = len(source_paths)

    caption_groups = _split_caption_across_scenes(caption, n_scenes)

    scenes: list[RenderScene] = []
    for i, source_path in enumerate(source_paths):
        captions: list[CaptionOverlay] = []
        if caption_groups[i]:
            captions = make_caption_overlays(
                text=caption_groups[i],
                duration_seconds=_DEFAULT_CLIP_DURATION_S,
                position="bottom",
                style=caption_style,
            )

        scenes.append(
            RenderScene(
                source_path=str(source_path),
                duration_seconds=_DEFAULT_CLIP_DURATION_S,
                captions=captions,
                transition=transition,
                transition_duration_seconds=transition_dur,
            )
        )

    thumbnail = ThumbnailConfig(
        title=title,
        template_name="b_roll_narration",
        output_path=str(
            diagnostics_dir / "thumbnails" / "b_roll_narration.png"
        ),
    )

    return RenderPlan(
        template_name="b_roll_narration",
        scenes=scenes,
        thumbnail=thumbnail,
    )
