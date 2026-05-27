# ADR 0007: Per-Agent LLM Model Configuration via Environment Variables

**Date:** 2026-05-27
**Status:** Accepted
**Commits:** `da4aafd` (partial)
**Phase:** 11 (logging, model config, SC cache, test-agent CLI)

## Context

All agents used a hardcoded default model (`mimo-v2-flash` from the router's `ultra_cheap` preset). There was no way to:

- Run the Safety agent on an ultra-cheap model while using a more capable model for the Scriptwriter.
- Test an agent against a different model without editing code.
- Configure model tiers per deployment (budget vs premium).
- Override models for specific agents at the environment level.

As the pipeline gained 7 agents with varying quality/cost requirements, the single-model approach became a bottleneck for both cost optimization and quality tuning.

## Decision

Add per-agent LLM model fields to `AppSettings` (`clipper_agency/config/schema.py`) with sensible defaults, and wire each agent to read its model from settings:

- **Env vars**: `SAFETY_MODEL`, `RESEARCHER_MODEL`, `SCRIPTWRITER_MODEL`, `REVIEWER_MODEL`.
- **Default**: All default to `mimo-v2-flash` (maintaining backward compatibility).
- **Agent wiring**: Each agent calls `load_settings()` and reads its model field (e.g., `settings.reviewer_model`).
- **LLM router preset** (`ultra_cheap`): Updated from `glm-4-9b` (deprecated/dead model) to `mimo-v2-flash`.
- **`.env.example`**: Documents all 4 model env vars with defaults.

## Alternatives Considered

### Single global model setting

- **Pros:** Simple, single env var.
- **Cons:** Forces all agents to use same model. Can't use cheap model for safety/checks and capable model for script/review. Opposite of cost optimization principle ("cheap before expensive").

### Model per agent tier (Config hierarchy)

- **Pros:** Full flexibility — agent defaults → niche → account → job levels.
- **Cons:** Over-engineered for MVP. The env var approach is the "agent defaults" layer of the hierarchy, extensible to lower layers later.

### Model selection in niche config (niche/*.yaml)

- **Pros:** Niche-driven model selection fits the "no code changes" principle.
- **Cons:** Model selection is an operational concern (cost, availability), not a content concern. Mixing concerns. Env vars are the right layer for infrastructure configuration.

## Rationale

- Environment variables are the standard 12-factor app approach for operational configuration.
- Per-agent model selection directly enables the cost optimization strategy (cheap models for deterministic/safety checks, capable models for generation/review).
- Defaulting to `mimo-v2-flash` maintains backward compatibility — existing deployments upgrade transparently.
- The pattern is extensible: when the config hierarchy (agent → niche → account → job) is fully implemented, per-agent env vars become the bottom layer of overrides.
- The `ultra_cheap` router preset update from `glm-4-9b` to `mimo-v2-flash` was necessary because GLM-4-9B was removed from OpenRouter.

## Consequences

- **Positive:** Cost optimization by model tier — safety/researcher run on cheap models, reviewer/scriptwriter use capable models.
- **Positive:** Backward compatible — existing `.env` files work with defaults.
- **Positive:** Simple to test — set `RESEARCHER_MODEL=test-model` and run.
- **Negative:** Only 4 agents are configurable (Safety, Researcher, Scriptwriter, Reviewer). Voice Producer, Visual Director, and Composer don't use LLM models — but future agents will follow the same pattern.
- **Negative:** Model misconfiguration (typo in env var name) silently falls back to default. No validation that the model name exists on OpenRouter.
- **Neutral:** Model availability changes are an operational concern, not a code change — update env vars to switch providers/models.
