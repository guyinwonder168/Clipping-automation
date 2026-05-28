"""Job artifact manifest — canonical inventory of all job assets."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clipper_agency.core.artifacts import read_json, write_json


def _manifest_path(assets_cache: str, job_id: int) -> Path:
    return Path(assets_cache) / f"job_{job_id}" / "manifest.json"


def create_manifest(assets_cache: str, job_id: int, topic: str,
                    output_dir: str,
                    config_snapshot: dict | None = None) -> Path:
    """Create initial manifest.json for a job workspace."""
    manifest = {
        "job_id": job_id,
        "topic": topic,
        "assets_cache": assets_cache,
        "output_dir": output_dir,
        "config_snapshot": config_snapshot or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "agents": {},
        "gates": {},
        "final_outputs": {},
    }
    path = _manifest_path(assets_cache, job_id)
    write_json(path, manifest)
    return path


def load_manifest(assets_cache: str, job_id: int) -> dict[str, Any]:
    """Load the manifest for a job."""
    return read_json(_manifest_path(assets_cache, job_id))


def _update_inplace(assets_cache: str, job_id: int,
                    update_fn: Any) -> dict[str, Any]:
    """Load manifest (or create default), apply update, write back."""
    mpath = _manifest_path(assets_cache, job_id)
    if mpath.exists():
        manifest = load_manifest(assets_cache, job_id)
    else:
        manifest = {
            "job_id": job_id,
            "topic": "",
            "assets_cache": assets_cache,
            "output_dir": "",
            "config_snapshot": {},
            "agents": {},
            "gates": {},
            "final_outputs": {},
        }
    update_fn(manifest)
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(mpath, manifest)
    return manifest


def update_manifest_agent(assets_cache: str, job_id: int,
                          agent_name: str, status: str,
                          input_path: str = "",
                          output_path: str = "") -> dict[str, Any]:
    """Record an agent's completion status in the manifest."""
    def _update(m: dict) -> None:
        m["agents"][agent_name] = {
            "status": status,
            "input": input_path,
            "output": output_path,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    return _update_inplace(assets_cache, job_id, _update)


def update_manifest_gate(assets_cache: str, job_id: int,
                         gate_name: str, passed: bool,
                         severity: str, file_path: str = "") -> dict[str, Any]:
    """Record a gate result in the manifest."""
    def _update(m: dict) -> None:
        m["gates"][gate_name] = {
            "passed": passed,
            "severity": severity,
            "file": file_path,
        }
    return _update_inplace(assets_cache, job_id, _update)


def update_manifest_final(assets_cache: str, job_id: int,
                          outputs: dict[str, str]) -> dict[str, Any]:
    """Record final output package paths."""
    def _update(m: dict) -> None:
        m["final_outputs"] = outputs
    return _update_inplace(assets_cache, job_id, _update)
