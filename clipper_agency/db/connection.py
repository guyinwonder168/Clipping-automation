"""SQLite connection management with WAL mode and thread-safe singleton."""

import sqlite3
from pathlib import Path
from threading import Lock

_connections: dict[str, sqlite3.Connection] = {}
_conn_lock = Lock()


def get_connection(db_path: str) -> sqlite3.Connection:
    """Get or create a SQLite connection with WAL mode."""
    abs_path = str(Path(db_path).resolve())
    with _conn_lock:
        if abs_path not in _connections:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(abs_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row
            _connections[abs_path] = conn
        return _connections[abs_path]


def close_connection(db_path: str | None = None) -> None:
    """Close database connection(s)."""
    with _conn_lock:
        if db_path:
            abs_path = str(Path(db_path).resolve())
            if abs_path in _connections:
                _connections[abs_path].close()
                del _connections[abs_path]
        else:
            for conn in _connections.values():
                conn.close()
            _connections.clear()
