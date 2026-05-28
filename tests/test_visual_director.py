"""Tests for VisualDirectorAgent artifact persistence."""

import json
from pathlib import Path
from unittest import mock

import pytest

from clipper_agency.agents.visual_director import VisualDirectorAgent


SCENES = [
    {"scene": 1, "text": "Intro", "duration": 3},
    {"scene": 2, "text": "Body", "duration": 5},
]


def _setup_mocks(mocker):
    """Mock Pexels search and download for a happy path."""
    mocker.patch(
        "clipper_agency.services.pexels.PexelsService.search_videos",
        return_value=[
            {"id": 1, "video_files": [{"link": "https://pexels.mp4/1"}]},
            {"id": 2, "video_files": [{"link": "https://pexels.mp4/2"}]},
        ],
    )
    mocker.patch(
        "clipper_agency.services.pexels.PexelsService.download_video",
        side_effect=lambda url, path: path,
    )
    mocker.patch(
        "clipper_agency.services.ytdlp.YtDlpService.download",
        return_value=None,
    )


class TestVisualDirectorArtifacts:
    """Visual Director writes input/output, scene_plan, provenance to agent dir."""

    def test_persists_input_json(self, tmp_path, mocker):
        _setup_mocks(mocker)
        agent = VisualDirectorAgent()
        agent.execute(
            job_id=20,
            script=SCENES,
            topic="Test",
            source_urls=[],
            assets_cache=str(tmp_path),
        )

        input_file = tmp_path / "job_20" / "agents" / "visual_director" / "input.json"
        assert input_file.exists()
        data = json.loads(input_file.read_text())
        assert data["job_id"] == 20
        assert data["scene_count"] == 2
        assert data["topic"] == "Test"

    def test_persists_scene_plan_json(self, tmp_path, mocker):
        _setup_mocks(mocker)
        agent = VisualDirectorAgent()
        agent.execute(
            job_id=21,
            script=SCENES,
            topic="Test",
            source_urls=[],
            assets_cache=str(tmp_path),
        )

        plan_file = tmp_path / "job_21" / "agents" / "visual_director" / "scene_plan.json"
        assert plan_file.exists()
        data = json.loads(plan_file.read_text())
        assert len(data) == 2
        assert all("scene" in item for item in data)

    def test_persists_output_json(self, tmp_path, mocker):
        _setup_mocks(mocker)
        agent = VisualDirectorAgent()
        agent.execute(
            job_id=22,
            script=SCENES,
            topic="Test",
            source_urls=[],
            assets_cache=str(tmp_path),
        )

        output_file = tmp_path / "job_22" / "agents" / "visual_director" / "output.json"
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["status"] == "completed"
        assert len(data["assets"]) == 2

    def test_persists_provenance_json(self, tmp_path, mocker):
        _setup_mocks(mocker)
        agent = VisualDirectorAgent()
        agent.execute(
            job_id=23,
            script=SCENES,
            topic="Test",
            source_urls=[],
            assets_cache=str(tmp_path),
        )

        prov_file = tmp_path / "job_23" / "agents" / "visual_director" / "provenance.json"
        assert prov_file.exists()
        data = json.loads(prov_file.read_text())
        assert data["topic"] == "Test"
        assert data["pexels_results"] >= 0

    def test_assets_use_agent_scenes_subdir(self, tmp_path, mocker):
        _setup_mocks(mocker)
        agent = VisualDirectorAgent()
        result = agent.execute(
            job_id=24,
            script=SCENES,
            topic="Test",
            source_urls=[],
            assets_cache=str(tmp_path),
        )

        scenes_dir = tmp_path / "job_24" / "agents" / "visual_director" / "scenes"
        assert scenes_dir.exists()
        for asset in result["assets"]:
            if asset["path"]:
                assert "scenes" in asset["path"]

    def test_no_assets_cache_uses_output_dir_fallback(self, tmp_path, mocker):
        """Without assets_cache, still works using output_dir (backward compat)."""
        _setup_mocks(mocker)
        agent = VisualDirectorAgent()
        result = agent.execute(
            job_id=25,
            script=SCENES,
            topic="Test",
            source_urls=[],
            output_dir=str(tmp_path / "outputs"),
        )
        assert result["status"] == "completed"
        assert len(result["assets"]) == 2
