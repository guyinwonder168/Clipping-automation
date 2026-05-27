"""Visual Director Agent — video asset sourcing and scene planning."""

import logging
from typing import Any

from clipper_agency.agents.base import BaseAgent
from clipper_agency.services.pexels import PexelsService
from clipper_agency.services.ytdlp import YtDlpService

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

        logger.info(
            "Visual: topic='%s' scenes=%d source_urls=%d",
            topic, len(scenes), len(urls),
        )

        try:
            pexels_videos = self._search_pexels(topic)
            plan = self._plan_scenes(scenes, urls, pexels_videos)
            assets = self._download_assets(plan, job_id, output_dir)
            logger.info("Visual: completed %d assets", len(assets))
            return {"status": "completed", "assets": assets}
        except Exception as e:
            logger.error("Visual: asset sourcing failed — %s", e)
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
        self, plan: list[dict], job_id: int, output_dir: str
    ) -> list[dict]:
        assets: list[dict] = []
        pexels = PexelsService()
        ytdlp = YtDlpService()

        for i, item in enumerate(plan):
            scene_id = item["scene"]
            source = item["source"]
            url = item["url"]

            if source == "tiktok":
                output_path = f"{output_dir}/job_{job_id}/scene_{scene_id}.mp4"
                result = ytdlp.download(url, output_path)
                file_path = result.path if result else ""
                assets.append({
                    "scene": scene_id,
                    "source": source,
                    "path": file_path,
                })
            elif source == "pexels":
                output_path = f"{output_dir}/job_{job_id}/scene_{scene_id}.mp4"
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
