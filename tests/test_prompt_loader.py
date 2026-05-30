"""Tests for agent prompt file loading."""

from clipper_agency.agents.prompts import load_prompt


def test_load_prompt_returns_file_content_from_prompt_dir(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "safety.md").write_text("Prompt from file\n", encoding="utf-8")

    result = load_prompt("safety", fallback="Fallback prompt", prompts_dir=prompts_dir)

    assert result == "Prompt from file"


def test_load_prompt_returns_fallback_when_file_missing(tmp_path):
    result = load_prompt("safety", fallback="Fallback prompt", prompts_dir=tmp_path)

    assert result == "Fallback prompt"


def test_load_prompt_returns_fallback_when_file_empty(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "safety.md").write_text("\n", encoding="utf-8")

    result = load_prompt("safety", fallback="Fallback prompt", prompts_dir=prompts_dir)

    assert result == "Fallback prompt"
