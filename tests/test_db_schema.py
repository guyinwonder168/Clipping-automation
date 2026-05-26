"""Tests for database schema initialization."""

from clipper_agency.db.connection import get_connection, close_connection
from clipper_agency.db.schema import initialize_schema, table_exists


def test_initialize_schema_creates_tables(temp_db_path):
    """All 15 tables are created by initialize_schema."""
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    expected_tables = [
        "niches", "accounts", "jobs", "agent_states", "agent_configs",
        "templates", "assets", "research_cache", "job_outputs",
        "audit_log", "config_versions", "prompt_versions",
        "creative_history", "job_snapshots", "preflight_estimates",
    ]
    for table in expected_tables:
        assert table_exists(conn, table), f"Table {table} not created"
    close_connection()


def test_initialize_schema_idempotent(temp_db_path):
    """Running initialize_schema twice does not raise."""
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    initialize_schema(conn)  # Should not raise
    close_connection()


def test_jobs_table_columns(temp_db_path):
    """Jobs table has the required columns."""
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    cursor = conn.execute("PRAGMA table_info(jobs)")
    columns = {row[1] for row in cursor.fetchall()}
    assert "id" in columns
    assert "topic" in columns
    assert "status" in columns
    assert "niche" in columns
    close_connection()
