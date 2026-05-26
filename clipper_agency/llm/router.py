"""Model routing with presets for cost/quality tiers."""

from enum import Enum


class ModelPreset(str, Enum):
    """Cost/quality tiers for model selection."""

    BUDGET_EAST = "budget_east"
    AGENTIC_EAST = "agentic_east"
    PREMIUM_EAST = "premium_east"
    PREMIUM_WEST = "premium_west"


PRESET_MODELS: dict[str, dict[str, str]] = {
    "budget_east": {
        "ultra_cheap": "glm-4-9b",
        "default": "mimo-v2-flash",
        "indonesian": "qwen3-32b",
    },
    "agentic_east": {
        "default": "minimax-m2.7",
        "reasoning": "deepseek-v3.2",
    },
    "premium_east": {
        "default": "kimi-k2.5",
    },
    "premium_west": {
        "default": "anthropic/claude-sonnet-4",
    },
}


def resolve_model(preset: ModelPreset, role: str = "default") -> str:
    """Resolve the model name for a given preset and role.

    Args:
        preset: The cost/quality tier.
        role: The role within the preset (e.g., 'default', 'reasoning').

    Returns:
        The model identifier string.
    """
    models = PRESET_MODELS.get(preset.value, PRESET_MODELS["budget_east"])
    return models.get(role, models.get("default", "mimo-v2-flash"))
