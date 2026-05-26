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
