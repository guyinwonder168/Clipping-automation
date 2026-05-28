"""Convert generated card PNGs into 5s silent MP4 video scenes."""
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CardVideoResult:
    path: str
    success: bool
    width: int | None = None
    height: int | None = None
    error: str = ""
    stderr: str | None = None


def card_to_video(png_path: str, output_mp4: str, duration: int = 5) -> CardVideoResult:
    """Convert a PNG card to a silent MP4 video scene.
    
    Uses ffmpeg: -loop 1 for infinite input, -t for duration,
    anullsrc for silent audio track, libx264 yuv420p encoding.
    """
    if not os.path.isfile(png_path):
        return CardVideoResult(path=output_mp4, success=False, error=f"Card not found: {png_path}")
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", png_path,
        "-f", "lavfi",
        "-i", "anullsrc",
        "-t", str(duration),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-map_metadata", "-1",
        output_mp4,
    ]
    
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=60)
        if proc.returncode != 0:
            return CardVideoResult(
                path=output_mp4, success=False,
                error=f"FFmpeg exit code {proc.returncode}",
                stderr=proc.stderr.decode(errors="replace"),
            )
    except FileNotFoundError:
        return CardVideoResult(path=output_mp4, success=False, error="FFmpeg not found")
    except subprocess.TimeoutExpired:
        return CardVideoResult(path=output_mp4, success=False, error="FFmpeg timed out")
    
    # Probe output to get actual resolution
    width = height = None
    try:
        from clipper_agency.core.media_probe import probe_video
        info = probe_video(output_mp4, Path(output_mp4).parent)
        if info:
            width, height = info.width, info.height
    except Exception:
        pass
    
    return CardVideoResult(path=output_mp4, success=True, width=width, height=height)
