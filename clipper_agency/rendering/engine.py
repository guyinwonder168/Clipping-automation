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
    RenderScene,
)
from clipper_agency.rendering.primitives import escape_drawtext
from clipper_agency.rendering.thumbnails import generate_template_thumbnail


class TemplateRenderError(RuntimeError):
    """Raised when FFmpeg rendering fails for a render plan."""


# ---------------------------------------------------------------------------
# Drawtext helpers
# ---------------------------------------------------------------------------


def _build_drawtext(caption: CaptionOverlay, time_offset: float = 0.0) -> str:
    """Return a single FFmpeg drawtext filter string for *caption*.

    Text is escaped via :func:`escape_drawtext`.  Positioning:
    * ``x=(w-text_w)/2`` (centred)
    * ``y``: ``h-th-20`` for ``"bottom"``, ``20`` for ``"top"``,
      ``(h-th)/2`` for ``"center"``.

    *time_offset* shifts the enable window so captions appear at the
    correct absolute time in multi-scene plans.
    """
    escaped = escape_drawtext(caption.text)

    if caption.position == "top":
        y_expr = "20"
    elif caption.position == "center":
        y_expr = "(h-th)/2"
    else:
        y_expr = "h-th-20"

    return (
        f"drawtext=text='{escaped}':"
        f"fontsize=32:"
        f"fontcolor=white:"
        f"x=(w-text_w)/2:"
        f"y={y_expr}:"
        f"enable='between(t,{caption.start_seconds + time_offset},{caption.end_seconds + time_offset})'"
    )


# ---------------------------------------------------------------------------
# FFmpeg argument builder
# ---------------------------------------------------------------------------


def _add_trimmed_inputs(cmd: list[str], scenes: list[RenderScene]) -> None:
    """Append FFmpeg inputs, trimmed to the planned scene duration."""
    for scene in scenes:
        cmd.extend(["-t", str(scene.duration_seconds), "-i", str(scene.source_path)])


def _add_normalised_inputs(filter_parts: list[str], num_scenes: int) -> None:
    """Append per-input normalisation filters used by concat/xfade."""
    for index in range(num_scenes):
        filter_parts.append(
            f"[{index}:v]settb=AVTB,setpts=PTS-STARTPTS,fps=30[n{index}]"
        )


def _append_concat(
    filter_parts: list[str],
    left_label: str,
    right_label: str,
    out_label: str,
) -> None:
    """Append a two-input video concat filter."""
    filter_parts.append(f"[{left_label}][{right_label}]concat=n=2:v=1[{out_label}]")


def _append_fade_scene(
    filter_parts: list[str],
    scene_index: int,
    duration_seconds: float,
    transition_duration: float,
) -> str:
    """Append fade-in/out filters for one scene and return its output label."""
    faded_label = f"f{scene_index}"
    filter_parts.append(
        f"[n{scene_index}]fade=t=in:st=0:d={transition_duration},"
        f"fade=t=out:st={duration_seconds - transition_duration}:d={transition_duration}"
        f"[{faded_label}]"
    )
    return faded_label


def _transition_kind(scene: RenderScene) -> str:
    """Return supported transition kind, treating unknown values as cut."""
    if scene.transition in {"fade", "crossfade"}:
        return scene.transition
    return "cut"


def _append_transition_boundary(
    filter_parts: list[str],
    current_label: str,
    next_index: int,
    previous_scene: RenderScene,
    next_scene: RenderScene,
    out_label: str,
    cumulative_duration: float,
) -> tuple[str, float, float]:
    """Append one scene-boundary transition.

    Returns ``(out_label, next_scene_offset, new_cumulative_duration)``.
    """
    transition_duration = previous_scene.transition_duration_seconds
    transition = _transition_kind(previous_scene)

    if transition == "crossfade":
        offset = cumulative_duration - transition_duration
        filter_parts.append(
            f"[{current_label}][n{next_index}]xfade=transition=fade:"
            f"duration={transition_duration}:offset={offset}[{out_label}]"
        )
        return out_label, offset, cumulative_duration + next_scene.duration_seconds - transition_duration

    if transition == "fade":
        faded_label = _append_fade_scene(
            filter_parts,
            next_index,
            next_scene.duration_seconds,
            transition_duration,
        )
        _append_concat(filter_parts, current_label, faded_label, out_label)
        return out_label, cumulative_duration, cumulative_duration + next_scene.duration_seconds

    _append_concat(filter_parts, current_label, f"n{next_index}", out_label)
    return out_label, cumulative_duration, cumulative_duration + next_scene.duration_seconds


def _build_transition_chain(
    filter_parts: list[str],
    scenes: list[RenderScene],
) -> tuple[list[float], float]:
    """Append the video transition chain and return scene offsets + duration."""
    num_scenes = len(scenes)
    scene_offsets: list[float] = [0.0] * num_scenes

    if num_scenes == 1:
        filter_parts.append("[n0]concat=n=1:v=1[outv]")
        return scene_offsets, scenes[0].duration_seconds

    current_label = "n0"
    cumulative_duration = scenes[0].duration_seconds
    for index in range(1, num_scenes):
        out_label = f"v{index}" if index < num_scenes - 1 else "outv"
        current_label, scene_offsets[index], cumulative_duration = _append_transition_boundary(
            filter_parts,
            current_label,
            index,
            scenes[index - 1],
            scenes[index],
            out_label,
            cumulative_duration,
        )

    return scene_offsets, cumulative_duration


def _collect_caption_offsets(
    scenes: list[RenderScene],
    scene_offsets: list[float],
) -> list[tuple[float, CaptionOverlay]]:
    """Flatten scene captions with absolute scene offsets."""
    return [
        (scene_offsets[scene_idx], caption)
        for scene_idx, scene in enumerate(scenes)
        for caption in scene.captions
    ]


def _append_caption_filters(
    filter_parts: list[str],
    caption_offsets: list[tuple[float, CaptionOverlay]],
) -> str:
    """Append drawtext filters and return the final video output label."""
    previous_label = "outv"
    for index, (offset, caption) in enumerate(caption_offsets):
        label = f"cap{index}"
        drawtext = _build_drawtext(caption, time_offset=offset)
        filter_parts.append(f"[{previous_label}]{drawtext}[{label}]")
        previous_label = label
    return previous_label


def _build_ffmpeg_args(plan: RenderPlan, output_path: Path) -> list[str]:
    """Build complete FFmpeg command-line arguments for *plan*.

    Each scene's ``.transition`` field controls the transition FROM that scene
    TO the next scene.  This respects per-scene transition boundaries so that
    mixed-transition plans (e.g. ``cut → crossfade → cut``) are rendered
    correctly rather than using a single global transition type.

    Supported transition strategies:

    * **cut** — plain concat of normalised inputs.
    * **fade** — per-scene fade-in/out before concat.
    * **crossfade** — xfade with normalised inputs.

    Returns a list suitable for ``subprocess.run(cmd, shell=False, ...)``.
    """
    cmd: list[str] = ["ffmpeg", "-y"]
    scenes = plan.scenes
    num_scenes = len(scenes)
    if num_scenes == 0:
        raise ValueError("Render plan contains no scenes")

    filter_parts: list[str] = []
    _add_trimmed_inputs(cmd, scenes)
    _add_normalised_inputs(filter_parts, num_scenes)
    scene_offsets, total_duration = _build_transition_chain(filter_parts, scenes)

    # ── Drawtext chain (each caption offset by its scene start time) ──
    all_captions = _collect_caption_offsets(scenes, scene_offsets)
    video_output_label = _append_caption_filters(filter_parts, all_captions)

    # ── Silent audio ──
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
