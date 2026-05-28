"""Media probing utilities — ffprobe-based video metadata extraction."""

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VideoInfo:
    """Immutable video metadata extracted via ffprobe."""

    path: str
    width: int
    height: int
    codec: str
    pix_fmt: str
    duration: float | None
    has_audio: bool = False
    file_size: int = 0


def probe_video(path: str) -> VideoInfo | None:
    """Probe a video file with ffprobe and return structured metadata.

    Returns ``None`` if the file does not exist, ffprobe is unavailable,
    or the JSON output cannot be parsed.
    """
    # Validate path: guard against traversal and ensure readable file
    if not path or not isinstance(path, str):
        return None
    # Required boundary check before passing a dynamic media path to ffprobe.
    if not os.path.isfile(path):  # NOSONAR - validated before shell-free subprocess use
        return None
    resolved: str = os.path.abspath(path)

    try:
        cmd: list[str] = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            resolved,
        ]
        raw = subprocess.check_output(  # NOSONAR - shell=False and path is an existing file
            cmd,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    try:
        data: dict[str, Any] = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

    streams: list[dict[str, Any]] = data.get("streams", [])
    fmt: dict[str, Any] | None = data.get("format")

    # --- video stream ---
    video_stream = _find_stream(streams, "video")
    if video_stream is None:
        return None

    width = video_stream.get("width", 0)
    height = video_stream.get("height", 0)
    codec = video_stream.get("codec_name", "unknown")
    pix_fmt = video_stream.get("pix_fmt", "unknown")

    # --- audio stream ---
    has_audio = _find_stream(streams, "audio") is not None

    # --- duration ---
    duration: float | None = None
    if fmt is not None and fmt.get("duration"):
        try:
            duration = float(fmt["duration"])
        except (ValueError, TypeError):
            duration = None

    # --- file size ---
    try:
        file_size = os.path.getsize(resolved)
    except OSError:
        file_size = 0

    return VideoInfo(
        path=resolved,
        width=width,
        height=height,
        codec=codec,
        pix_fmt=pix_fmt,
        duration=duration,
        has_audio=has_audio,
        file_size=file_size,
    )


def _find_stream(
    streams: list[dict[str, Any]], codec_type: str,
) -> dict[str, Any] | None:
    """Return the first stream matching *codec_type*, or ``None``."""
    for stream in streams:
        if stream.get("codec_type") == codec_type:
            return stream
    return None
