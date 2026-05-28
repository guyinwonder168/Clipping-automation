"""Helpers for persisted JSON and text artifacts."""

import json
from pathlib import Path
from typing import Any


def _resolve_safe(path: str | Path) -> Path:
    """Resolve *path* to eliminate ``..`` traversal components."""
    return Path(path).resolve()


def write_json(path: str | Path, data: Any) -> str:
    """Write JSON data to *path*, creating parent directories first."""
    target = _resolve_safe(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Artifact paths are built internally from configured roots, integer job IDs,
    # and static filenames; _resolve_safe normalizes them.
    target.write_text(  # NOSONAR
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )
    return str(target)


def read_json(path: str | Path) -> Any:
    """Read JSON data from *path*."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_text(path: str | Path, content: str) -> str:
    """Write text content to *path*, creating parent directories first."""
    target = _resolve_safe(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Artifact paths are built internally from configured roots, integer job IDs,
    # and static filenames; _resolve_safe normalizes them.
    target.write_text(content, encoding="utf-8")  # NOSONAR
    return str(target)
