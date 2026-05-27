"""Tests for artifact file helpers."""

import json

from clipper_agency.core.artifacts import write_json, write_text


def test_write_json_creates_parent_directories(tmp_path):
    path = tmp_path / "job_1" / "agents" / "safety" / "output.json"

    write_json(path, {"status": "completed"})

    assert json.loads(path.read_text(encoding="utf-8")) == {"status": "completed"}


def test_write_text_creates_parent_directories(tmp_path):
    path = tmp_path / "job_1" / "agents" / "researcher" / "research_brief.md"

    write_text(path, "# Brief")

    assert path.read_text(encoding="utf-8") == "# Brief"
