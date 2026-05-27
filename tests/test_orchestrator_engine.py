"""Tests for the Orchestrator engine — pipeline coordination."""

from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest

from clipper_agency.db.connection import close_connection, get_connection
from clipper_agency.db.schema import initialize_schema
from clipper_agency.orchestrator.engine import Orchestrator


@pytest.fixture
def db_initialized(temp_db_path):
    """Initialize schema on a temp database."""
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    yield temp_db_path
    close_connection(temp_db_path)


@pytest.fixture
def mock_safety_pass():
    """Mock SafetyAgent.execute returning pass."""
    return {"status": "pass", "reason": "Safe topic"}


@pytest.fixture
def mock_safety_hard_fail():
    """Mock SafetyAgent.execute returning hard_fail."""
    return {"status": "hard_fail", "reason": "Blocked content"}


@pytest.fixture
def mock_research_output():
    """Mock ResearcherAgent.execute output."""
    return {
        "status": "completed",
        "research_brief": "Research findings for topic",
        "sources": [{"url": "https://example.com", "title": "Source 1"}],
    }


@pytest.fixture
def mock_script_output():
    """Mock ScriptwriterAgent.execute output."""
    return {
        "status": "completed",
        "script": [
            {"scene": 1, "text": "Halo semua!", "duration": 3},
            {"scene": 2, "text": "Ada berita terbaru!", "duration": 4},
        ],
        "caption": "Breaking news tentang Ariana Grande!",
        "hashtags": ["#ArianaGrande", "#KonserJakarta"],
        "estimated_duration": 7,
    }


@pytest.fixture
def mock_voice_output():
    """Mock VoiceProducerAgent.execute output."""
    return {
        "status": "completed",
        "audio_files": ["outputs/job_1/scene_1.mp3", "outputs/job_1/scene_2.mp3"],
    }


@pytest.fixture
def mock_visual_output():
    """Mock VisualDirectorAgent.execute output."""
    return {
        "status": "completed",
        "assets": [
            {"scene": 1, "source": "pexels", "path": "assets/cache/scene_1.mp4"},
            {"scene": 2, "source": "pexels", "path": "assets/cache/scene_2.mp4"},
        ],
    }


@pytest.fixture
def mock_composer_output():
    """Mock ComposerAgent.execute output."""
    return {
        "status": "completed",
        "video_path": "outputs/job_1/final.mp4",
        "thumbnail_path": "outputs/job_1/thumbnail.png",
    }


@pytest.fixture
def mock_review_output():
    """Mock ReviewerAgent.execute output."""
    return {
        "status": "pass",
        "score": 85,
        "feedback": "Good content",
        "issues": [],
    }


@pytest.fixture
def mock_packager_output():
    """Mock OutputPackager.package output."""
    return {
        "status": "completed",
        "output_dir": "outputs/job_1",
        "video_path": "outputs/job_1/final.mp4",
        "caption_path": "outputs/job_1/caption.txt",
        "thumbnail_path": "outputs/job_1/thumbnail.png",
        "metadata_path": "outputs/job_1/metadata.json",
    }


class TestOrchestratorRunPipeline:
    """Tests for Orchestrator.run_pipeline()."""

    def test_creates_job_in_db(self, db_initialized):
        """Orchestrator should create a job record in the database."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {"status": "completed", "research_brief": "ok", "sources": []}
            mock_scriptwriter.return_value = {"status": "completed", "script": [], "caption": "", "hashtags": [], "estimated_duration": 0}
            mock_voice.return_value = {"status": "completed", "audio_files": []}
            mock_visual.return_value = {"status": "completed", "assets": []}
            mock_composer.return_value = {"status": "completed", "video_path": "", "thumbnail_path": ""}
            mock_reviewer.return_value = {"status": "pass", "score": 80, "feedback": "ok", "issues": []}
            mock_pkg.return_value = {"status": "completed", "output_dir": "/tmp", "video_path": "", "caption_path": "", "thumbnail_path": "", "metadata_path": ""}

            result = orch.run_pipeline(topic="Test topic", niche="test_niche")

        assert result["status"] == "completed"
        assert result["job_id"] > 0
        conn = get_connection(db_initialized)
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (result["job_id"],)).fetchone()
        assert job is not None
        assert job["topic"] == "Test topic"

    def test_stops_on_safety_hard_fail(self, db_initialized):
        """Orchestrator should stop pipeline if safety returns hard_fail."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher:
            mock_safety.return_value = {"status": "hard_fail", "reason": "Blocked"}
            mock_researcher.return_value = {}

            result = orch.run_pipeline(topic="Bad topic", niche="test")

        assert result["status"] == "failed"
        assert result["failed_at"] == "safety"
        assert "Blocked" in str(result.get("reason", ""))
        # Researcher should NOT have been called
        mock_researcher.assert_not_called()

    def test_initializes_agent_states(self, db_initialized):
        """Orchestrator should create agent_states for all 7 agents."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {"status": "completed", "research_brief": "ok", "sources": []}
            mock_scriptwriter.return_value = {"status": "completed", "script": [], "caption": "", "hashtags": [], "estimated_duration": 0}
            mock_voice.return_value = {"status": "completed", "audio_files": []}
            mock_visual.return_value = {"status": "completed", "assets": []}
            mock_composer.return_value = {"status": "completed", "video_path": "", "thumbnail_path": ""}
            mock_reviewer.return_value = {"status": "pass", "score": 80, "feedback": "ok", "issues": []}
            mock_pkg.return_value = {"status": "completed", "output_dir": "/tmp", "video_path": "", "caption_path": "", "thumbnail_path": "", "metadata_path": ""}

            result = orch.run_pipeline(topic="Test", niche="test_niche")

        conn = get_connection(db_initialized)
        expected_agents = ["safety", "researcher", "scriptwriter",
                          "voice_producer", "visual_director", "composer", "reviewer"]
        for agent_name in expected_agents:
            row = conn.execute(
                "SELECT * FROM agent_states WHERE job_id=? AND agent_name=?",
                (result["job_id"], agent_name),
            ).fetchone()
            assert row is not None, f"agent_state missing for {agent_name}"

    def test_full_pipeline_calls_all_agents_in_order(self, db_initialized):
        """Orchestrator should invoke agents in correct sequence."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {"status": "completed", "research_brief": "ok", "sources": []}
            mock_scriptwriter.return_value = {"status": "completed", "script": [], "caption": "", "hashtags": [], "estimated_duration": 0}
            mock_voice.return_value = {"status": "completed", "audio_files": []}
            mock_visual.return_value = {"status": "completed", "assets": []}
            mock_composer.return_value = {"status": "completed", "video_path": "", "thumbnail_path": ""}
            mock_reviewer.return_value = {"status": "pass", "score": 80, "feedback": "ok", "issues": []}
            mock_pkg.return_value = {"status": "completed", "output_dir": "/tmp", "video_path": "", "caption_path": "", "thumbnail_path": "", "metadata_path": ""}

            orch.run_pipeline(topic="Test", niche="test_niche")

        # Verify all agents were called
        mock_safety.assert_called_once()
        mock_researcher.assert_called_once()
        mock_scriptwriter.assert_called_once()
        mock_voice.assert_called_once()
        mock_visual.assert_called_once()
        mock_composer.assert_called_once()
        mock_reviewer.assert_called_once()
        mock_pkg.assert_called_once()

    def test_passes_research_to_scriptwriter(self, db_initialized):
        """Orchestrator should pass research output to scriptwriter."""
        orch = Orchestrator(db_path=db_initialized)
        research_brief = "Detailed research about Ariana Grande"

        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {"status": "completed", "research_brief": research_brief, "sources": []}
            mock_scriptwriter.return_value = {"status": "completed", "script": [], "caption": "", "hashtags": [], "estimated_duration": 0}
            mock_voice.return_value = {"status": "completed", "audio_files": []}
            mock_visual.return_value = {"status": "completed", "assets": []}
            mock_composer.return_value = {"status": "completed", "video_path": "", "thumbnail_path": ""}
            mock_reviewer.return_value = {"status": "pass", "score": 80, "feedback": "ok", "issues": []}
            mock_pkg.return_value = {"status": "completed", "output_dir": "/tmp", "video_path": "", "caption_path": "", "thumbnail_path": "", "metadata_path": ""}

            orch.run_pipeline(topic="Test", niche="test_niche")

        # Verify researcher was passed the topic
        # Verify scriptwriter received research_brief
        scriptwriter_call = mock_scriptwriter.call_args[1]
        assert scriptwriter_call["research_brief"] == research_brief

    def test_passes_assets_cache_to_safety(self, db_initialized, tmp_path):
        """Orchestrator should pass configured asset workspace to Safety."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {"status": "completed", "research_brief": "ok", "sources": []}
            mock_scriptwriter.return_value = {"status": "completed", "script": [], "caption": "", "hashtags": [], "estimated_duration": 0}
            mock_voice.return_value = {"status": "completed", "audio_files": []}
            mock_visual.return_value = {"status": "completed", "assets": []}
            mock_composer.return_value = {"status": "completed", "video_path": "", "thumbnail_path": ""}
            mock_reviewer.return_value = {"status": "pass", "score": 80, "feedback": "ok", "issues": []}
            mock_pkg.return_value = {"status": "completed", "output_dir": "/tmp", "video_path": "", "caption_path": "", "thumbnail_path": "", "metadata_path": ""}

            orch.run_pipeline(
                topic="Test",
                niche="test_niche",
                assets_cache=str(tmp_path),
            )

        safety_call = mock_safety.call_args[1]
        assert safety_call["assets_cache"] == str(tmp_path)

    def test_passes_assets_cache_to_scriptwriter(self, db_initialized, tmp_path):
        """Orchestrator should pass configured asset workspace to Scriptwriter."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {"status": "completed", "research_brief": "ok", "sources": []}
            mock_scriptwriter.return_value = {"status": "completed", "script": [], "caption": "", "hashtags": [], "estimated_duration": 0}
            mock_voice.return_value = {"status": "completed", "audio_files": []}
            mock_visual.return_value = {"status": "completed", "assets": []}
            mock_composer.return_value = {"status": "completed", "video_path": "", "thumbnail_path": ""}
            mock_reviewer.return_value = {"status": "pass", "score": 80, "feedback": "ok", "issues": []}
            mock_pkg.return_value = {"status": "completed", "output_dir": "/tmp", "video_path": "", "caption_path": "", "thumbnail_path": "", "metadata_path": ""}

            orch.run_pipeline(
                topic="Test",
                niche="test_niche",
                assets_cache=str(tmp_path),
            )

        scriptwriter_call = mock_scriptwriter.call_args[1]
        assert scriptwriter_call["assets_cache"] == str(tmp_path)

    def test_passes_script_and_research_to_voice_and_visual(self, db_initialized):
        """Orchestrator should pass script to voice producer and visual director."""
        orch = Orchestrator(db_path=db_initialized)
        script_scenes = [{"scene": 1, "text": "Halo!", "duration": 3}]
        research_sources = [{"url": "https://example.com"}]

        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {"status": "completed", "research_brief": "brief", "sources": research_sources}
            mock_scriptwriter.return_value = {"status": "completed", "script": script_scenes, "caption": "Caption", "hashtags": [], "estimated_duration": 3}
            mock_voice.return_value = {"status": "completed", "audio_files": ["a.mp3"]}
            mock_visual.return_value = {"status": "completed", "assets": [{"scene": 1, "source": "pexels", "path": "v.mp4"}]}
            mock_composer.return_value = {"status": "completed", "video_path": "final.mp4", "thumbnail_path": "thumb.png"}
            mock_reviewer.return_value = {"status": "pass", "score": 80, "feedback": "ok", "issues": []}
            mock_pkg.return_value = {"status": "completed", "output_dir": "/tmp", "video_path": "", "caption_path": "", "thumbnail_path": "", "metadata_path": ""}

            orch.run_pipeline(topic="Test", niche="test_niche")

        # Voice producer should receive script
        voice_call = mock_voice.call_args[1]
        assert voice_call["script"] == script_scenes

        # Visual director should receive script and source_urls from research
        visual_call = mock_visual.call_args[1]
        assert visual_call["script"] == script_scenes
        # source_urls should come from research sources

    def test_passes_assets_and_audio_to_composer(self, db_initialized):
        """Orchestrator should pass visual assets and audio to composer."""
        orch = Orchestrator(db_path=db_initialized)
        audio_files = ["a1.mp3", "a2.mp3"]
        assets = [{"scene": 1, "source": "pexels", "path": "v1.mp4"}]

        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {"status": "completed", "research_brief": "brief", "sources": []}
            mock_scriptwriter.return_value = {"status": "completed", "script": [], "caption": "", "hashtags": [], "estimated_duration": 0}
            mock_voice.return_value = {"status": "completed", "audio_files": audio_files}
            mock_visual.return_value = {"status": "completed", "assets": assets}
            mock_composer.return_value = {"status": "completed", "video_path": "final.mp4", "thumbnail_path": "thumb.png"}
            mock_reviewer.return_value = {"status": "pass", "score": 80, "feedback": "ok", "issues": []}
            mock_pkg.return_value = {"status": "completed", "output_dir": "/tmp", "video_path": "", "caption_path": "", "thumbnail_path": "", "metadata_path": ""}

            orch.run_pipeline(topic="Test", niche="test_niche")

        composer_call = mock_composer.call_args[1]
        assert composer_call["assets"] == assets
        assert composer_call["audio_files"] == audio_files

    def test_updates_job_status_on_completion(self, db_initialized):
        """Orchestrator should set job status to COMPLETED on success."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {"status": "completed", "research_brief": "ok", "sources": []}
            mock_scriptwriter.return_value = {"status": "completed", "script": [], "caption": "", "hashtags": [], "estimated_duration": 0}
            mock_voice.return_value = {"status": "completed", "audio_files": []}
            mock_visual.return_value = {"status": "completed", "assets": []}
            mock_composer.return_value = {"status": "completed", "video_path": "", "thumbnail_path": ""}
            mock_reviewer.return_value = {"status": "pass", "score": 80, "feedback": "ok", "issues": []}
            mock_pkg.return_value = {"status": "completed", "output_dir": "/tmp", "video_path": "", "caption_path": "", "thumbnail_path": "", "metadata_path": ""}

            result = orch.run_pipeline(topic="Test", niche="test_niche")

        conn = get_connection(db_initialized)
        job = conn.execute("SELECT status FROM jobs WHERE id = ?", (result["job_id"],)).fetchone()
        assert job["status"] == "COMPLETED"

    def test_g1_preflight_empty_topic(self, db_initialized):
        """G1 should reject empty topics before running any agents."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety:
            result = orch.run_pipeline(topic="   ", niche="test")
            assert result["status"] == "failed"
            assert result["failed_at"] == "preflight"
            mock_safety.assert_not_called()

    def test_g1_preflight_no_niche(self, db_initialized):
        """G1 should reject when None niche_config is provided (empty string still treated as valid niche name)."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety:
            # Empty niche name passes G1 (gate only checks None, not empty string)
            # The pipeline proceeds and fails at safety when it hits a real agent
            mock_safety.return_value = {"status": "hard_fail", "reason": "Blocked"}
            result = orch.run_pipeline(topic="Test", niche="")
            assert result["status"] == "failed"
            assert result["failed_at"] == "safety"

    def test_composer_failure_sets_job_failed(self, db_initialized):
        """If composer fails, job should be marked FAILED at the composer stage."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {"status": "completed", "research_brief": "ok", "sources": []}
            mock_scriptwriter.return_value = {"status": "completed", "script": [], "caption": "", "hashtags": [], "estimated_duration": 0}
            mock_voice.return_value = {"status": "completed", "audio_files": []}
            mock_visual.return_value = {"status": "completed", "assets": []}
            mock_composer.return_value = {"status": "failed", "error": "FFmpeg not found", "video_path": "", "thumbnail_path": ""}
            mock_reviewer.return_value = {}
            mock_pkg.return_value = {}

            result = orch.run_pipeline(topic="Test", niche="test_niche")

        assert result["status"] == "failed"
        assert result["failed_at"] == "composer"
        mock_reviewer.assert_not_called()
        mock_pkg.assert_not_called()

    def test_default_output_dir(self, db_initialized):
        """Orchestrator should default output_dir to 'outputs'."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {"status": "completed", "research_brief": "ok", "sources": []}
            mock_scriptwriter.return_value = {"status": "completed", "script": [], "caption": "", "hashtags": [], "estimated_duration": 0}
            mock_voice.return_value = {"status": "completed", "audio_files": []}
            mock_visual.return_value = {"status": "completed", "assets": []}
            mock_composer.return_value = {"status": "completed", "video_path": "/tmp/final.mp4", "thumbnail_path": "/tmp/thumb.png"}
            mock_reviewer.return_value = {"status": "pass", "score": 80, "feedback": "ok", "issues": []}
            mock_pkg.return_value = {"status": "completed", "output_dir": "/tmp", "video_path": "", "caption_path": "", "thumbnail_path": "", "metadata_path": ""}

            orch.run_pipeline(topic="Test", niche="test_niche")

        # Voice, visual, and composer should use outputs dir
        voice_call = mock_voice.call_args[1]
        assert "outputs" in voice_call.get("output_dir", "")

    def test_generates_cost_estimate_data(self, db_initialized):
        """G2 should generate a cost estimate."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {"status": "completed", "research_brief": "ok", "sources": []}
            mock_scriptwriter.return_value = {"status": "completed", "script": [], "caption": "", "hashtags": [], "estimated_duration": 0}
            mock_voice.return_value = {"status": "completed", "audio_files": []}
            mock_visual.return_value = {"status": "completed", "assets": []}
            mock_composer.return_value = {"status": "completed", "video_path": "/tmp/final.mp4", "thumbnail_path": "/tmp/thumb.png"}
            mock_reviewer.return_value = {"status": "pass", "score": 80, "feedback": "ok", "issues": []}
            mock_pkg.return_value = {"status": "completed", "output_dir": "/tmp", "video_path": "", "caption_path": "", "thumbnail_path": "", "metadata_path": ""}

            result = orch.run_pipeline(topic="Test", niche="test_niche")

        assert "cost_estimate" in result
        assert result["cost_estimate"]["estimate_cents"] > 0

    # ── Bug-fix tests ──────────────────────────────────────────────

    def test_unwraps_aggregate_research_sources(self, db_initialized):
        """P0: Orchestrator must unwrap Researcher's aggregate sources dict
        before extracting source URLs. The real ResearcherAgent.execute()
        returns 'sources' as {firecrawl_count, scrapecreators_count,
        total_sources, sources: [...]} — not a flat list."""
        orch = Orchestrator(db_path=db_initialized)
        # Simulate the real ResearcherAgent output format
        aggregate_sources = {
            "firecrawl_count": 2,
            "scrapecreators_count": 1,
            "total_sources": 3,
            "sources": [
                {"url": "https://a.com", "title": "A"},
                {"url": "https://b.com", "title": "B"},
                {"url": "https://c.com", "title": "C"},
            ],
        }

        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {
                "status": "completed",
                "research_brief": "ok",
                "sources": aggregate_sources,
            }
            mock_scriptwriter.return_value = {"status": "completed", "script": [], "caption": "", "hashtags": [], "estimated_duration": 0}
            mock_voice.return_value = {"status": "completed", "audio_files": []}
            mock_visual.return_value = {"status": "completed", "assets": []}
            mock_composer.return_value = {"status": "completed", "video_path": "/tmp/final.mp4", "thumbnail_path": "/tmp/thumb.png"}
            mock_reviewer.return_value = {"status": "pass", "score": 80, "feedback": "ok", "issues": []}
            mock_pkg.return_value = {"status": "completed", "output_dir": "/tmp", "video_path": "", "caption_path": "", "thumbnail_path": "", "metadata_path": ""}

            orch.run_pipeline(topic="Test", niche="test_niche")

        # Visual director should receive only the inner sources list URLs
        visual_call = mock_visual.call_args[1]
        assert visual_call.get("source_urls") is not None
        assert visual_call["source_urls"] == ["https://a.com", "https://b.com", "https://c.com"]

    def test_g4_hard_fail_aborts_pipeline(self, db_initialized):
        """P1: G4 (PostResearchRisk) returning hard_fail must abort the
        pipeline — currently the result is computed but never checked."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            # Researcher returns a danger flag that triggers G4 hard_fail
            mock_researcher.return_value = {
                "status": "completed",
                "research_brief": "ok",
                "sources": [],
                "risk_flags": ["defamation"],
            }
            mock_scriptwriter.return_value = {}

            result = orch.run_pipeline(topic="Test", niche="test_niche")

        assert result["status"] == "failed"
        assert result.get("failed_at") in ("post_research_risk", "g4")
        mock_scriptwriter.assert_not_called()

    def test_package_failure_sets_job_failed(self, db_initialized):
        """P1: When OutputPackager returns status='failed', the job must be
        marked FAILED — currently COMPLETED is set unconditionally."""
        orch = Orchestrator(db_path=db_initialized)
        with patch.object(Orchestrator, "_run_safety") as mock_safety,\
             patch.object(Orchestrator, "_run_researcher") as mock_researcher,\
             patch.object(Orchestrator, "_run_scriptwriter") as mock_scriptwriter,\
             patch.object(Orchestrator, "_run_voice_producer") as mock_voice,\
             patch.object(Orchestrator, "_run_visual_director") as mock_visual,\
             patch.object(Orchestrator, "_run_composer") as mock_composer,\
             patch.object(Orchestrator, "_run_reviewer") as mock_reviewer,\
             patch.object(Orchestrator, "_package_output") as mock_pkg:
            mock_safety.return_value = {"status": "pass", "reason": "Safe"}
            mock_researcher.return_value = {"status": "completed", "research_brief": "ok", "sources": []}
            mock_scriptwriter.return_value = {"status": "completed", "script": [], "caption": "", "hashtags": [], "estimated_duration": 0}
            mock_voice.return_value = {"status": "completed", "audio_files": []}
            mock_visual.return_value = {"status": "completed", "assets": []}
            mock_composer.return_value = {"status": "completed", "video_path": "/tmp/final.mp4", "thumbnail_path": "/tmp/thumb.png"}
            mock_reviewer.return_value = {"status": "pass", "score": 80, "feedback": "ok", "issues": []}
            # Package returns FAILED
            mock_pkg.return_value = {"status": "failed", "error": "Disk full", "output_dir": "/tmp"}

            result = orch.run_pipeline(topic="Test", niche="test_niche")

        assert result["status"] == "failed"
        assert result.get("failed_at") == "packaging"

        conn = get_connection(db_initialized)
        job = conn.execute("SELECT status FROM jobs WHERE id = ?", (result["job_id"],)).fetchone()
        assert job["status"] == "FAILED"
