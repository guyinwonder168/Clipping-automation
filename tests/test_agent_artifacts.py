"""Tests for persisted per-agent artifacts."""

import json

from clipper_agency.agents.safety import SafetyAgent


def test_safety_agent_persists_input_and_output(mocker, tmp_path):
    mocker.patch(
        "clipper_agency.llm.client.OpenRouterClient.chat",
        return_value={
            "content": '{"verdict": "pass", "reason": "Safe topic"}',
            "model": "mimo-v2-flash",
            "usage": {},
        },
    )
    agent = SafetyAgent()

    result = agent.execute(job_id=125, topic="Agnez Mo", assets_cache=str(tmp_path))

    base = tmp_path / "job_125" / "agents" / "safety"
    assert (base / "input.json").exists()
    assert (base / "output.json").exists()
    assert json.loads((base / "input.json").read_text(encoding="utf-8"))["topic"] == "Agnez Mo"
    assert json.loads((base / "output.json").read_text(encoding="utf-8"))["status"] == result["status"]
