"""Researcher Agent — web search and content research synthesis."""

import json
import logging
import os
from typing import Any

from clipper_agency.agents.base import BaseAgent
from clipper_agency.config.loader import load_settings
from clipper_agency.core.paths import (
    ensure_research_cache_dir,
    firecrawl_cache_file,
    research_brief_cache_file,
    scrapecreators_cache_file,
)
from clipper_agency.llm.client import OpenRouterClient
from clipper_agency.services.firecrawl_service import FirecrawlService
from clipper_agency.services.scrapecreators import ScrapeCreatorsService

logger = logging.getLogger(__name__)

# ── token guard ──────────────────────────────────────────────────────────────
# Prevent LLM context overflow from overly large search results.
MAX_SOURCE_CHARS = 40_000  # ~10K tokens worth of text
MAX_CHARS_PER_SOURCE = 500


RESEARCH_PROMPT = """You are a research assistant for a TikTok content creator.
Analyze the provided search results and create a concise research brief.

Rules to follow:
{rules_text}

Search results:
{sources_text}

Return a concise research brief that covers:
1. Key facts and verified information
2. Trending angles and viral potential
3. Content suggestions for TikTok
4. Any risks or sensitive topics to handle carefully
"""


class ResearcherAgent(BaseAgent):
    """Researches a topic using web search tools and LLM synthesis.

    Caches ScrapeCreators and Firecrawl API responses per job so
    expensive API calls are only made once per topic/job run.
    """

    @property
    def agent_name(self) -> str:
        return "researcher"

    def execute(
        self,
        job_id: int,
        topic: str = "",
        safety_rules: list[str] | None = None,
        max_results: int = 5,
        output_dir: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        rules = safety_rules or []
        ensure_research_cache_dir(output_dir, job_id)

        # ── 1. Gather sources (cached or live) ──────────────────────────
        scrapecreators_data = self._get_scrapecreators(topic, output_dir, job_id)
        firecrawl_data = self._get_firecrawl(topic, max_results, output_dir, job_id)
        aggregated = self._aggregate_data(firecrawl_data, scrapecreators_data)

        # ── 2. Synthesize research brief (cached or live LLM) ───────────
        brief = self._get_research_brief(aggregated, topic, rules, output_dir, job_id)

        return {
            "status": "completed",
            "research_brief": brief,
            "sources": aggregated,
        }

    # ── source gathering (with cache) ───────────────────────────────────────

    def _get_scrapecreators(
        self, topic: str, output_dir: str, job_id: int
    ) -> list[dict]:
        cache_path = scrapecreators_cache_file(output_dir, job_id)

        if os.path.exists(cache_path):
            logger.info("Researcher: ScrapeCreators cache HIT (%s)", cache_path)
            with open(cache_path) as fh:
                return json.load(fh)

        logger.info("Researcher: ScrapeCreators cache MISS — calling API")
        try:
            service = ScrapeCreatorsService()
            data = service.search_tiktok_videos(topic)
            with open(cache_path, "w") as fh:
                json.dump(data, fh, indent=2)
            logger.debug("Researcher: saved %d results to %s", len(data), cache_path)
            return data
        except Exception:
            logger.exception("Researcher: ScrapeCreators API failed")
            return []

    def _get_firecrawl(
        self, topic: str, max_results: int, output_dir: str, job_id: int
    ) -> list[dict]:
        cache_path = firecrawl_cache_file(output_dir, job_id)

        if os.path.exists(cache_path):
            logger.info("Researcher: Firecrawl cache HIT (%s)", cache_path)
            with open(cache_path) as fh:
                return json.load(fh)

        logger.info("Researcher: Firecrawl cache MISS — calling API")
        try:
            service = FirecrawlService()
            data = service.search(topic, max_results)
            # Strip large content fields for caching; keep url/title/desc
            lean = [
                {
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "description": r.get("description", ""),
                }
                for r in data
            ]
            with open(cache_path, "w") as fh:
                json.dump(lean, fh, indent=2)
            logger.debug("Researcher: saved %d Firecrawl results to %s", len(lean), cache_path)
            return lean
        except Exception:
            logger.exception("Researcher: Firecrawl API failed")
            return []

    # ── research brief synthesis (with cache + token guard) ─────────────────

    def _get_research_brief(
        self,
        aggregated: dict[str, Any],
        topic: str,
        safety_rules: list[str],
        output_dir: str,
        job_id: int,
    ) -> str:
        cache_path = research_brief_cache_file(output_dir, job_id)

        if os.path.exists(cache_path):
            logger.info("Researcher: research_brief cache HIT (%s)", cache_path)
            with open(cache_path) as fh:
                return json.load(fh)["research_brief"]

        logger.info("Researcher: research_brief cache MISS — calling LLM")
        result = self._synthesize_research(aggregated, topic, safety_rules)
        brief = result["research_brief"]

        with open(cache_path, "w") as fh:
            json.dump({"research_brief": brief}, fh, indent=2)
        logger.debug("Researcher: saved research_brief to %s", cache_path)
        return brief

    # ── helpers ─────────────────────────────────────────────────────────────

    def _aggregate_data(
        self, firecrawl_data: list[dict], scrapecreators_data: list[dict]
    ) -> dict[str, Any]:
        sources = list(firecrawl_data) + list(scrapecreators_data)
        return {
            "firecrawl_count": len(firecrawl_data),
            "scrapecreators_count": len(scrapecreators_data),
            "total_sources": len(sources),
            "sources": sources,
        }

    def _synthesize_research(
        self,
        aggregated: dict[str, Any],
        topic: str,
        safety_rules: list[str],
    ) -> dict[str, Any]:
        sources = aggregated.get("sources", [])

        # ── token guard: truncate per-source and total ──────────────────
        trimmed: list[str] = []
        total_chars = 0
        for s in sources:
            text = str(s)[:MAX_CHARS_PER_SOURCE]
            trimmed.append(text)
            total_chars += len(text)
            if total_chars >= MAX_SOURCE_CHARS:
                logger.warning(
                    "Researcher: source text truncated at %d chars "
                    "(%d of %d sources used to avoid LLM context overflow)",
                    total_chars,
                    len(trimmed),
                    len(sources),
                )
                break

        sources_text = "\n\n".join(trimmed)
        rules_text = "\n".join(f"- {r}" for r in safety_rules) if safety_rules else "None"

        logger.info(
            "Researcher: synthesizing research "
            "(%d sources, %d chars of text)",
            len(trimmed),
            len(sources_text),
        )

        settings = load_settings()
        llm = OpenRouterClient()
        response = llm.chat(
            model=settings.researcher_model,
            messages=[
                {
                    "role": "system",
                    "content": RESEARCH_PROMPT.format(
                        rules_text=rules_text, sources_text=sources_text
                    ),
                },
                {
                    "role": "user",
                    "content": f"Research topic: {topic}",
                },
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        return {
            "research_brief": response["content"],
            "source_count": len(sources),
        }
