"""Output Packager — final output assembly with metadata."""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clipper_agency import __version__


class OutputPackager:
    """Packages final video, caption, thumbnail, and metadata into output directory."""

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

            final_video = out / "final.mp4"
            final_caption = out / "caption.txt"
            final_thumbnail = out / "thumbnail.png"
            meta_file = out / "metadata.json"

            # Copy video
            if video_path and Path(video_path).exists():
                shutil.copy2(video_path, final_video)
            else:
                return {
                    "status": "failed",
                    "error": f"Video source not found: {video_path}",
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
