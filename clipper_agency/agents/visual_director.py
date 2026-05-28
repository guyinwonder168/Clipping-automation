"""Visual Director Agent — video asset sourcing and scene planning."""

import datetime
import logging
import os
from pathlib import Path
from typing import Any

from clipper_agency.agents.base import BaseAgent
from clipper_agency.core.artifacts import write_json
from clipper_agency.core.paths import (
    agent_input_file,
    agent_output_file,
    ensure_agent_dir,
    visual_scene_file,
)
from clipper_agency.services.pexels import PexelsService
from clipper_agency.services.ytdlp import YtDlpService
from clipper_agency.core.media_probe import probe_video

logger = logging.getLogger(__name__)


class VisualDirectorAgent(BaseAgent):
    """Sources video assets and plans scene layouts for video composition."""

    @property
    def agent_name(self) -> str:
        return "visual_director"

    def execute(
        self,
        job_id: int,
        script: list[dict] | None = None,
        topic: str = "",
        source_urls: list[str] | None = None,
        output_dir: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        scenes = script or []
        urls = source_urls or []

        assets_cache = kwargs.get("assets_cache", "")
        agent_dir = ""
        if assets_cache:
            agent_dir = ensure_agent_dir(assets_cache, job_id, "visual_director")
            write_json(agent_input_file(assets_cache, job_id, "visual_director"), {
                "job_id": job_id,
                "scene_count": len(scenes),
                "topic": topic,
                "source_url_count": len(urls),
            })

        logger.info(
            "Visual: scenes=%d source_urls=%d",
            len(scenes), len(urls),
        )

        try:
            pexels_videos = self._search_pexels(topic)
            plan = self._plan_scenes(scenes, urls, pexels_videos)

            if agent_dir:
                write_json(f"{agent_dir}/scene_plan.json", plan)

            # Determine output base (and ensure scenes dir exists)
            if assets_cache:
                scenes_dir = f"{agent_dir}/scenes"
                Path(scenes_dir).mkdir(parents=True, exist_ok=True)
            else:
                scenes_dir = f"{output_dir or 'outputs'}/job_{job_id}"

            assets = self._download_assets(plan, job_id, scenes_dir)

            # --- Build per-clip provenance ---
            clips: dict[str, dict[str, Any]] = {}
            for asset in assets:
                scene_id = str(asset["scene"])
                path = asset.get("path", "")

                clip_data: dict[str, Any] = {"source": asset["source"]}

                if path and os.path.isfile(path):
                    info = probe_video(path)
                    if info is not None:
                        clip_data.update({
                            "original_width": info.width,
                            "original_height": info.height,
                            "codec": info.codec,
                            "duration": info.duration,
                            "file_size": info.file_size,
                            "probed": True,
                            "probe_error": None,
                        })
                    else:
                        clip_data.update({
                            "probed": False,
                            "probe_error": "ffprobe returned no data",
                            "file_size": os.path.getsize(path),
                        })
                else:
                    clip_data.update({
                        "probed": False,
                        "probe_error": "No file path available",
                    })

                clip_data["downloaded_at"] = (
                    datetime.datetime.now(datetime.timezone.utc).isoformat()
                )
                clips[scene_id] = clip_data

            output = {"status": "completed", "assets": assets}

            if agent_dir:
                write_json(agent_output_file(assets_cache, job_id, "visual_director"),
                            output)
                write_json(f"{agent_dir}/provenance.json", {
                    "topic": topic,
                    "pexels_results": len(pexels_videos),
                    "source_url_count": len(urls),
                    "scene_count": len(plan),
                    "clips": clips,
                })

            logger.info("Visual: completed %d assets", len(assets))
            return output
        except Exception as e:
            logger.exception("Visual: asset sourcing failed")
            return {"status": "failed", "error": str(e), "assets": []}

    def _search_pexels(self, topic: str) -> list[dict]:
        service = PexelsService()
        return service.search_videos(topic, per_page=10)

    def _plan_scenes(
        self,
        scenes: list[dict],
        source_urls: list[str],
        pexels_videos: list[dict],
    ) -> list[dict]:
        plan: list[dict] = []
        url_idx = 0
        pexels_idx = 0

        for scene in scenes:
            if url_idx < len(source_urls):
                plan.append({
                    "scene": scene["scene"],
                    "source": "tiktok",
                    "url": source_urls[url_idx],
                    "duration": scene.get("duration", 5),
                })
                url_idx += 1
            elif pexels_idx < len(pexels_videos):
                video = pexels_videos[pexels_idx]
                video_url = video["video_files"][0]["link"] if video.get("video_files") else ""
                plan.append({
                    "scene": scene["scene"],
                    "source": "pexels",
                    "url": video_url,
                    "duration": scene.get("duration", 5),
                })
                pexels_idx += 1
            else:
                plan.append({
                    "scene": scene["scene"],
                    "source": "none",
                    "url": "",
                    "duration": scene.get("duration", 5),
                })

        return plan

    def _download_assets(
        self, plan: list[dict], _job_id: int, scenes_dir: str
    ) -> list[dict]:
        assets: list[dict] = []
        pexels = PexelsService()
        ytdlp = YtDlpService()

        for item in plan:
            scene_id = item["scene"]
            source = item["source"]
            url = item["url"]

            if source == "tiktok":
                output_path = f"{scenes_dir}/scene_{scene_id}.mp4"
                result = ytdlp.download(url, output_path)
                file_path = result.path if result else ""
                assets.append({
                    "scene": scene_id,
                    "source": source,
                    "path": file_path,
                })
            elif source == "pexels":
                output_path = f"{scenes_dir}/scene_{scene_id}.mp4"
                path = pexels.download_video(url, output_path)
                assets.append({
                    "scene": scene_id,
                    "source": source,
                    "path": path,
                })
            else:
                assets.append({
                    "scene": scene_id,
                    "source": source,
                    "path": "",
                })

        return assets
