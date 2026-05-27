# ADR 0006: Structured Logging for Observability

**Date:** 2026-05-27
**Status:** Accepted
**Commits:** `da4aafd` (partial)
**Phase:** 11 (logging, model config, SC cache, test-agent CLI)

## Context

The pipeline had no structured logging. Debugging failures required adding `print()` statements or reading raw Python tracebacks. There was no way to:

- Track which LLM model was called, how many tokens it consumed, or how much it cost.
- See agent start/completion/failure timestamps in a unified format.
- Monitor pipeline state transitions without reading source code.
- Configure log verbosity without modifying code.

As the system grew to 7 agents + orchestrator + 5+ external services, ad-hoc debugging became unsustainable.

## Decision

Add a dedicated logging module (`clipper_agency/core/logging.py`) providing `setup_logging()` and `get_logger()`, and instrument all layers consistently:

- **Logging module**: `setup_logging()` configures Python logging with ISO-8601 timestamps, log level from `LOG_LEVEL` env var (default INFO), and consistent format: `[YYYY-MM-DD HH:MM:SS] LEVEL name: message`.
- **All 7 agents**: Log at `INFO` on start ("Agent X: starting"), completion ("Agent X: completed — result: ..."), and errors ("Agent X: failed — ..."). Log using `logger.exception()` inside `except` blocks to capture full tracebacks.
- **All services** (ElevenLabs, Pexels, Firecrawl, ScrapeCreators): Log request start (`INFO`), response status (`INFO`), and errors with `logger.exception()`.
- **LLM client** (`clipper_agency/llm/client.py`): Log at `DEBUG` the request payload (model, prompt length), `INFO` the response summary (model, tokens, cost, latency), and `ERROR` on HTTP failures with enhanced detail.
- **Orchestrator** (`engine.py`): Log pipeline start, each gate evaluation, each agent dispatch, and pipeline completion/failure.
- **CLI**: `--log-level` option to override `LOG_LEVEL` at runtime. Startup info block logs all API key statuses (`✅ configured` / `❌ missing`).
- **Sanitization**: User-controlled input (topic strings, script text) is never interpolated directly into log messages to prevent log injection attacks (SonarCloud S5145).

## Alternatives Considered

### `print()` statements (status quo ante)

- **Pros:** Zero setup.
- **Cons:** No timestamps, no levels, no destination control. Cannot be silenced or redirected. Clutters stdout.

### `loguru` library

- **Pros:** Rich structured logging, easy setup, async support.
- **Cons:** External dependency. Requires adoption across all files. Interop with Python's `logging`-aware libraries (httpx, urllib3) requires bridging.

### `structlog` library

- **Pros:** First-class structured/dict logging.
- **Cons:** Over-engineered for MVP. Adds dependency. Best for event-sourced systems with centralized log aggregation — beyond current needs.

### Google Cloud Logging / Sentry

- **Pros:** Production-grade observability.
- **Cons:** Overhead for local development. API keys, SDK setup. Premature for MVP.

## Rationale

- Python's built-in `logging` is zero-dependency, well-understood, and sufficient for a single-node pipeline.
- `setup_logging()` as a one-time call at startup configures the root logger — all modules inherit the format and level.
- `get_logger(__name__)` gives per-module loggers with automatic module path naming.
- `LOG_LEVEL` env var + CLI `--log-level` covers both development (DEBUG) and production (INFO/WARNING) use cases.
- `logger.exception()` in `except` blocks automatically includes the full traceback — critical for debugging API failures in remote services.
- Log injection sanitization (avoiding `%s` with user-controlled strings) is a SonarCloud quality gate requirement.

## Consequences

- **Positive:** Pipeline execution is fully traceable — every agent, API call, and LLM invocation is timestamped with duration, tokens, and cost.
- **Positive:** Failures produce actionable output: traceback + context + state.
- **Positive:** Cost tracking data (tokens per model, latency per call) flows naturally from existing logs.
- **Positive:** No new dependencies — uses Python stdlib only.
- **Negative:** `logger.exception()` fills terminal with tracebacks on expected errors (e.g., ElevenLabs 401). Mitigated by INFO-level defaults.
- **Negative:** Log injection sanitization requires vigilance — every log statement with dynamic content must use `%s`-style formatting or stringification.
- **Negative:** No structured JSON output for log aggregation tools (acceptable for MVP).
