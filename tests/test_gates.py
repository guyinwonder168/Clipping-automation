"""Tests for pipeline gate definitions (G1-G10)."""

import pytest

from clipper_agency.orchestrator.gates import (
    GateResult,
    GateInputPreflight,
    GateCostEstimate,
    GateResearchCache,
    GatePostResearchRisk,
    GateSourceQuality,
    GateCreativeMemory,
    GateScriptValidation,
    GateAudioValidation,
    GateAssetValidation,
    GateVideoValidation,
)


def test_gate_result_model():
    r = GateResult(passed=True, severity="pass", message="OK")
    assert r.passed
    assert r.severity == "pass"
    assert r.message == "OK"
    assert r.data == {}


def test_gate_result_with_data():
    r = GateResult(True, "pass", "done", data={"key": "val"})
    assert r.data["key"] == "val"


# ── G1: Input Preflight ──────────────────────────────────────────

def test_g1_input_preflight_valid():
    gate = GateInputPreflight()
    result = gate.evaluate(topic="Ariana Grande konser Jakarta",
                           niche_config={"name": "test"})
    assert result.passed
    assert result.severity == "pass"


def test_g1_input_preflight_empty():
    gate = GateInputPreflight()
    result = gate.evaluate(topic="", niche_config={"name": "test"})
    assert not result.passed
    assert result.severity == "hard_fail"


def test_g1_input_preflight_whitespace():
    gate = GateInputPreflight()
    result = gate.evaluate(topic="   ", niche_config={"name": "test"})
    assert not result.passed


def test_g1_input_preflight_missing_niche():
    gate = GateInputPreflight()
    result = gate.evaluate(topic="hello")
    assert not result.passed


# ── G2: Cost Estimate ────────────────────────────────────────────

def test_g2_cost_estimate_pass():
    gate = GateCostEstimate()
    result = gate.evaluate(cached=True, niche_config={"name": "test"})
    assert result.passed
    assert result.data["estimate_cents"] > 0


def test_g2_cost_estimate_no_cache():
    gate = GateCostEstimate()
    result = gate.evaluate(cached=False)
    assert result.passed
    assert result.data["estimate_cents"] == 3.3
