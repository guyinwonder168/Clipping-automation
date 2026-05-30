# ADR 0004: Use pydantic-settings + python-dotenv for Configuration Management

**Date:** 2026-05-27
**Status:** Accepted
**Commits:** `419c9ce`, `cfb7843`, `c48b9ff`, `45934e4`
**Phase:** 10 (env/config fix)

## Context

The project had a dead `AppConfig` class (`clipper_agency/config/__init__.py`) that was never loaded in production. Environment variables were read ad-hoc via `os.getenv()` with no schema validation, no default values, and no single source of truth. Key paths like `DB_PATH` and `OUTPUT_DIR` were hardcoded in multiple places, making configuration inconsistent between CLI and dashboard. The `.env` file was never loaded at startup — `load_dotenv()` was missing from the entry point.

Three problems needed solving:
1. **No config lifecycle** — `.env` vars weren't loaded before services read `os.getenv()`, causing intermittent failures when the dashboard spawned an orchestrator with different config.
2. **No typed config schema** — every service parsed env vars independently, with no type coercion or validation.
3. **No test isolation** — tests shared the developer's `.env` state, causing flaky cross-test contamination.

## Decision

Replace the dead `AppConfig` with `pydantic-settings` `BaseSettings` (`AppSettings`) and wire `python-dotenv` at the CLI entry point:

- **`AppSettings`** (at `clipper_agency/config/schema.py`) — a `pydantic-settings` `BaseSettings` subclass mapping env var names 1:1 to typed Python fields with defaults.
- **`load_dotenv()`** — called once at `clipper_agency/__main__.py` module import time (before any `os.getenv()` call), ensuring `.env` variables land in `os.environ` before any service reads them.
- **`load_settings()`** (at `clipper_agency/config/loader.py`) — returns `AppSettings()`, used by both CLI (`__main__.py`) and dashboard (`app.py`).
- **Test isolation** — tests must use both `AppSettings(_env_file=None)` and `patch.dict(os.environ, {}, clear=True)` to prevent the user's `.env` from leaking into test expectations.

## Alternatives Considered

### Pure `os.getenv()` everywhere (status quo ante)

- **Pros:** Simple, no dependencies.
- **Cons:** No type safety, no validation, no defaults, no single source of truth. Was already causing bugs (dashboard writing to wrong DB because `db_path` was hardcoded differently). No way to test config in isolation.

### `environs` library

- **Pros:** Lightweight, reads `.env` automatically, type casting.
- **Cons:** One-off library for a well-solved problem. `pydantic-settings` integrates naturally since the project already uses pydantic v2. `environs` would add another dependency for minimal benefit.

### YAML config file

- **Pros:** Human-readable, versionable.
- **Cons:** Duplicates env vars for secrets (API keys which must stay in `.env`). Two config sources adds ambiguity. `.env` is the standard for 12-factor apps.

### Environment-specific config classes

- **Pros:** Strong typing per environment (dev/staging/prod).
- **Cons:** Over-engineering for MVP — single-environment project. Adds complexity without benefit.

## Rationale

- `pydantic-settings` is already a dependency of pydantic v2, so it adds zero new dependencies.
- `load_dotenv()` at import time ensures all `os.getenv()` calls (including those in module-level code) see `.env` values.
- `AppSettings` provides typed access to all env vars with validation, defaults, and `field_alias` support (e.g., `FISHAUDIO_API_KEY` aliased to `fish_audio_api_key`).
- Test isolation pattern `_env_file=None + patch.dict(os.environ, {}, clear=True)` is explicitly documented and enforced — prevents a class of flaky test bugs that plagued earlier phases.
- Single path helper module (`clipper_agency/core/paths.py`) centralizes all cache/output directory logic, eliminating the hardcoded path duplication.

## Consequences

- **Positive:** Config is now typed, validated, and centrally defined. CLI and dashboard use the same settings. No more "wrong DB" bugs.
- **Positive:** `os.getenv()` in services still works (`.env` → `os.environ` at import time).
- **Positive:** Test environment is isolated — tests don't accidentally depend on developer's `.env`.
- **Negative:** `load_dotenv()` at module import means test files importing `__main__` pull in `.env`. Test isolation pattern must be followed.
- **Negative:** Adding a new config field requires both an `AppSettings` field and a `.env.example` entry (minor overhead).
- **Neutral:** `AppSettings` fields are uppercased env vars by convention, not snake_case Python field names — consistent but requires remembering the mapping.
