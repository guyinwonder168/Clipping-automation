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

    # ── Input files (trimmed to scene duration) ──
    for scene in scenes:
        cmd.extend(["-t", str(scene.duration_seconds), "-i", str(scene.source_path)])

    # ── Normalise all inputs ──
    for i in range(num_scenes):
        filter_parts.append(
            f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,fps=30[n{i}]"
        )

    # ── Build filter chain iteratively, boundary by boundary ──
    # Each scene's .transition controls the transition from this scene
    # to the *next* scene.  Iterating boundaries instead of picking one
    # global type means mixed-transition plans render correctly.
    scene_offsets: list[float] = [0.0] * num_scenes

    if num_scenes == 1:
        filter_parts.append("[n0]concat=n=1:v=1[outv]")
        video_output_label = "outv"
        total_duration = scenes[0].duration_seconds
    else:
        current_label = "n0"
        cumulative_dur = scenes[0].duration_seconds

        for i in range(1, num_scenes):
            prev = scenes[i - 1]
            curr = scenes[i]
            transition = prev.transition or "cut"
            td = prev.transition_duration_seconds

            out_label = f"v{i}" if i < num_scenes - 1 else "outv"

            if transition == "cut":
                filter_parts.append(
                    f"[{current_label}][n{i}]concat=n=2:v=1[{out_label}]"
                )
                scene_offsets[i] = cumulative_dur
                cumulative_dur += curr.duration_seconds

            elif transition == "crossfade":
                offset = cumulative_dur - td
                filter_parts.append(
                    f"[{current_label}][n{i}]xfade=transition=fade:"
                    f"duration={td}:offset={offset}[{out_label}]"
                )
                scene_offsets[i] = cumulative_dur - td
                cumulative_dur += curr.duration_seconds - td

            elif transition == "fade":
                filter_parts.append(
                    f"[n{i}]fade=t=in:st=0:d={td},"
                    f"fade=t=out:st={curr.duration_seconds - td}:d={td}[f{i}]"
                )
                filter_parts.append(
                    f"[{current_label}][f{i}]concat=n=2:v=1[{out_label}]"
                )
                scene_offsets[i] = cumulative_dur
                cumulative_dur += curr.duration_seconds

            else:
                # Unknown transition → treat as cut
                filter_parts.append(
                    f"[{current_label}][n{i}]concat=n=2:v=1[{out_label}]"
                )
                scene_offsets[i] = cumulative_dur
                cumulative_dur += curr.duration_seconds

            current_label = out_label

        video_output_label = current_label
        total_duration = cumulative_dur

    # ── Drawtext chain (each caption offset by its scene start time) ──
    all_captions: list[tuple[float, CaptionOverlay]] = []
    for scene_idx, scene in enumerate(scenes):
        offset = scene_offsets[scene_idx]
        for cap in scene.captions:
            all_captions.append((offset, cap))

    if all_captions:
        previous_label = "outv"
        for idx, (offset, cap) in enumerate(all_captions):
            dt = _build_drawtext(cap, time_offset=offset)
            label = f"v{idx}"
            filter_parts.append(f"[{previous_label}]{dt}[{label}]")
            previous_label = label
        video_output_label = previous_label
    else:
        video_output_label = "outv"

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
