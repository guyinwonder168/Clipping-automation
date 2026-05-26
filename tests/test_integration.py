"""Integration smoke tests for the full Clipper Agency pipeline.

These tests exercise the Orchestrator end-to-end. They are marked
``@pytest.mark.integration`` and skipped by default unless
``-m integration`` is passed.
"""

import pytest

from clipper_agency.db.connection import close_connection, get_connection
from clipper_agency.db.schema import initialize_schema
from clipper_agency.orchestrator.engine import Orchestrator


@pytest.mark.integration
def test_full_pipeline_smoke(temp_db_path):
    """Smoke test: run full pipeline with a simple topic.

    Requires FFmpeg, OPENROUTER_API_KEY.
    """
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    close_connection(temp_db_path)

    orch = Orchestrator(db_path=temp_db_path)
    result = orch.run_pipeline(
        topic="Ariana Grande konser Jakarta viral",
        niche="indonesian_artists",
    )
    assert result["status"] == "completed", f"Pipeline failed: {result.get('reason', result.get('error', 'unknown'))}"
    assert "job_id" in result
    assert "output" in result


@pytest.mark.integration
def test_short_topic_does_not_crash(temp_db_path):
    """Smoke test: a minimal topic should not crash the pipeline."""
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    close_connection(temp_db_path)

    orch = Orchestrator(db_path=temp_db_path)
    result = orch.run_pipeline(topic="Test", niche="indonesian_artists")
    assert result["status"] in ("completed", "failed"), f"Unexpected status: {result.get('status')}"
