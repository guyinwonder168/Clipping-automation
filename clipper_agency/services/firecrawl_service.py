"""Firecrawl web search and scrape service."""

import os
from typing import Any

import httpx


class FirecrawlService:
    """Web search and scraping via Firecrawl API."""

    BASE_URL = "https://api.firecrawl.dev/v1"

    def __init__(self) -> None:
        self.api_key = os.getenv("FIRECRAWL_API_KEY")

    def search(
        self, query: str, max_results: int = 5
    ) -> list[dict[str, Any]]:
        """Search the web for content matching the query.

        Returns:
            List of search result dicts with url, title, description, content.
        """
        if not self.api_key:
            raise ValueError("FIRECRAWL_API_KEY not set")

        with httpx.Client(base_url=self.BASE_URL, timeout=30) as client:
            resp = client.post(
                "/search",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"query": query, "maxResults": max_results},
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "url": r.get("url"),
                    "title": r.get("title"),
                    "description": r.get("description"),
                    "content": r.get("content", "")[:2000],
                }
                for r in data.get("data", [])
            ]

    def scrape(self, url: str) -> dict[str, Any] | None:
        """Scrape a single URL and return the extracted content.

        Returns:
            Dict with scraped data on success, None on failure.
        """
        with httpx.Client(base_url=self.BASE_URL, timeout=30) as client:
            resp = client.post(
                "/scrape",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"url": url, "formats": ["markdown"]},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data.get("data")
