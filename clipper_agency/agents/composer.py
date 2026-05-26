"""Composer Agent — FFmpeg-based video assembly and thumbnail generation."""

import subprocess
from typing import Any

from clipper_agency.agents.base import BaseAgent


class ComposerAgent(BaseAgent):
    """Assembles final video from assets and audio using FFmpeg."""

    @property
    def agent_name(self) -> str:
        return "composer"

    def execute(
        self,
        job_id: int,
        assets: list[dict] | None = None,
        audio_files: list[str] | None = None,
        output_dir: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        video_assets = assets or []
        voice_files = audio_files or []

        if not video_assets and not voice_files:
            return {
                "status": "completed",
                "video_path": "",
                "thumbnail_path": "",
            }

        video_path = f"{output_dir}/job_{job_id}/final.mp4"
        thumbnail_path = f"{output_dir}/job_{job_id}/thumbnail.png"

        try:
            self._assemble_video(video_assets, voice_files, video_path)
            self._generate_thumbnail(video_path, thumbnail_path)
            return {
                "status": "completed",
                "video_path": video_path,
                "thumbnail_path": thumbnail_path,
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "video_path": video_path,
                "thumbnail_path": "",
            }

    def _build_filter(
        self, assets: list[dict], audio_files: list[str]
    ) -> str:
        video_inputs = [a for a in assets if a.get("path")]
        num_videos = len(video_inputs)

        if num_videos == 0:
            return "null"

        # Build concat filter for video streams
        concat_inputs = "".join(f"[{i}:v]" for i in range(num_videos))
        concat_filter = (
            f"{concat_inputs}concat=n={num_videos}:v=1[outv]"
        )

        # Build amix filter for audio streams
        if audio_files:
            audio_inputs = "".join(
                f"[{num_videos + i}:a]" for i in range(len(audio_files))
            )
            concat_filter += (
                f";{audio_inputs}amix=inputs={len(audio_files)}:duration=first[outa]"
            )
        else:
            concat_filter += ";anullsrc[outa]"

        return concat_filter

    def _assemble_video(
        self, assets: list[dict], audio_files: list[str], output_path: str
    ) -> None:
        video_inputs = [a for a in assets if a.get("path")]
        if not video_inputs:
            return

        cmd = ["ffmpeg", "-y"]
        for v in video_inputs:
            cmd.extend(["-i", v["path"]])
        for af in audio_files:
            cmd.extend(["-i", af])

        filter_graph = self._build_filter(assets, audio_files)
        cmd.extend([
            "-filter_complex", filter_graph,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            output_path,
        ])

        subprocess.run(cmd, check=True, capture_output=True, text=True)

    def _generate_thumbnail(self, video_path: str, thumbnail_path: str) -> None:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", "00:00:00",
            "-frames:v", "1",
            "-vf", "scale=720:1280",
            thumbnail_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
