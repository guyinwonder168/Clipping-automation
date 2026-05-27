"""Tests for ResearcherAgent."""

from unittest.mock import MagicMock
import pytest

from clipper_agency.agents.researcher import ResearcherAgent


class TestResearcherName:
    """Agent name property."""

    def test_researcher_agent_name(self):
        agent = ResearcherAgent()
        assert agent.agent_name == "researcher"


class TestResearcherAggregateData:
    """Aggregating search results from multiple sources."""

    def test_aggregate_combines_sources(self):
        agent = ResearcherAgent()
        firecrawl_data = [
            {
                "title": "Article 1",
                "url": "https://example.com/1",
                "content": "Some content",
            },
            {
                "title": "Article 2",
                "url": "https://example.com/2",
                "content": "More content",
            },
        ]
        scrapecreators_data = [
            {
                "title": "TikTok Post 1",
                "url": "https://tiktok.com/@user/video/1",
                "play_count": 5000,
            },
        ]
        result = agent._aggregate_data(firecrawl_data, scrapecreators_data)
        assert result["firecrawl_count"] == 2
        assert result["scrapecreators_count"] == 1
        assert result["total_sources"] == 3
        assert len(result["sources"]) == 3

    def test_aggregate_handles_empty(self):
        agent = ResearcherAgent()
        result = agent._aggregate_data([], [])
        assert result["firecrawl_count"] == 0
        assert result["scrapecreators_count"] == 0
        assert result["total_sources"] == 0
        assert result["sources"] == []


class TestResearcherSynthesize:
    """LLM-powered research synthesis."""

    @staticmethod
    def _mock_chat(content: str) -> dict:
        return {"content": content, "model": "glm-4-9b", "usage": {}}

    def test_synthesize_returns_brief_and_sources(self, mocker):
        mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat("Research brief: Some analysis"),
        )
        agent = ResearcherAgent()
        aggregated = {
            "firecrawl_count": 1,
            "scrapecreators_count": 1,
            "total_sources": 2,
            "sources": [
                {"title": "Art 1", "url": "https://a.com", "content": "Data"},
                {"title": "TK 1", "url": "https://b.com", "play_count": 1000},
            ],
        }
        result = agent._synthesize_research(aggregated, "Test topic", [])
        assert result["research_brief"] == "Research brief: Some analysis"
        assert result["source_count"] == 2

    def test_synthesize_passes_topic_and_rules(self, mocker):
        mock_chat = mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat("Brief content"),
        )
        agent = ResearcherAgent()
        aggregated = {
            "firecrawl_count": 1,
            "scrapecreators_count": 0,
            "total_sources": 1,
            "sources": [{"title": "Art 1", "url": "https://a.com", "content": "X"}],
        }
        agent._synthesize_research(
            aggregated,
            "Ariana Grande",
            ["mark_rumors_as_unconfirmed"],
        )
        messages = mock_chat.call_args.kwargs["messages"]
        system_content = messages[0]["content"]
        user_content = messages[1]["content"]
        assert "Ariana Grande" in user_content
        assert "mark_rumors_as_unconfirmed" in system_content

    def test_synthesize_model_and_temperature(self, mocker):
        mock_chat = mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat("Brief"),
        )
        agent = ResearcherAgent()
        aggregated = {
            "firecrawl_count": 0,
            "scrapecreators_count": 0,
            "total_sources": 0,
            "sources": [],
        }
        agent._synthesize_research(aggregated, "Topic", [])
        assert mock_chat.call_args.kwargs["model"] == "mimo-v2-flash"
        assert mock_chat.call_args.kwargs["temperature"] == 0.3


class TestResearcherExecute:
    """Full execute() with mocked services and LLM."""

    @staticmethod
    def _mock_chat(content: str) -> dict:
        return {"content": content, "model": "glm-4-9b", "usage": {}}

    @staticmethod
    def _mock_firecrawl_results():
        return [
            {
                "title": "Search Result 1",
                "url": "https://example.com/1",
                "content": "Content from search",
            },
            {
                "title": "Search Result 2",
                "url": "https://example.com/2",
                "content": "More content",
            },
        ]

    @staticmethod
    def _mock_scrapecreators_results():
        return [
            {
                "title": "Viral TikTok",
                "url": "https://tiktok.com/@creator/video/999",
                "play_count": 10000,
                "like_count": 500,
            },
        ]

    def test_execute_returns_research_package(self, mocker, tmp_path):
        mocker.patch(
            "clipper_agency.services.firecrawl_service.FirecrawlService.search",
            return_value=self._mock_firecrawl_results(),
        )
        mocker.patch(
            "clipper_agency.services.scrapecreators.ScrapeCreatorsService.search_tiktok_videos",
            return_value=self._mock_scrapecreators_results(),
        )
        mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat("Research brief: Comprehensive analysis"),
        )
        agent = ResearcherAgent()
        result = agent.execute(
            job_id=2,
            topic="K-pop trends",
            output_dir=str(tmp_path),
        )
        assert result["status"] == "completed"
        assert result["research_brief"] == "Research brief: Comprehensive analysis"
        assert "sources" in result
        assert result["sources"]["firecrawl_count"] == 2
        assert result["sources"]["scrapecreators_count"] == 1

    def test_execute_handles_firecrawl_failure(self, mocker, tmp_path):
        mocker.patch(
            "clipper_agency.services.firecrawl_service.FirecrawlService.search",
            side_effect=Exception("Firecrawl error"),
        )
        mocker.patch(
            "clipper_agency.services.scrapecreators.ScrapeCreatorsService.search_tiktok_videos",
            return_value=self._mock_scrapecreators_results(),
        )
        mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat("Partial research brief"),
        )
        agent = ResearcherAgent()
        result = agent.execute(job_id=2, topic="Test", output_dir=str(tmp_path))
        assert result["status"] == "completed"
        assert result["sources"]["firecrawl_count"] == 0
        assert result["sources"]["scrapecreators_count"] == 1

    def test_execute_handles_scrapecreators_failure(self, mocker, tmp_path):
        mocker.patch(
            "clipper_agency.services.firecrawl_service.FirecrawlService.search",
            return_value=self._mock_firecrawl_results(),
        )
        mocker.patch(
            "clipper_agency.services.scrapecreators.ScrapeCreatorsService.search_tiktok_videos",
            side_effect=Exception("ScrapeCreators error"),
        )
        mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat("Partial research brief"),
        )
        agent = ResearcherAgent()
        result = agent.execute(job_id=2, topic="Test", output_dir=str(tmp_path))
        assert result["status"] == "completed"
        assert result["sources"]["firecrawl_count"] == 2
        assert result["sources"]["scrapecreators_count"] == 0

    def test_execute_handles_total_failure(self, mocker, tmp_path):
        mocker.patch(
            "clipper_agency.services.firecrawl_service.FirecrawlService.search",
            side_effect=Exception("Firecrawl error"),
        )
        mocker.patch(
            "clipper_agency.services.scrapecreators.ScrapeCreatorsService.search_tiktok_videos",
            side_effect=Exception("ScrapeCreators error"),
        )
        mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat("Minimal brief from LLM knowledge"),
        )
        agent = ResearcherAgent()
        result = agent.execute(job_id=2, topic="Test", output_dir=str(tmp_path))
        assert result["status"] == "completed"
        assert result["sources"]["total_sources"] == 0

    def test_execute_uses_max_results_param(self, mocker, tmp_path):
        mock_search = mocker.patch(
            "clipper_agency.services.firecrawl_service.FirecrawlService.search",
            return_value=[{
                "title": "X", "url": "https://x.com", "content": "Y",
            }],
        )
        mocker.patch(
            "clipper_agency.services.scrapecreators.ScrapeCreatorsService.search_tiktok_videos",
            return_value=[],
        )
        mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat("Brief"),
        )
        agent = ResearcherAgent()
        agent.execute(job_id=2, topic="Test", max_results=3, output_dir=str(tmp_path))
        mock_search.assert_called_once_with("Test", 3)
