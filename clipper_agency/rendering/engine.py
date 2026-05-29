"""Standalone FFmpeg Render Engine — converts RenderPlan into video + thumbnail.

All filesystem access is confined to *output_path* and *diagnostics_dir*;
no arbitrary caller-provided paths are opened for read/write.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from clipper_agency.core.artifacts import write_json, write_text
from clipper_agency.core.media_probe import probe_video
from clipper_agency.rendering.contracts import (
    CaptionOverlay,
    RenderPlan,
    RenderResult,
)
from clipper_agency.rendering.primitives import escape_drawtext
from clipper_agency.rendering.thumbnails import generate_template_thumbnail


class TemplateRenderError(RuntimeError):
    """Raised when FFmpeg rendering fails for a render plan."""


# ---------------------------------------------------------------------------
# Drawtext helpers
# ---------------------------------------------------------------------------


def _build_drawtext(caption: CaptionOverlay) -> str:
    """Return a single FFmpeg drawtext filter string for *caption*.

    Text is escaped via :func:`escape_drawtext`.  Positioning:
    * ``x=(w-text_w)/2`` (centred)
    * ``y`` is ``h-th-20`` for ``position="bottom"``, ``20`` for ``"top"``.
    """
    escaped = escape_drawtext(caption.text)

    if caption.position == "top":
        y_expr = "20"
    else:
        y_expr = "h-th-20"

    return (
        f"drawtext=text='{escaped}':"
        f"fontsize=32:"
        f"fontcolor=white:"
        f"x=(w-text_w)/2:"
        f"y={y_expr}:"
        f"enable='between(t,{caption.start_seconds},{caption.end_seconds})'"
    )


# ---------------------------------------------------------------------------
# FFmpeg argument builder
# ---------------------------------------------------------------------------


def _build_ffmpeg_args(plan: RenderPlan, output_path: Path) -> list[str]:
    """Build complete FFmpeg command-line arguments for *plan*.

    Filter graph structure::

        [0:v][1:v]...concat=n=N:v=1[outv]
        ;[outv]drawtext=...:enable='...'[v0];[v0]drawtext=...[v1];...
        ;anullsrc[outa]

    Returns a list suitable for ``subprocess.run(cmd, shell=False, ...)``.
    """
    cmd: list[str] = ["ffmpeg", "-y"]
    scenes = plan.scenes
    num_scenes = len(scenes)
    filter_parts: list[str] = []

    # ── Input files ──
    for scene in scenes:
        cmd.extend(["-i", str(scene.source_path)])

    # ── Concat filter ──
    concat_inputs = "".join(f"[{i}:v]" for i in range(num_scenes))
    concat_filter = f"{concat_inputs}concat=n={num_scenes}:v=1[outv]"
    filter_parts.append(concat_filter)

    # ── Optional drawtext chain ──
    all_captions = [
        (i, cap)
        for i, scene in enumerate(scenes)
        for cap in scene.captions
    ]
    if all_captions:
        # First drawtext takes [outv] as input, each subsequent takes [v{N}]
        previous_label = "outv"
        for idx, (_, cap) in enumerate(all_captions):
            dt = _build_drawtext(cap)
            label = f"v{idx}"
            filter_parts.append(f"[{previous_label}]{dt}[{label}]")
            previous_label = label
        video_output_label = previous_label
    else:
        video_output_label = "outv"

    # ── Silent audio ──
    total_duration = sum(scene.duration_seconds for scene in scenes)
    filter_parts.append(
        f"anullsrc=channel_layout=stereo:sample_rate=44100:duration={total_duration}[outa]"
    )

    filter_graph = ";".join(filter_parts)

    cmd.extend([
        "-filter_complex", filter_graph,
        "-map", f"[{video_output_label}]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(output_path),
    ])

    return cmd


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_plan(
    plan: RenderPlan,
    output_path: Path,
    diagnostics_dir: Path,
) -> RenderResult:
    """Render *plan* to video, producing diagnostics and an optional thumbnail.

    Args:
        plan: Fully-specified render plan (scenes, captions, thumbnail, …).
        output_path: Where to write the rendered video file.
        diagnostics_dir: Directory for ``render_plan.json``,
            ``ffmpeg_command.txt``, and (on failure) ``ffmpeg_stderr.log``.

    Returns:
        ``RenderResult`` with paths to video, thumbnail, render-plan copy,
        and diagnostics directory.

    Raises:
        TemplateRenderError: When FFmpeg exits with a non-zero code.
    """
    # ── Ensure diagnostics directory exists ──
    diagnostics_dir.mkdir(parents=True, exist_ok=True)

    # ── Ensure output directory exists ──
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Persist render plan ──
    write_json(diagnostics_dir / "render_plan.json", plan.model_dump())

    # ── Build & persist FFmpeg command ──
    cmd = _build_ffmpeg_args(plan, output_path)
    cmd_str = " ".join(cmd)
    write_text(diagnostics_dir / "ffmpeg_command.txt", cmd_str)

    # ── Run FFmpeg ──
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, shell=False)
    except subprocess.CalledProcessError as exc:
        stderr_raw = exc.stderr or ""
        if isinstance(stderr_raw, bytes):
            stderr_raw = stderr_raw.decode(errors="replace")
        write_text(diagnostics_dir / "ffmpeg_stderr.log", stderr_raw)
        raise TemplateRenderError(
            f"FFmpeg failed (exit {exc.returncode}): {stderr_raw[:500]}"
        ) from exc

    # ── Generate thumbnail (optional) ──
    thumbnail_path: str = ""
    if plan.thumbnail is not None:
        thumb_file = generate_template_thumbnail(plan.thumbnail)
        thumbnail_path = str(thumb_file)

    # ── Probe output video ──
    # allowed_base_dir is fixed to output_path.parent — the engine only
    # opens files it owns.
    probe_video(output_path, output_path.parent)

    return RenderResult(
        video_path=str(output_path),
        thumbnail_path=thumbnail_path,
        render_plan_path=str(diagnostics_dir / "render_plan.json"),
        diagnostics_dir=str(diagnostics_dir),
    )
