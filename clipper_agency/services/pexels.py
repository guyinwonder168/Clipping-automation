"""Pexels stock media search and download service."""

import os
from pathlib import Path
from typing import Any

import httpx


class PexelsService:
    """Search and download stock videos from Pexels API."""

    BASE_URL = "https://api.pexels.com/v1"

    def __init__(self) -> None:
        self.api_key = os.getenv("PEXELS_API_KEY")

    def search_videos(
        self, query: str, per_page: int = 5
    ) -> list[dict[str, Any]]:
        """Search for stock videos matching the query.

        Returns:
            List of video metadata dicts.
        """
        if not self.api_key:
            raise ValueError("PEXELS_API_KEY not set")

        with httpx.Client(base_url=self.BASE_URL) as client:
            resp = client.get(
                "/videos/search",
                headers={"Authorization": self.api_key},
                params={
                    "query": query,
                    "per_page": per_page,
                    "orientation": "portrait",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "id": v["id"],
                    "url": v["url"],
                    "duration": v["duration"],
                    "video_files": [
                        f
                        for f in v["video_files"]
                        if f.get("quality") == "hd" or f.get("height", 0) <= 1080
                    ],
                }
                for v in data.get("videos", [])
            ]

    def download_video(self, video_url: str, output_path: str) -> str | None:
        """Download a video file from a direct URL.

        Returns:
            The output file path on success, None on failure.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with httpx.Client(timeout=120) as client:
                resp = client.get(video_url)
                resp.raise_for_status()
                path.write_bytes(resp.content)
            return str(path)
        except Exception:
            return None
