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
