"""ScrapeCreators TikTok data service."""

import os
from typing import Any

import httpx


class ScrapeCreatorsService:
    """Search TikTok videos via ScrapeCreators API."""

    BASE_URL = "https://api.scrapecreators.com/v1"

    def __init__(self) -> None:
        self.api_key = os.getenv("SCRAPECREATORS_API_KEY")

    def search_tiktok_videos(
        self, query: str, max_results: int = 5
    ) -> list[dict[str, Any]]:
        """Search TikTok for videos matching the query.

        Returns:
            List of video metadata dicts.
        """
        if not self.api_key:
            raise ValueError("SCRAPECREATORS_API_KEY not set")

        with httpx.Client(base_url=self.BASE_URL, timeout=30) as client:
            resp = client.get(
                "/tiktok/search/keyword",
                headers={"x-api-key": self.api_key},
                params={"query": query},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("search_item_list", [])
