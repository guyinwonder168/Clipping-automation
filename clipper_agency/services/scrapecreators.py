"""ScrapeCreators TikTok data service."""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ScrapeCreatorsService:
    """Search TikTok videos via ScrapeCreators API.

    Returns *structured* results with only the fields the pipeline needs,
    not the raw 1-2MB TikTok ``aweme_info`` payloads.
    """

    BASE_URL = "https://api.scrapecreators.com/v1"
    MAX_RESULTS = 20
    MAX_CHARS_PER_DESC = 300

    def __init__(self) -> None:
        self.api_key = os.getenv("SCRAPECREATORS_API_KEY")

    def search_tiktok_videos(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        """Search TikTok for videos matching the query.

        Uses ``trim=true`` for smaller responses and extracts only
        essential fields: description, author, engagement, video URLs,
        music metadata, and hashtags.

        Returns:
            List of structured dicts (one per video).
        """
        if not self.api_key:
            raise ValueError("SCRAPECREATORS_API_KEY not set")

        logger.info("ScrapeCreators: searching TikTok (query=%d chars)", len(query))

        with httpx.Client(base_url=self.BASE_URL, timeout=30) as client:
            resp = client.get(
                "/tiktok/search/keyword",
                headers={"x-api-key": self.api_key},
                params={
                    "query": query,
                    "trim": "true",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            raw_items = data.get("search_item_list", [])

        logger.info(
            "ScrapeCreators: %d raw results (trim=true), extracting fields",
            len(raw_items),
        )

        extracted = []
        for item in raw_items[:self.MAX_RESULTS]:
            result = self._extract_fields(item)
            if result:
                extracted.append(result)

        logger.debug(
            "ScrapeCreators: %d extracted results (%d chars total)",
            len(extracted),
            sum(len(str(r)) for r in extracted),
        )
        return extracted

    def _extract_fields(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """Extract only pipeline-relevant fields from a raw TikTok item."""
        aweme = item.get("aweme_info", {})
        if not aweme:
            return None

        desc = aweme.get("desc", "")
        if desc:
            desc = desc[:self.MAX_CHARS_PER_DESC]

        # Video download URLs (best quality first)
        video_urls: dict[str, str] = {}
        video = aweme.get("video", {})
        bit_rates = video.get("bit_rate", []) or []
        for br in bit_rates:
            url_list = br.get("play_addr", {}).get("url_list", [])
            if url_list:
                gear = br.get("gear_name") or ""
                quality = br.get("quality_type") or ""
                label = gear or (f"{quality}p" if quality else "default")
                video_urls[label] = url_list[0]

        # Music / audio metadata
        music = aweme.get("music", {})
        music_info: dict[str, str] = {}
        if music:
            music_info = {
                "title": music.get("title", ""),
                "author": music.get("author", ""),
            }

        # Statistics
        stats = aweme.get("statistics", {}) or {}

        # Hashtags
        hashtags = [
            c.get("cha_name", "")
            for c in (aweme.get("cha_list", []) or [])
            if c.get("cha_name")
        ]

        share_url = aweme.get("share_url", "")

        return {
            "desc": desc,
            "author": (aweme.get("author", {}) or {}).get("unique_id", ""),
            "likes": stats.get("digg_count", 0),
            "comments": stats.get("comment_count", 0),
            "shares": stats.get("share_count", 0),
            "plays": stats.get("play_count", 0),
            "url": share_url,           # orchestrator reads this key for source_urls
            "share_url": share_url,
            "video_urls": video_urls,
            "music": music_info,
            "hashtags": hashtags,
        }
