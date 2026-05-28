"""Composer Agent — FFmpeg-based video assembly and thumbnail generation."""

import dataclasses
import logging
import subprocess
from pathlib import Path
from typing import Any

from clipper_agency.agents.base import BaseAgent
from clipper_agency.core.artifacts import write_json
from clipper_agency.core.ffmpeg_preflight import FFmpegPreflight
from clipper_agency.core.paths import (
    agent_input_file,
    agent_output_file,
    ensure_agent_dir,
)

logger = logging.getLogger(__name__)


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

        # ── FFmpeg preflight diagnostics ──
        try:
            preflight = FFmpegPreflight.probe()
        except Exception as exc:
            logger.error("Composer: FFmpeg preflight probe failed: %s", exc)
            return {
                "status": "failed",
                "error": f"FFmpeg preflight probe failed: {exc}",
            }
        preflight_dir = (
            Path(output_dir) / f"job_{job_id}" / "agents" / "composer"
        )
        preflight_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            preflight_dir / "preflight.json",
            dataclasses.asdict(preflight),
        )
        if not preflight.all_ok():
            logger.error(
                "Composer: FFmpeg preflight failed — ffmpeg=%s ffprobe=%s "
                "libx264=%s aac=%s mp3=%s",
                preflight.ffmpeg_found,
                preflight.ffprobe_found,
                preflight.libx264_available,
                preflight.aac_available,
                preflight.mp3_decode_available,
            )
            return {
                "status": "failed",
                "error": "FFmpeg preflight failed",
                "preflight": dataclasses.asdict(preflight),
            }

        assets_cache = kwargs.get("assets_cache", "")
        agent_dir = ""
        if assets_cache:
            agent_dir = ensure_agent_dir(assets_cache, job_id, "composer")
            write_json(agent_input_file(assets_cache, job_id, "composer"), {
                "job_id": job_id,
                "video_asset_count": len(video_assets),
                "audio_file_count": len(voice_files),
            })

        logger.info(
            "Composer: %d video assets, %d audio files",
            len(video_assets), len(voice_files),
        )

        if not video_assets and not voice_files:
            logger.warning("Composer: no assets or audio — skipping")
            return {
                "status": "completed",
                "video_path": "",
                "thumbnail_path": "",
            }

        video_path = f"{output_dir}/job_{job_id}/video.mp4"
        thumbnail_path = f"{output_dir}/job_{job_id}/thumbnail.png"

        try:
            ffmpeg_cmd = self._assemble_video(video_assets, voice_files, video_path)
            self._generate_thumbnail(video_path, thumbnail_path)

            if agent_dir:
                self._persist_diagnostics(agent_dir, ffmpeg_cmd, "")

            logger.info(
                "Composer: completed — video=%s thumbnail=%s",
                video_path, thumbnail_path,
            )

            output = {
                "status": "completed",
                "video_path": video_path,
                "thumbnail_path": thumbnail_path,
            }
            if agent_dir:
                write_json(agent_output_file(assets_cache, job_id, "composer"),
                            output)
            return output
        except subprocess.CalledProcessError as e:
            stderr_raw = e.stderr or b""
            stderr_text = stderr_raw.strip()
            if isinstance(stderr_text, bytes):
                stderr_text = stderr_text.decode()
            logger.error("Composer: FFmpeg failed — %s", stderr_text[:500])
            if agent_dir:
                self._persist_diagnostics(agent_dir, getattr(e, 'cmd', []), stderr_text)
            return {
                "status": "failed",
                "error": stderr_text or str(e),
                "video_path": video_path,
                "thumbnail_path": "",
            }
        except Exception as e:
            logger.exception("Composer: unexpected error")
            return {
                "status": "failed",
                "error": str(e),
                "video_path": video_path,
                "thumbnail_path": "",
            }

    def _persist_diagnostics(self, agent_dir: str, ffmpeg_cmd: list | str,
                              stderr_text: str) -> None:
        """Save FFmpeg command and stderr to agent artifact directory."""
        cmd_str = " ".join(ffmpeg_cmd) if isinstance(ffmpeg_cmd, list) else str(ffmpeg_cmd)
        cmd_file = Path(agent_dir) / "ffmpeg_command.txt"
        cmd_file.write_text(cmd_str)

        if stderr_text:
            log_file = Path(agent_dir) / "ffmpeg_stderr.log"
            log_file.write_text(stderr_text)

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
    ) -> list[str]:
        video_inputs = [a for a in assets if a.get("path")]
        if not video_inputs:
            return []

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
        return cmd

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
