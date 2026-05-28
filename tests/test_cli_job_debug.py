"""Tests for read-only CLI job diagnostics."""

import json

from click.testing import CliRunner

from clipper_agency.__main__ import cli
from clipper_agency.config.schema import AppSettings
from clipper_agency.db.connection import get_connection
from clipper_agency.db.queries import create_agent_state, create_job, mark_agent_failed
from clipper_agency.db.schema import initialize_schema


def _create_debug_job(tmp_path, monkeypatch):
    db_path = tmp_path / "clipper.db"
    assets_cache = tmp_path / "assets" / "cache"
    output_dir = tmp_path / "outputs"
    conn = get_connection(db_path)
    initialize_schema(conn)
    job_id = create_job(conn, "Raisa concert update", "indonesian_artists")
    create_agent_state(conn, job_id, "composer")
    mark_agent_failed(conn, job_id, "composer", "FFmpeg render failed")

    job_cache = assets_cache / f"job_{job_id}"
    final_dir = output_dir / f"job_{job_id}"
    (job_cache / "agents" / "researcher").mkdir(parents=True)
    (job_cache / "agents" / "voice_producer" / "voices").mkdir(parents=True)
    (job_cache / "agents" / "composer").mkdir(parents=True)
    (job_cache / "gates").mkdir(parents=True)
    final_dir.mkdir(parents=True)

    (job_cache / "manifest.json").write_text(json.dumps({"job_id": job_id}), encoding="utf-8")
    (job_cache / "agents" / "researcher" / "research_brief.md").write_text("# Research brief", encoding="utf-8")
    (job_cache / "agents" / "voice_producer" / "provider_attempts.json").write_text(
        json.dumps([{"provider": "gemini_tts", "status": "http_403"}]),
        encoding="utf-8",
    )
    (job_cache / "agents" / "composer" / "ffmpeg_stderr.log").write_text("dimension mismatch", encoding="utf-8")
    (job_cache / "gates" / "G10_video_validation.json").write_text(json.dumps({"passed": False}), encoding="utf-8")
    (job_cache / "agents" / "voice_producer" / "voices" / "scene_1.mp3").write_bytes(b"binary-audio")
    (final_dir / "caption.txt").write_text("caption", encoding="utf-8")

    settings = AppSettings(
        _env_file=None,
        db_path=str(db_path),
        assets_cache=assets_cache,
        output_dir=output_dir,
    )
    monkeypatch.setattr("clipper_agency.__main__.load_settings", lambda: settings)
    return job_id


def test_jobs_command_includes_status_updated_and_failure_summary(tmp_path, monkeypatch):
    """jobs lists status, updated time, current stage, and compact failure summary."""
    _create_debug_job(tmp_path, monkeypatch)
    result = CliRunner().invoke(cli, ["jobs"])

    assert result.exit_code == 0
    assert "Raisa concert update" in result.output
    assert "composer failed" in result.output
    assert "FFmpeg render failed" in result.output
    assert "updated=" in result.output


def test_job_show_prints_single_job_summary(tmp_path, monkeypatch):
    """job-show prints one job's DB status and timestamps."""
    job_id = _create_debug_job(tmp_path, monkeypatch)
    result = CliRunner().invoke(cli, ["job-show", str(job_id)])

    assert result.exit_code == 0
    assert f"Job #{job_id}" in result.output
    assert "Raisa concert update" in result.output
    assert "Status:" in result.output
    assert "Created:" in result.output


def test_job_debug_prints_agent_states_gates_and_key_artifacts(tmp_path, monkeypatch):
    """job-debug prints job row, agent states, gates, and useful previews."""
    job_id = _create_debug_job(tmp_path, monkeypatch)
    result = CliRunner().invoke(cli, ["job-debug", str(job_id)])

    assert result.exit_code == 0
    assert "Agent States" in result.output
    assert "composer" in result.output
    assert "Gate Results" in result.output
    assert "G10_video_validation.json" in result.output
    assert "provider_attempts.json" in result.output
    assert "dimension mismatch" in result.output


def test_job_artifacts_lists_paths_and_does_not_inline_binary(tmp_path, monkeypatch):
    """job-artifacts lists binary artifacts with metadata only."""
    job_id = _create_debug_job(tmp_path, monkeypatch)
    result = CliRunner().invoke(cli, ["job-artifacts", str(job_id)])

    assert result.exit_code == 0
    assert "scene_1.mp3" in result.output
    assert "caption.txt" in result.output
    assert "binary-audio" not in result.output


def test_job_debug_commands_missing_job_return_nonzero(tmp_path, monkeypatch):
    """Missing jobs fail with a clear non-zero result."""
    _create_debug_job(tmp_path, monkeypatch)
    result = CliRunner().invoke(cli, ["job-show", "99999"])

    assert result.exit_code != 0
    assert "Job not found" in result.output
