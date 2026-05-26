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


# ── G3: Research Cache ───────────────────────────────────────────

def test_g3_fresh_cache():
    gate = GateResearchCache()
    result = gate.evaluate(cache_entry={"freshness": "fresh"})
    assert result.passed
    assert result.severity == "pass"


def test_g3_stale_cache():
    gate = GateResearchCache()
    result = gate.evaluate(cache_entry={"freshness": "stale"})
    assert result.passed
    assert result.severity == "soft_fail"


def test_g3_no_cache():
    gate = GateResearchCache()
    result = gate.evaluate()
    assert not result.passed
    assert result.severity == "hard_fail"


# ── G4: Post-Research Risk ───────────────────────────────────────

def test_g4_no_risks():
    gate = GatePostResearchRisk()
    result = gate.evaluate(risk_flags=[])
    assert result.passed
    assert result.severity == "pass"


def test_g4_danger_keyword():
    gate = GatePostResearchRisk()
    result = gate.evaluate(risk_flags=["ilegal"])
    assert not result.passed
    assert result.severity == "hard_fail"


def test_g4_unverified_claim():
    gate = GatePostResearchRisk()
    result = gate.evaluate(risk_flags=["unverified_claim"])
    assert result.passed
    assert result.severity == "soft_fail"


# ── G5: Source Quality ───────────────────────────────────────────

def test_g5_two_sources():
    gate = GateSourceQuality()
    result = gate.evaluate(video_sources=["a.mp4", "b.mp4"])
    assert result.passed
    assert result.severity == "pass"


def test_g5_one_source():
    gate = GateSourceQuality()
    result = gate.evaluate(video_sources=["a.mp4"])
    assert result.passed
    assert result.severity == "soft_fail"


def test_g5_no_sources():
    gate = GateSourceQuality()
    result = gate.evaluate()
    assert not result.passed
    assert result.severity == "hard_fail"


# ── G6: Creative Memory ──────────────────────────────────────────

def test_g6_variation_available():
    gate = GateCreativeMemory()
    result = gate.evaluate(used_angles=["a"], available_angles=["a", "b", "c"])
    assert result.passed
    assert result.severity == "pass"


def test_g6_one_angle_left():
    gate = GateCreativeMemory()
    result = gate.evaluate(used_angles=["a", "b"], available_angles=["a", "b", "c"])
    assert result.passed
    assert result.severity == "soft_fail"


def test_g6_all_angles_exhausted():
    gate = GateCreativeMemory()
    result = gate.evaluate(used_angles=["a", "b", "c"],
                           available_angles=["a", "b", "c"])
    assert not result.passed
    assert result.severity == "hard_fail"


# ── G7: Script Validation ────────────────────────────────────────

def test_g7_valid_script():
    gate = GateScriptValidation()
    result = gate.evaluate(script="Hello world.", caption="Short caption")
    assert result.passed
    assert result.severity == "pass"


def test_g7_empty_script():
    gate = GateScriptValidation()
    result = gate.evaluate(script="", caption="Some caption")
    assert not result.passed
    assert result.severity == "hard_fail"


def test_g7_empty_caption():
    gate = GateScriptValidation()
    result = gate.evaluate(script="Hello world.", caption="")
    assert not result.passed
    assert result.severity == "soft_fail"


def test_g7_long_caption():
    gate = GateScriptValidation()
    result = gate.evaluate(script="Hello.", caption="x" * 200)
    assert result.passed
    assert result.severity == "soft_fail"


# ── G8: Audio Validation ─────────────────────────────────────────

def test_g8_missing_audio():
    gate = GateAudioValidation()
    result = gate.evaluate(audio_path="/nonexistent/audio.mp3")
    assert not result.passed
    assert result.severity == "hard_fail"


def test_g8_empty_audio_file(tmp_path):
    path = tmp_path / "empty.mp3"
    path.write_text("")
    gate = GateAudioValidation()
    result = gate.evaluate(audio_path=str(path))
    assert not result.passed
    assert result.severity == "hard_fail"


def test_g8_valid_audio(tmp_path):
    path = tmp_path / "audio.mp3"
    path.write_text("fake-audio-data")
    gate = GateAudioValidation()
    result = gate.evaluate(audio_path=str(path))
    assert result.passed
    assert result.severity == "pass"


# ── G9: Asset Validation ─────────────────────────────────────────

def test_g9_no_assets():
    gate = GateAssetValidation()
    result = gate.evaluate()
    assert not result.passed
    assert result.severity == "hard_fail"


def test_g9_all_assets_valid(tmp_path):
    a = tmp_path / "a.png"
    a.write_text("img")
    b = tmp_path / "b.jpg"
    b.write_text("img")
    gate = GateAssetValidation()
    result = gate.evaluate(asset_paths=[str(a), str(b)])
    assert result.passed
    assert result.severity == "pass"


def test_g9_mixed_assets(tmp_path):
    a = tmp_path / "good.png"
    a.write_text("img")
    bad = tmp_path / "missing.png"  # never created
    gate = GateAssetValidation()
    result = gate.evaluate(asset_paths=[str(a), str(bad)])
    assert result.passed
    assert result.severity == "soft_fail"


def test_g9_no_valid_assets(tmp_path):
    bad1 = tmp_path / "missing1.png"
    bad2 = tmp_path / "missing2.png"
    gate = GateAssetValidation()
    result = gate.evaluate(asset_paths=[str(bad1), str(bad2)])
    assert not result.passed
    assert result.severity == "hard_fail"


# ── G10: Video Validation ────────────────────────────────────────

def test_g10_missing_video():
    gate = GateVideoValidation()
    result = gate.evaluate(video_path="/nonexistent/video.mp4")
    assert not result.passed
    assert result.severity == "hard_fail"


def test_g10_too_small_video(tmp_path):
    path = tmp_path / "tiny.mp4"
    path.write_bytes(b"X" * 512)  # less than 1024 bytes
    gate = GateVideoValidation()
    result = gate.evaluate(video_path=str(path))
    assert not result.passed
    assert result.severity == "hard_fail"


def test_g10_valid_video(tmp_path):
    path = tmp_path / "video.mp4"
    path.write_bytes(b"X" * 2048)  # >= 1024 bytes
    gate = GateVideoValidation()
    result = gate.evaluate(video_path=str(path))
    assert result.passed
    assert result.severity == "pass"
