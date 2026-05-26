"""Researcher Agent — web search and content research synthesis."""

from typing import Any

from clipper_agency.agents.base import BaseAgent
from clipper_agency.llm.client import OpenRouterClient
from clipper_agency.services.firecrawl_service import FirecrawlService
from clipper_agency.services.scrapecreators import ScrapeCreatorsService

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
    """Researches a topic using web search tools and LLM synthesis."""

    @property
    def agent_name(self) -> str:
        return "researcher"

    def execute(
        self,
        job_id: int,
        topic: str = "",
        safety_rules: list[str] | None = None,
        max_results: int = 5,
        **kwargs: Any,
    ) -> dict[str, Any]:
        rules = safety_rules or []

        firecrawl_data = self._search_firecrawl(topic, max_results)
        scrapecreators_data = self._search_scrapecreators(topic)
        aggregated = self._aggregate_data(firecrawl_data, scrapecreators_data)
        synthesis = self._synthesize_research(aggregated, topic, rules)

        return {
            "status": "completed",
            "research_brief": synthesis["research_brief"],
            "sources": aggregated,
        }

    def _search_firecrawl(self, topic: str, max_results: int) -> list[dict]:
        try:
            service = FirecrawlService()
            return service.search(topic, max_results)
        except Exception:
            return []

    def _search_scrapecreators(self, topic: str) -> list[dict]:
        try:
            service = ScrapeCreatorsService()
            return service.search_tiktok_videos(topic)
        except Exception:
            return []

    def _aggregate_data(
        self, firecrawl_data: list[dict], scrapecreators_data: list[dict]
    ) -> dict[str, Any]:
        firecrawl_count = len(firecrawl_data)
        scrapecreators_count = len(scrapecreators_data)
        total = firecrawl_count + scrapecreators_count
        sources = list(firecrawl_data) + list(scrapecreators_data)
        return {
            "firecrawl_count": firecrawl_count,
            "scrapecreators_count": scrapecreators_count,
            "total_sources": total,
            "sources": sources,
        }

    def _synthesize_research(
        self,
        aggregated: dict[str, Any],
        topic: str,
        safety_rules: list[str],
    ) -> dict[str, Any]:
        sources = aggregated.get("sources", [])
        sources_text = "\n\n".join(str(s) for s in sources)
        rules_text = "\n".join(f"- {r}" for r in safety_rules) if safety_rules else "None"

        llm = OpenRouterClient()
        response = llm.chat(
            model="glm-4-9b",
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
