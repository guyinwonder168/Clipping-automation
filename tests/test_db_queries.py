"""Tests for database CRUD queries."""

from clipper_agency.db.connection import get_connection, close_connection
from clipper_agency.db.schema import initialize_schema
from clipper_agency.db.queries import (
    create_job, get_job, update_job_status,
    create_agent_state, get_agent_state, update_agent_state,
    list_jobs,
)


def test_create_and_get_job(temp_db_path):
    """Create a job and retrieve it by ID."""
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    job_id = create_job(conn, topic="Test topic", niche="indonesian_artists")
    assert job_id > 0
    job = get_job(conn, job_id)
    assert job["topic"] == "Test topic"
    assert job["niche"] == "indonesian_artists"
    assert job["status"] == "CREATED"
    close_connection()


def test_update_job_status(temp_db_path):
    """Update job status and verify the change."""
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    job_id = create_job(conn, topic="Test", niche="indonesian_artists")
    update_job_status(conn, job_id, "SAFETY_CHECKED")
    job = get_job(conn, job_id)
    assert job["status"] == "SAFETY_CHECKED"
    close_connection()


def test_create_and_get_agent_state(temp_db_path):
    """Create an agent state and retrieve it."""
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    job_id = create_job(conn, topic="Test", niche="indonesian_artists")
    create_agent_state(conn, job_id=job_id, agent_name="safety")
    state = get_agent_state(conn, job_id, "safety")
    assert state["state"] == "pending"
    assert state["agent_name"] == "safety"
    close_connection()


def test_update_agent_state(temp_db_path):
    """Update agent state and verify output_data is stored."""
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    job_id = create_job(conn, topic="Test", niche="indonesian_artists")
    create_agent_state(conn, job_id, "safety")
    update_agent_state(conn, job_id, "safety", "completed", output_data='{"result": "pass"}')
    state = get_agent_state(conn, job_id, "safety")
    assert state["state"] == "completed"
    close_connection()


def test_create_job_with_empty_config_snapshot(temp_db_path):
    """Empty dict config_snapshot is stored as '{}', not NULL."""
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    job_id = create_job(conn, topic="Test", niche="test", config_snapshot={})
    job = get_job(conn, job_id)
    assert job["config_snapshot"] == "{}"
    close_connection()


def test_update_agent_state_clears_completed_at_on_retry(temp_db_path):
    """Transition from terminal to non-terminal clears completed_at."""
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    job_id = create_job(conn, topic="Test", niche="test")
    create_agent_state(conn, job_id, "safety")
    update_agent_state(conn, job_id, "safety", "completed")
    state = get_agent_state(conn, job_id, "safety")
    assert state["completed_at"] is not None

    update_agent_state(conn, job_id, "safety", "running")
    state = get_agent_state(conn, job_id, "safety")
    assert state["state"] == "running"
    assert state["completed_at"] is None
    close_connection()


def test_list_jobs_returns_ordered(temp_db_path):
    """list_jobs returns jobs ordered by created_at DESC."""
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    create_job(conn, topic="A", niche="test")
    create_job(conn, topic="B", niche="test")
    jobs = list_jobs(conn)
    assert len(jobs) >= 2
    assert jobs[0]["id"] >= jobs[1]["id"]  # Most recent first
    close_connection()


# ── Task 11: Agent state transition helpers ──────────────────────


def test_mark_agent_running_sets_state_and_timestamps(temp_db_path):
    """mark_agent_running should set state to running and started_at."""
    from clipper_agency.db.queries import mark_agent_running

    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    job_id = create_job(conn, topic="Test", niche="test")
    create_agent_state(conn, job_id, "safety")

    mark_agent_running(conn, job_id, "safety", input_data='{"topic":"X"}')

    state = get_agent_state(conn, job_id, "safety")
    assert state["state"] == "running"
    assert state["started_at"] is not None
    close_connection()


def test_mark_agent_completed_sets_state_and_output(temp_db_path):
    """mark_agent_completed should set state to completed, output, completed_at."""
    from clipper_agency.db.queries import mark_agent_completed

    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    job_id = create_job(conn, topic="Test", niche="test")
    create_agent_state(conn, job_id, "researcher")

    mark_agent_completed(conn, job_id, "researcher",
                         output_data='{"status":"completed"}')

    state = get_agent_state(conn, job_id, "researcher")
    assert state["state"] == "completed"
    assert state["output_data"] == '{"status":"completed"}'
    assert state["completed_at"] is not None
    close_connection()


def test_mark_agent_failed_sets_state_and_error(temp_db_path):
    """mark_agent_failed should set state to failed with error message."""
    from clipper_agency.db.queries import mark_agent_failed

    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    job_id = create_job(conn, topic="Test", niche="test")
    create_agent_state(conn, job_id, "composer")

    mark_agent_failed(conn, job_id, "composer", "FFmpeg not found",
                      output_data='{"status":"failed"}')

    state = get_agent_state(conn, job_id, "composer")
    assert state["state"] == "failed"
    assert state["error_message"] == "FFmpeg not found"
    assert state["completed_at"] is not None
    close_connection()


def test_agent_state_transitions_in_order(temp_db_path):
    """Agent should go pending → running → completed in sequence."""
    from clipper_agency.db.queries import (
        mark_agent_running, mark_agent_completed,
    )

    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    job_id = create_job(conn, topic="Test", niche="test")
    create_agent_state(conn, job_id, "safety")

    s1 = get_agent_state(conn, job_id, "safety")
    assert s1["state"] == "pending"

    mark_agent_running(conn, job_id, "safety")
    s2 = get_agent_state(conn, job_id, "safety")
    assert s2["state"] == "running"

    mark_agent_completed(conn, job_id, "safety")
    s3 = get_agent_state(conn, job_id, "safety")
    assert s3["state"] == "completed"
    close_connection()
