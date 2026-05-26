"""Tests for database connection management."""

import sqlite3

from clipper_agency.db.connection import get_connection, close_connection


def test_get_connection(temp_db_path):
    """Connection is a valid sqlite3.Connection."""
    conn = get_connection(temp_db_path)
    assert isinstance(conn, sqlite3.Connection)
    # WAL mode should be enabled
    cursor = conn.execute("PRAGMA journal_mode")
    assert cursor.fetchone()[0].lower() == "wal"
    close_connection()


def test_get_connection_singleton(temp_db_path):
    """Same db_path returns the same connection object."""
    conn1 = get_connection(temp_db_path)
    conn2 = get_connection(temp_db_path)
    assert conn1 is conn2  # Same connection returned
    close_connection()


def test_advisory_lock(temp_db_path):
    """Basic query works — advisory lock is a no-op for SQLite."""
    conn = get_connection(temp_db_path)
    conn.execute("SELECT 1")
    close_connection()
