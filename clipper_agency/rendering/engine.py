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

    Handles three transition strategies:

    * **cut** — plain concat (rapid_update).
    * **fade** — per-scene fade-in/out before concat (news_card).
    * **crossfade** — xfade chain with normalised inputs (b_roll_narration).

    Returns a list suitable for ``subprocess.run(cmd, shell=False, ...)``.
    """
    cmd: list[str] = ["ffmpeg", "-y"]
    scenes = plan.scenes
    num_scenes = len(scenes)
    filter_parts: list[str] = []

    # ── Determine transition type from the first non-cut scene ──
    transition_type = "cut"
    transition_dur = 0.0
    for scene in scenes:
        if scene.transition and scene.transition != "cut":
            transition_type = scene.transition
            transition_dur = scene.transition_duration_seconds
            break

    # ── Input files (trimmed to scene duration) ──
    for scene in scenes:
        cmd.extend(["-t", str(scene.duration_seconds), "-i", str(scene.source_path)])

    # ── Capture start offsets for downstream caption timing ──
    scene_offsets: list[float] = [0.0] * num_scenes

    # ── Video filter chain ──
    if transition_type == "crossfade" and num_scenes > 1:
        dur = transition_dur

        # Normalise each input for consistent xfade
        for i in range(num_scenes):
            filter_parts.append(
                f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,fps=30[fn{i}]"
            )

        # Chain xfade filters cumulatively
        last_label = "fn0"
        cumulative = scenes[0].duration_seconds
        for i in range(1, num_scenes):
            offset = cumulative - i * dur
            out_label = f"xf{i}" if i < num_scenes - 1 else "outv"
            filter_parts.append(
                f"[{last_label}][fn{i}]xfade=transition=fade:"
                f"duration={dur}:offset={offset}[{out_label}]"
            )
            last_label = out_label
            cumulative += scenes[i].duration_seconds

        # Caption offsets: scene N starts at sum(d[0..N-1]) - N * xfade_dur
        scene_offsets[0] = 0.0
        cum = 0.0
        for i in range(1, num_scenes):
            cum += scenes[i - 1].duration_seconds
            scene_offsets[i] = max(0.0, cum - i * dur)

        total_duration = sum(s.duration_seconds for s in scenes) - (num_scenes - 1) * dur

    elif transition_type == "fade" and num_scenes > 1:
        dur = transition_dur

        # Per-scene fade-in / fade-out, then concat
        for i, scene in enumerate(scenes):
            d = scene.duration_seconds
            filter_parts.append(
                f"[{i}:v]fade=t=in:st=0:d={dur},"
                f"fade=t=out:st={d - dur}:d={dur}[f{i}]"
            )
        fade_inputs = "".join(f"[f{i}]" for i in range(num_scenes))
        filter_parts.append(f"{fade_inputs}concat=n={num_scenes}:v=1[outv]")

        cum = 0.0
        for i in range(num_scenes):
            scene_offsets[i] = cum
            cum += scenes[i].duration_seconds
        total_duration = cum

    else:
        # Plain cut (always used for single-scene plans too)
        concat_inputs = "".join(f"[{i}:v]" for i in range(num_scenes))
        filter_parts.append(f"{concat_inputs}concat=n={num_scenes}:v=1[outv]")

        cum = 0.0
        for i in range(num_scenes):
            scene_offsets[i] = cum
            cum += scenes[i].duration_seconds
        total_duration = cum

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
