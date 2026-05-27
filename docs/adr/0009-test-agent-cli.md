# ADR 0009: Independent Agent Testing via test-agent CLI Subcommand

**Date:** 2026-05-27
**Status:** Accepted
**Commits:** `da4aafd` (partial)
**Phase:** 11 (logging, model config, SC cache, test-agent CLI)

## Context

Debugging individual agents required running the full pipeline (orchestrator → DB → all 7 agents sequentially). This was slow, burned API credits on agents that weren't being tested, and made it impossible to isolate agent behavior. There was no way to:

- Test the Scriptwriter with custom research input without running the Researcher first.
- See what the Safety agent returned for a specific topic without triggering the full pipeline.
- Iterate on an agent prompt or model configuration with fast feedback.

## Decision

Add a `test-agent` CLI subcommand to `clipper_agency/__main__.py` that instantiates and runs any single agent independently, bypassing the orchestrator and database:

- **Usage**: `python3 -m clipper_agency test-agent <NAME> [OPTS]`
- **Supported agents**: `safety`, `researcher`, `scriptwriter`, `voice`, `visual`, `composer`, `reviewer`
- **Dispatch**: A dispatch dictionary maps string names to callable functions that create agent instances, gather required inputs (from CLI args or auto-generated defaults), execute the agent, and display results.
- **No DB tracking**: Agent runs bypass the orchestrator entirely — no `jobs` or `agent_states` records are created.
- **Auto-generated inputs**: For agents that require prior pipeline outputs, the CLI accepts CLI flags (`--research-brief`, `--script`, `--source-urls`, etc.) or falls back to sensible defaults.
- **Research auto-mode**: `test-agent scriptwriter --auto-research` runs a mini-research step inline to generate the research brief before running the scriptwriter.

## Alternatives Considered

### Pytest fixtures with mocks

- **Pros:** Standard testing approach.
- **Cons:** Requires writing test files for every scenario. Slow iteration cycle (edit test → run pytest → read output). Not suitable for ad-hoc debugging during development.

### Full pipeline with selective skip

- **Pros:** Uses the real orchestrator state machine.
- **Cons:** Still touches DB. Still runs gates. Still requires all env vars configured. A single-agent debug session shouldn't need ElevenLabs credits or FFmpeg.

### Interactive Python shell (python3 -c "from...")

- **Pros:** Maximum flexibility.
- **Cons:** Requires deep knowledge of agent constructors, settings, and output contracts. Not discoverable. No help text. Not repeatable.

## Rationale

- The `test-agent` CLI makes agent debugging as simple as `python3 -m clipper_agency test-agent safety --topic "test"`.
- Bypassing the orchestrator means zero DB overhead, zero gate evaluations, zero unrelated API calls.
- The dispatch dictionary pattern is extensible — adding a new agent means adding one entry to the dict.
- Output is printed to stdout (JSON for machine parsing, formatted text for humans), making it usable in both interactive debugging and shell scripts.
- The `--auto-research` flag for scriptwriter covers the most common use case: "I want to test the script with real research data, without thinking about research."

## Consequences

- **Positive:** Agent development iteration drops from minutes (full pipeline) to seconds (single agent).
- **Positive:** No API credits burned on unrelated agents during debugging.
- **Positive:** Self-documenting — `test-agent --help` shows all agents and options.
- **Positive:** Works offline (with cached research data) — no API keys needed for re-running with cached inputs.
- **Negative:** Dispatching via a dictionary requires manual maintenance when agent signatures change (forgot to update dispatch → runtime error).
- **Negative:** Auto-generated inputs may differ from real pipeline data, masking orchestration-dependent bugs.
- **Negative:** Agent isolation means bugs in agent-to-agent data flow (contract mismatches) are not tested — those remain in integration tests.
