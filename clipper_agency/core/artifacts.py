"""Helpers for persisted JSON and text artifacts."""

import json
from pathlib import Path
from typing import Any


def write_json(path: str | Path, data: Any) -> str:
    """Write JSON data to *path*, creating parent directories first."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )
    return str(target)


def read_json(path: str | Path) -> Any:
    """Read JSON data from *path*."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_text(path: str | Path, content: str) -> str:
    """Write text content to *path*, creating parent directories first."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return str(target)
