"""Tests for VisualDirectorAgent."""

import pytest
from unittest.mock import patch

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
            side_effect=lambda url, base_dir, filename: f"{base_dir}/{filename}",
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


class TestProvenanceTracking:
    """Clip provenance tracking after asset download."""

    def test_provenance_includes_source_dimensions_and_origin(
        self, tmp_path, mocker
    ):
        """Visual Director records per-clip provenance: source, dimensions, timestamp."""
        import json
        from clipper_agency.core.media_probe import VideoInfo

        assets_cache = tmp_path / "assets"
        assets_cache.mkdir(parents=True)

        # Create a real scene file
        scene_file = tmp_path / "scene_1.mp4"
        scene_file.write_bytes(b"x" * 10000)

        # Mock probe_video to return consistent dimensions
        mock_info = VideoInfo(
            path=str(scene_file), width=720, height=1280,
            codec="h264", pix_fmt="yuv420p", duration=5.0,
            has_audio=False, file_size=10000,
        )
        mocker.patch(
            "clipper_agency.agents.visual_director.probe_video",
            return_value=mock_info,
        )

        agent = VisualDirectorAgent()

        # Mock search so we don't hit the API
        mocker.patch.object(agent, "_search_pexels", return_value=[])

        # Mock download to return preset paths
        mocker.patch.object(agent, "_download_assets", return_value=[{
            "scene": 1, "source": "tiktok", "path": str(scene_file),
        }])

        agent.execute(
            job_id=99,
            script=[{"scene": 1, "text": "Intro", "duration": 3}],
            topic="Test",
            output_dir=str(tmp_path / "output"),
            assets_cache=str(assets_cache),
        )

        prov_file = (
            assets_cache / "job_99" / "agents" / "visual_director"
            / "provenance.json"
        )
        assert prov_file.exists()
        data = json.loads(prov_file.read_text())

        assert "clips" in data
        assert "1" in data["clips"]
        clip = data["clips"]["1"]
        assert clip["source"] == "tiktok"
        assert clip["original_width"] == 720
        assert clip["original_height"] == 1280
        assert clip["codec"] == "h264"
        assert clip["duration"] == 5.0
        assert clip["file_size"] == 10000
        assert clip["probed"] is True
        assert clip["probe_error"] is None
        assert "downloaded_at" in clip

    def test_provenance_marks_clip_as_not_probed_when_probe_fails(
        self, tmp_path, mocker
    ):
        """When probe_video returns None, clip is marked probed=False with error note."""
        import json

        assets_cache = tmp_path / "assets"
        assets_cache.mkdir(parents=True)

        scene_file = tmp_path / "scene_1.mp4"
        scene_file.write_bytes(b"x" * 100)

        mocker.patch(
            "clipper_agency.agents.visual_director.probe_video",
            return_value=None,  # probe fails
        )

        agent = VisualDirectorAgent()
        mocker.patch.object(agent, "_search_pexels", return_value=[])
        mocker.patch.object(agent, "_download_assets", return_value=[{
            "scene": 1, "source": "pexels", "path": str(scene_file),
        }])

        agent.execute(
            job_id=100,
            script=[{"scene": 1, "text": "Intro", "duration": 3}],
            topic="Test",
            output_dir=str(tmp_path / "output"),
            assets_cache=str(assets_cache),
        )

        prov_file = (
            assets_cache / "job_100" / "agents" / "visual_director"
            / "provenance.json"
        )
        data = json.loads(prov_file.read_text())

        clip = data["clips"]["1"]
        assert clip["source"] == "pexels"
        assert clip["probed"] is False
        assert clip["probe_error"] == "ffprobe returned no data"
        assert "downloaded_at" in clip

    def test_provenance_skips_empty_paths(self, tmp_path, mocker):
        """Clips with no file path (source=none) are marked probed=false."""
        import json

        assets_cache = tmp_path / "assets"
        assets_cache.mkdir(parents=True)

        probe_mock = mocker.patch(
            "clipper_agency.agents.visual_director.probe_video",
        )

        agent = VisualDirectorAgent()
        mocker.patch.object(agent, "_search_pexels", return_value=[])
        mocker.patch.object(agent, "_download_assets", return_value=[
            {"scene": 1, "source": "none", "path": ""},
        ])

        agent.execute(
            job_id=101,
            script=[{"scene": 1, "text": "No Source", "duration": 3}],
            topic="Test",
            output_dir=str(tmp_path / "output"),
            assets_cache=str(assets_cache),
        )

        prov_file = (
            assets_cache / "job_101" / "agents" / "visual_director"
            / "provenance.json"
        )
        data = json.loads(prov_file.read_text())

        clip = data["clips"]["1"]
        assert clip["source"] == "none"
        assert clip["probed"] is False
        assert clip["probe_error"] == "No file path available"
        probe_mock.assert_not_called()  # probe_video never called for empty path


class TestCompactResearchData:
    """Research data compaction for LLM planning."""

    def test_strips_noise_keeps_signal(self, tmp_path):
        """Compaction strips CDN URLs, music, hashtags, empty content."""
        import json
        agent = VisualDirectorAgent()

        contract = {
            "video_sources": [
                {
                    "url": "https://tiktok.com/@user/v/1",
                    "desc": "Denise Chariesta viral",
                    "plays": 3860000,
                    "likes": 81000,
                    "shares": 4679,
                    "author": "@denise",
                    "music": "some song",
                    "hashtags": ["#viral"],
                    "share_url": "https://share.tiktok.com/1",
                    "video_urls": ["https://cdn.tiktok.com/big.mp4"],
                }
            ],
            "context_sources": [
                {
                    "title": "Insertlive",
                    "description": "Nikita Mirzani goes to court",
                    "url": "https://insertlive.com",
                    "content": "",
                }
            ],
        }
        brief = "# Research Brief\n\nKey facts here."

        contract_path = tmp_path / "research_contract.json"
        contract_path.write_text(json.dumps(contract))
        brief_path = tmp_path / "research_brief.md"
        brief_path.write_text(brief)

        result = agent._compact_research_data(str(contract_path), str(brief_path))

        # Signal preserved
        assert result["video_sources"][0]["url"] == "https://tiktok.com/@user/v/1"
        assert result["video_sources"][0]["desc"] == "Denise Chariesta viral"
        assert result["video_sources"][0]["plays"] == 3860000
        assert result["context_sources"][0]["description"] == "Nikita Mirzani goes to court"
        assert "research_brief" in result

        # Noise stripped
        vs = result["video_sources"][0]
        assert "music" not in vs
        assert "hashtags" not in vs
        assert "share_url" not in vs
        assert "video_urls" not in vs

        cs = result["context_sources"][0]
        assert "url" not in cs
        assert "content" not in cs

    def test_sorts_video_sources_by_engagement(self, tmp_path):
        """Video sources sorted by plays descending."""
        import json
        agent = VisualDirectorAgent()

        contract = {
            "video_sources": [
                {"url": "https://tiktok.com/1", "desc": "low", "plays": 100},
                {"url": "https://tiktok.com/2", "desc": "high", "plays": 5000000},
                {"url": "https://tiktok.com/3", "desc": "mid", "plays": 50000},
            ],
            "context_sources": [],
        }

        contract_path = tmp_path / "research_contract.json"
        contract_path.write_text(json.dumps(contract))

        result = agent._compact_research_data(str(contract_path), "")

        assert result["video_sources"][0]["plays"] == 5000000
        assert result["video_sources"][1]["plays"] == 50000
        assert result["video_sources"][2]["plays"] == 100

    def test_handles_missing_files_gracefully(self):
        """Returns minimal dict when files don't exist."""
        agent = VisualDirectorAgent()
        result = agent._compact_research_data("/nonexistent.json", "/nonexistent.md")
        assert result == {"video_sources": [], "context_sources": []}


class TestPlanWithLLM:
    """LLM-driven visual planning."""

    def test_plan_with_llm_returns_per_scene_plan(self, mocker):
        """LLM returns a valid per-scene visual plan."""
        import json
        agent = VisualDirectorAgent()

        mock_llm_response = {
            "content": json.dumps({
                "scenes": [
                    {
                        "scene_number": 1,
                        "reasoning": "High engagement TikTok clip",
                        "action": {"type": "tiktok_clip", "source_url": "https://tiktok.com/@user/v/1"},
                        "fallback": {"type": "pexels_video", "search_query": "courtroom drama"},
                    },
                    {
                        "scene_number": 2,
                        "reasoning": "No relevant video, use text card",
                        "action": {
                            "type": "text_card",
                            "headline": "BREAKING NEWS",
                            "style": "breaking_news",
                            "image_search": "news anchor desk",
                            "bg_color": "gradient_red",
                        },
                        "fallback": {"type": "text_card", "headline": "UPDATE", "style": "news_card", "image_search": "news"},
                    },
                ]
            }),
            "model": "test-model",
            "usage": {},
        }
        mock_llm = mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient"
        )
        mock_llm.return_value.chat.return_value = mock_llm_response

        mocker.patch(
            "clipper_agency.agents.prompts.load_prompt",
            return_value="You are a Visual Director for {content_angle} content.",
        )
        mocker.patch(
            "clipper_agency.config.loader.load_settings",
        )

        scenes = [
            {"scene": 1, "text": "Hook about viral video", "duration": 5},
            {"scene": 2, "text": "Breaking news reveal", "duration": 4},
        ]
        compact_data = {
            "video_sources": [{"url": "https://tiktok.com/@user/v/1", "plays": 3860000}],
            "context_sources": [],
        }

        plan = agent._plan_with_llm(scenes, compact_data)

        assert len(plan) == 2
        assert plan[0]["action"]["type"] == "tiktok_clip"
        assert plan[1]["action"]["type"] == "text_card"

    def test_plan_with_llm_falls_back_on_invalid_json(self, mocker):
        """If LLM returns garbage, _plan_with_llm returns None (caller handles fallback)."""
        import json
        agent = VisualDirectorAgent()

        mock_llm = mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient"
        )
        mock_llm.return_value.chat.return_value = {
            "content": "NOT JSON AT ALL {{{",
            "model": "test",
            "usage": {},
        }
        mocker.patch(
            "clipper_agency.agents.prompts.load_prompt",
            return_value="You are a Visual Director.",
        )
        mocker.patch(
            "clipper_agency.config.loader.load_settings",
        )

        scenes = [{"scene": 1, "text": "Test", "duration": 5}]
        compact_data = {"video_sources": [], "context_sources": []}

        plan = agent._plan_with_llm(scenes, compact_data)

        # Returns None so caller (_run_llm_planning) routes to _download_assets
        assert plan is None


class TestExecutePlan:
    """LLM plan execution with image fallback chain."""

    def test_execute_tiktok_clip(self, mocker, tmp_path):
        """tiktok_clip action downloads via yt-dlp."""
        from clipper_agency.services.ytdlp import DownloadResult
        agent = VisualDirectorAgent()
        mock_ytdlp = mocker.patch(
            "clipper_agency.agents.visual_director.YtDlpService"
        )
        mock_ytdlp.return_value.download.return_value = DownloadResult(
            path=str(tmp_path / "scene_1.mp4")
        )

        plan = [{
            "scene_number": 1,
            "action": {"type": "tiktok_clip", "source_url": "https://tiktok.com/v/1"},
        }]
        result = agent._execute_plan(plan, str(tmp_path))
        assert result[0]["source"] == "tiktok_clip"
        assert result[0]["path"] == str(tmp_path / "scene_1.mp4")

    def test_execute_pexels_video(self, mocker, tmp_path):
        """pexels_video action searches and downloads."""
        agent = VisualDirectorAgent()
        mock_pexels = mocker.patch(
            "clipper_agency.agents.visual_director.PexelsService"
        )
        mock_pexels.return_value.search_videos.return_value = [
            {"id": 1, "video_files": [{"link": "https://video.pexels.com/1.mp4"}]},
        ]
        mock_pexels.return_value.download_video.return_value = str(tmp_path / "scene_1.mp4")

        plan = [{
            "scene_number": 1,
            "action": {"type": "pexels_video", "search_query": "courtroom"},
        }]
        result = agent._execute_plan(plan, str(tmp_path))
        assert result[0]["source"] == "pexels_video"

    def test_execute_text_card_with_pexels_image(self, mocker, tmp_path):
        """text_card action finds image via Pexels first."""
        agent = VisualDirectorAgent()
        mock_pexels = mocker.patch(
            "clipper_agency.agents.visual_director.PexelsService"
        )
        mock_pexels.return_value.search_photos.return_value = [
            {"id": 1, "src": {"medium": "https://images.pexels.com/1.jpg"}},
        ]
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_image_data"
        mock_response.raise_for_status = mocker.MagicMock()
        with patch("httpx.Client") as MockClient:
            mock_client = mocker.MagicMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__enter__ = lambda s: mock_client
            MockClient.return_value.__exit__ = mocker.MagicMock(return_value=False)

            plan = [{
                "scene_number": 1,
                "action": {
                    "type": "text_card",
                    "headline": "BREAKING",
                    "style": "breaking_news",
                    "image_search": "news desk",
                    "bg_color": "gradient_red",
                },
            }]
            result = agent._execute_plan(plan, str(tmp_path))
            assert result[0]["source"] == "text_card"
            assert result[0]["path"] != ""

    def test_execute_uses_fallback_on_failure(self, mocker, tmp_path):
        """When primary action fails, fallback is used."""
        from clipper_agency.services.ytdlp import DownloadResult
        agent = VisualDirectorAgent()
        mock_ytdlp = mocker.patch(
            "clipper_agency.agents.visual_director.YtDlpService"
        )
        mock_ytdlp.return_value.download.return_value = None  # TikTok fails

        mock_pexels = mocker.patch(
            "clipper_agency.agents.visual_director.PexelsService"
        )
        mock_pexels.return_value.search_videos.return_value = [
            {"id": 1, "video_files": [{"link": "https://video.pexels.com/1.mp4"}]},
        ]
        mock_pexels.return_value.download_video.return_value = str(tmp_path / "scene_1.mp4")

        plan = [{
            "scene_number": 1,
            "action": {"type": "tiktok_clip", "source_url": "https://tiktok.com/v/1"},
            "fallback": {"type": "pexels_video", "search_query": "drama"},
        }]
        result = agent._execute_plan(plan, str(tmp_path))
        assert result[0]["source"] == "pexels_video"  # fell back


class TestLLMPlanningIntegration:
    """Full execute() flow with LLM planning."""

    def test_execute_uses_llm_when_research_paths_provided(self, mocker, tmp_path):
        """When research_contract_path is provided, LLM planning is used."""
        import json

        contract = {
            "video_sources": [
                {"url": "https://tiktok.com/@user/v/1", "desc": "viral", "plays": 1000000},
            ],
            "context_sources": [],
        }
        contract_path = tmp_path / "research_contract.json"
        contract_path.write_text(json.dumps(contract))
        brief_path = tmp_path / "research_brief.md"
        brief_path.write_text("# Brief")

        mock_llm = mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient"
        )
        mock_llm.return_value.chat.return_value = {
            "content": json.dumps({
                "scenes": [
                    {
                        "scene_number": 1,
                        "reasoning": "Use viral TikTok",
                        "action": {"type": "pexels_video", "search_query": "drama"},
                        "fallback": {"type": "text_card", "headline": "NEWS", "style": "news_card", "image_search": "news"},
                    }
                ]
            }),
            "model": "test",
            "usage": {},
        }
        mocker.patch(
            "clipper_agency.agents.prompts.load_prompt",
            return_value="You are a Visual Director.",
        )
        mocker.patch(
            "clipper_agency.config.loader.load_settings",
        )

        mocker.patch(
            "clipper_agency.services.pexels.PexelsService.search_videos",
            return_value=[{"id": 1, "video_files": [{"link": "https://video.pexels.com/1.mp4"}]}],
        )
        mocker.patch(
            "clipper_agency.services.pexels.PexelsService.download_video",
            return_value=str(tmp_path / "scene_1.mp4"),
        )

        agent = VisualDirectorAgent()
        result = agent.execute(
            job_id=1,
            script=[{"scene": 1, "text": "Hook", "duration": 5}],
            topic="Test topic",
            output_dir=str(tmp_path),
            research_contract_path=str(contract_path),
            research_brief_path=str(brief_path),
        )

        assert result["status"] == "completed"
        assert len(result["assets"]) == 1


class TestCoverageGaps:
    """Targeted tests for uncovered branches to reach ≥90% coverage."""

    def test_compact_research_data_brief_not_found(self, tmp_path):
        """Contract exists but brief file doesn't — except path covered."""
        import json
        agent = VisualDirectorAgent()
        contract = {"video_sources": [], "context_sources": []}
        contract_path = tmp_path / "research_contract.json"
        contract_path.write_text(json.dumps(contract))

        result = agent._compact_research_data(str(contract_path), "/nonexistent/brief.md")
        assert result["video_sources"] == []
        # brief_path FileNotFoundError caught, no research_brief key
        assert "research_brief" not in result

    def test_compact_research_data_empty_brief(self, tmp_path):
        """Contract exists, brief exists but is whitespace-only."""
        import json
        agent = VisualDirectorAgent()
        contract = {"video_sources": [], "context_sources": []}
        contract_path = tmp_path / "research_contract.json"
        contract_path.write_text(json.dumps(contract))
        brief_path = tmp_path / "brief.md"
        brief_path.write_text("   \n\n  ")

        result = agent._compact_research_data(str(contract_path), str(brief_path))
        assert "research_brief" not in result  # stripped to empty → falsy

    def test_execute_action_empty_url_returns_none(self, mocker):
        """tiktok_clip with empty source_url returns None."""
        agent = VisualDirectorAgent()
        mocker.patch("clipper_agency.agents.visual_director.YtDlpService")
        result = agent._execute_action(
            {"type": "tiktok_clip", "source_url": ""}, 1, "/tmp", mocker.MagicMock(), mocker.MagicMock(),
        )
        assert result is None

    def test_execute_action_empty_query_returns_none(self, mocker):
        """pexels_video with empty search_query returns None."""
        agent = VisualDirectorAgent()
        mocker.patch("clipper_agency.agents.visual_director.PexelsService")
        result = agent._execute_action(
            {"type": "pexels_video", "search_query": ""}, 1, "/tmp", mocker.MagicMock(), mocker.MagicMock(),
        )
        assert result is None

    def test_execute_action_unknown_type_returns_none(self, mocker):
        """Unknown action type returns None."""
        agent = VisualDirectorAgent()
        result = agent._execute_action(
            {"type": "unknown_type"}, 1, "/tmp", mocker.MagicMock(), mocker.MagicMock(),
        )
        assert result is None

    def test_execute_plan_both_fail_yields_none(self, mocker, tmp_path):
        """Both action and fallback fail → source 'none'."""
        agent = VisualDirectorAgent()
        mocker.patch(
            "clipper_agency.agents.visual_director.YtDlpService",
        ).return_value.download.return_value = None
        mocker.patch(
            "clipper_agency.agents.visual_director.PexelsService",
        ).return_value.search_videos.return_value = []

        plan = [{
            "scene_number": 1,
            "action": {"type": "tiktok_clip", "source_url": "https://tiktok.com/v/1"},
            "fallback": {"type": "pexels_video", "search_query": "drama"},
        }]
        result = agent._execute_plan(plan, str(tmp_path))
        assert result[0]["source"] == "none"
        assert result[0]["path"] == ""

    def test_fetch_image_no_results(self, mocker, tmp_path):
        """_fetch_image returns None when Pexels has no results."""
        agent = VisualDirectorAgent()
        mock_pexels = mocker.MagicMock()
        mock_pexels.search_photos.return_value = []
        result = agent._fetch_image("obscure query", 1, str(tmp_path), mock_pexels)
        assert result is None

    def test_fetch_image_download_fails(self, mocker, tmp_path):
        """_fetch_image returns None when image download fails."""
        agent = VisualDirectorAgent()
        mock_pexels = mocker.MagicMock()
        mock_pexels.search_photos.return_value = [
            {"id": 1, "src": {"medium": "https://images.pexels.com/broken.jpg"}},
        ]
        with patch("httpx.Client") as MockClient:
            mock_client = mocker.MagicMock()
            mock_client.get.side_effect = Exception("network error")
            MockClient.return_value.__enter__ = lambda s: mock_client
            MockClient.return_value.__exit__ = mocker.MagicMock(return_value=False)
            result = agent._fetch_image("query", 1, str(tmp_path), mock_pexels)
            assert result is None
