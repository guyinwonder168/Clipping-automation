"""Tests for VisualDirectorAgent."""

import pytest

from clipper_agency.agents.visual_director import VisualDirectorAgent


class TestVisualDirectorName:
    """Agent name property."""

    def test_visual_director_agent_name(self):
        agent = VisualDirectorAgent()
        assert agent.agent_name == "visual_director"


class TestVisualDirectorPlanScenes:
    """Scene planning logic."""

    def test_plan_scenes_assigns_sources(self):
        agent = VisualDirectorAgent()
        scenes = [
            {"scene": 1, "text": "Hook", "duration": 3},
            {"scene": 2, "text": "Body", "duration": 5},
            {"scene": 3, "text": "CTA", "duration": 2},
        ]
        urls = ["https://tiktok.com/v/1"]
        pexels = [
            {"id": 1, "video_files": [{"link": "https://video.pexels.com/1.mp4"}]},
            {"id": 2, "video_files": [{"link": "https://video.pexels.com/2.mp4"}]},
        ]
        plan = agent._plan_scenes(scenes, urls, pexels)
        assert len(plan) == 3
        # First scene gets a tiktok URL, rest get pexels fallback
        assert plan[0]["source"] == "tiktok"
        assert plan[0]["url"] == "https://tiktok.com/v/1"
        for i in range(1, 3):
            assert plan[i]["source"] == "pexels"
            assert plan[i]["url"].startswith("https://video.pexels.com/")

    def test_plan_scenes_all_pexels_when_no_urls(self):
        agent = VisualDirectorAgent()
        scenes = [{"scene": 1, "text": "Intro", "duration": 3}]
        pexels = [{"id": 1, "video_files": [{"link": "https://video.pexels.com/1.mp4"}]}]
        plan = agent._plan_scenes(scenes, [], pexels)
        assert plan[0]["source"] == "pexels"

    def test_plan_scenes_empty_scenes(self):
        agent = VisualDirectorAgent()
        plan = agent._plan_scenes([], [], [])
        assert plan == []


class TestVisualDirectorExecute:
    """Full execute() with mocked services."""

    def test_execute_downloads_and_returns_assets(self, mocker):
        mocker.patch(
            "clipper_agency.services.pexels.PexelsService.search_videos",
            return_value=[
                {"id": 1, "video_files": [{"link": "https://video.pexels.com/1.mp4"}]},
                {"id": 2, "video_files": [{"link": "https://video.pexels.com/2.mp4"}]},
            ],
        )
        mocker.patch(
            "clipper_agency.services.pexels.PexelsService.download_video",
            side_effect=lambda url, path: f"{path}/video_{url[-5:]}.mp4",
        )
        mocker.patch(
            "clipper_agency.services.ytdlp.YtDlpService.download",
            return_value=None,  # No TikTok URLs in this test
        )

        agent = VisualDirectorAgent()
        result = agent.execute(
            job_id=4,
            script=[
                {"scene": 1, "text": "Intro", "duration": 3},
                {"scene": 2, "text": "Body", "duration": 5},
            ],
            topic="Ariana Grande",
            output_dir="/tmp/output",
        )
        assert result["status"] == "completed"
        assert "assets" in result
        assert len(result["assets"]) == 2

    def test_execute_searches_pexels_with_topic(self, mocker):
        mock_search = mocker.patch(
            "clipper_agency.services.pexels.PexelsService.search_videos",
            return_value=[
                {"id": 1, "video_files": [{"link": "https://video.pexels.com/1.mp4"}]},
            ],
        )
        mocker.patch(
            "clipper_agency.services.pexels.PexelsService.download_video",
            return_value="/tmp/output/fake.mp4",
        )
        mocker.patch(
            "clipper_agency.services.ytdlp.YtDlpService.download",
            return_value=None,
        )

        agent = VisualDirectorAgent()
        agent.execute(
            job_id=4,
            script=[{"scene": 1, "text": "Test", "duration": 3}],
            topic="K-pop",
            output_dir="/tmp/output",
        )
        mock_search.assert_called_once_with("K-pop", per_page=10)

    def test_execute_handles_no_assets_found(self, mocker):
        mocker.patch(
            "clipper_agency.services.pexels.PexelsService.search_videos",
            return_value=[],
        )
        mocker.patch(
            "clipper_agency.services.ytdlp.YtDlpService.download",
            return_value=None,
        )

        agent = VisualDirectorAgent()
        result = agent.execute(
            job_id=4,
            script=[{"scene": 1, "text": "Test", "duration": 3}],
            topic="Topic",
            output_dir="/tmp/output",
        )
        assert result["status"] == "completed"
        assert result["assets"] == [{"scene": 1, "source": "none", "path": ""}]

    def test_execute_handles_service_failure(self, mocker):
        mocker.patch(
            "clipper_agency.services.pexels.PexelsService.search_videos",
            side_effect=Exception("Pexels API error"),
        )
        mocker.patch(
            "clipper_agency.services.ytdlp.YtDlpService.download",
            return_value=None,
        )

        agent = VisualDirectorAgent()
        result = agent.execute(
            job_id=4,
            script=[{"scene": 1, "text": "Test", "duration": 3}],
            topic="Topic",
            output_dir="/tmp/output",
        )
        assert result["status"] == "failed"
        assert "error" in result
