"""Prompt loading helpers for agents."""

from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load_prompt(
    agent_name: str,
    fallback: str,
    prompts_dir: Path = PROMPTS_DIR,
) -> str:
    """Load an agent prompt from disk, falling back to the embedded prompt."""
    prompt_path = prompts_dir / f"{agent_name}.md"
    if not prompt_path.exists():
        return fallback

    content = prompt_path.read_text(encoding="utf-8").strip()
    return content or fallback
