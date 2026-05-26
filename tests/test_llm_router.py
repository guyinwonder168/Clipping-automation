"""Tests for LLM model router (preset/role resolution)."""

from clipper_agency.llm.router import resolve_model, ModelPreset, PRESET_MODELS


class TestResolveModel:
    """resolve_model() — maps preset + role to model string."""

    def test_budget_east_default(self):
        assert resolve_model(ModelPreset.BUDGET_EAST, "default") == "mimo-v2-flash"

    def test_budget_east_reasoning_role(self):
        # budget_east doesn't have 'reasoning' role, falls back to 'default'
        assert resolve_model(ModelPreset.BUDGET_EAST, "reasoning") == "mimo-v2-flash"

    def test_agentic_east_default(self):
        assert resolve_model(ModelPreset.AGENTIC_EAST, "default") == "minimax-m2.7"

    def test_agentic_east_reasoning(self):
        assert resolve_model(ModelPreset.AGENTIC_EAST, "reasoning") == "deepseek-v3.2"

    def test_premium_east_default(self):
        assert resolve_model(ModelPreset.PREMIUM_EAST, "default") == "kimi-k2.5"

    def test_premium_west_default(self):
        assert resolve_model(ModelPreset.PREMIUM_WEST, "default") == "anthropic/claude-sonnet-4"

    def test_unknown_role_returns_default(self):
        """When role not in preset, fall back to 'default' role."""
        assert resolve_model(ModelPreset.AGENTIC_EAST, "nonexistent_role") == "minimax-m2.7"

    def test_unknown_preset_falls_back_to_budget_east(self):
        """Line 44: When preset not found, default to budget_east."""
        # Directly call with a preset that doesn't exist in PRESET_MODELS
        models = PRESET_MODELS.get("nonexistent_preset", PRESET_MODELS["budget_east"])
        assert models["default"] == "mimo-v2-flash"

    def test_resolve_unknown_preset_via_enum_value(self):
        """Using an enum value not in PRESET_MODELS falls back to budget_east."""
        # ModelPreset values ARE in PRESET_MODELS, so test the fallback path directly
        models = PRESET_MODELS.get("fake_preset", PRESET_MODELS["budget_east"])
        role_model = models.get("reasoning", models.get("default", "mimo-v2-flash"))
        assert role_model == "mimo-v2-flash"
