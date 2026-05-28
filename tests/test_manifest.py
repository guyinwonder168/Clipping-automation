"""Tests for job artifact manifest."""

import json

from clipper_agency.core.manifest import (
    create_manifest,
    update_manifest_agent,
    update_manifest_gate,
    update_manifest_final,
    load_manifest,
)


def test_create_manifest_initializes_json(tmp_path):
    """create_manifest should produce a valid manifest.json."""
    assets_cache = str(tmp_path)
    path = create_manifest(assets_cache, 125, "Test topic", "/tmp/outputs")

    manifest = json.loads(path.read_text())
    assert manifest["job_id"] == 125
    assert manifest["topic"] == "Test topic"
    assert manifest["assets_cache"] == assets_cache
    assert manifest["output_dir"] == "/tmp/outputs"
    assert "agents" in manifest
    assert "gates" in manifest
    assert "final_outputs" in manifest
    assert manifest["agents"] == {}
    assert manifest["gates"] == {}
    assert manifest["final_outputs"] == {}


def test_update_manifest_agent_records_status(tmp_path):
    """update_manifest_agent should record agent completion info."""
    assets_cache = str(tmp_path)
    create_manifest(assets_cache, 125, "Test", "/tmp/out")

    update_manifest_agent(assets_cache, 125, "safety", "completed",
                          input_path="job_125/agents/safety/input.json",
                          output_path="job_125/agents/safety/output.json")

    manifest = load_manifest(assets_cache, 125)
    assert manifest["agents"]["safety"]["status"] == "completed"
    assert manifest["agents"]["safety"]["input"] == "job_125/agents/safety/input.json"
    assert manifest["agents"]["safety"]["output"] == "job_125/agents/safety/output.json"
    assert "completed_at" in manifest["agents"]["safety"]


def test_update_manifest_gate_records_result(tmp_path):
    """update_manifest_gate should record gate result summary."""
    assets_cache = str(tmp_path)
    create_manifest(assets_cache, 125, "Test", "/tmp/out")

    update_manifest_gate(assets_cache, 125, "G5_source_quality", True, "pass",
                         "file.json")

    manifest = load_manifest(assets_cache, 125)
    gate = manifest["gates"]["G5_source_quality"]
    assert gate["passed"] is True
    assert gate["severity"] == "pass"
    assert gate["file"] == "file.json"


def test_update_manifest_final_records_outputs(tmp_path):
    """update_manifest_final should record final package files."""
    assets_cache = str(tmp_path)
    create_manifest(assets_cache, 125, "Test", "/tmp/out")

    update_manifest_final(assets_cache, 125, {
        "video": "outputs/job_125/video.mp4",
        "caption": "outputs/job_125/caption.txt",
        "thumbnail": "outputs/job_125/thumbnail.png",
        "metadata": "outputs/job_125/metadata.json",
    })

    manifest = load_manifest(assets_cache, 125)
    assert manifest["final_outputs"]["video"] == "outputs/job_125/video.mp4"
    assert manifest["final_outputs"]["caption"] == "outputs/job_125/caption.txt"


def test_manifest_path_is_under_job_cache(tmp_path):
    """Manifest should live at job_{id}/manifest.json."""
    assets_cache = str(tmp_path)
    path = create_manifest(assets_cache, 42, "Topic", "/tmp/out")
    assert path.parent.name == "job_42"
    assert path.name == "manifest.json"
