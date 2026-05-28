"""Output Packager — final output assembly with metadata."""

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clipper_agency import __version__
from clipper_agency.core.media_probe import probe_video
from clipper_agency.core.safe_paths import resolve_existing_file_under


@dataclass
class ValidationResult:
    """Result of media validation check."""
    valid: bool
    message: str


class OutputPackager:
    """Packages final video, caption, thumbnail, and metadata into output directory."""

    def _validate_output_media(
        self,
        video_path: str,
        allowed_base_dir: str | Path,
    ) -> ValidationResult:
        """Validate output video meets quality requirements.

        Checks resolution (1080x1920), codec (h264), duration (20-60s),
        and audio track presence.
        """
        safe_path = resolve_existing_file_under(allowed_base_dir, video_path)
        if safe_path is None:
            return ValidationResult(valid=False, message="invalid video path")

        info = probe_video(safe_path, allowed_base_dir)
        if info is None:
            return ValidationResult(valid=False, message="cannot probe video")

        if info.width != 1080 or info.height != 1920:
            return ValidationResult(
                valid=False,
                message=f"invalid resolution {info.width}x{info.height}, expected 1080x1920",
            )

        if info.codec != "h264":
            return ValidationResult(
                valid=False,
                message=f"invalid codec {info.codec}, expected h264",
            )

        if info.duration is not None and (info.duration < 20 or info.duration > 60):
            return ValidationResult(
                valid=False,
                message=f"invalid duration {info.duration:.1f}s, must be 20-60s",
            )

        if not info.has_audio:
            return ValidationResult(valid=False, message="no audio track")

        return ValidationResult(valid=True, message="video passes all checks")

    def package(
        self,
        job_id: int,
        video_path: str,
        caption_path: str,
        thumbnail_path: str,
        metadata: dict[str, Any],
        output_dir: str,
    ) -> dict[str, Any]:
        try:
            out = Path(output_dir) / f"job_{job_id}"
            out.mkdir(parents=True, exist_ok=True)

            final_video = out / "video.mp4"
            final_caption = out / "caption.txt"
            final_thumbnail = out / "thumbnail.png"
            meta_file = out / "metadata.json"

            # Copy video unless composer already wrote the final path.
            source_video = (
                resolve_existing_file_under(out, video_path)
                if video_path else None
            )
            if source_video is None:
                return {
                    "status": "failed",
                    "error": (
                        "Video source not found or outside job output directory: "
                        f"{video_path}"
                    ),
                    "output_dir": str(out),
                }
            if source_video != final_video.resolve():
                shutil.copy2(source_video, final_video)

            validation = self._validate_output_media(str(final_video), out)
            if not validation.valid:
                return {
                    "status": "failed",
                    "error": validation.message,
                    "output_dir": str(out),
                }

            # Copy caption if present
            if caption_path and Path(caption_path).exists():
                shutil.copy2(caption_path, final_caption)

            # Copy thumbnail if present
            if thumbnail_path and Path(thumbnail_path).exists():
                shutil.copy2(thumbnail_path, final_thumbnail)

            # Write metadata
            full_metadata = {
                "job_id": job_id,
                "clipper_agency_version": __version__,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **metadata,
            }
            meta_file.write_text(json.dumps(full_metadata, indent=2))

            return {
                "status": "completed",
                "output_dir": str(out),
                "video_path": str(final_video),
                "caption_path": str(final_caption),
                "thumbnail_path": str(final_thumbnail),
                "metadata_path": str(meta_file),
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "output_dir": output_dir,
            }
