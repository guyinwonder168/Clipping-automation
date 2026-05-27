# ADR 0005: Add Semantic Versioning to Pipeline and Interfaces

**Date:** 2026-05-27
**Status:** Accepted
**Commits:** `7559282`
**Phase:** 10 (env/config fix)

## Context

The CLI, dashboard, and output package had no version information. Users (and developers) had no way to determine which version of the pipeline produced a given output. The `pyproject.toml` had a placeholder version but it wasn't surfaced anywhere in the application. There was no mechanism to correlate output packages to pipeline versions for debugging or regression tracking.

## Decision

Define a single semantic version (`semver`) as the source of truth at `clipper_agency/__main__.py` and surface it consistently:

- **`VERSION = "1.0.0"`** defined in `__main__.py` as the single source of truth.
- **CLI**: `python3 -m clipper_agency --version` prints the version.
- **Dashboard**: Version displayed in the base HTML template footer.
- **Output metadata** (`metadata.json`): `pipeline_version` field in every output package.
- **`pyproject.toml`**: Reads version from `__main__.py` to keep it in sync.

## Alternatives Considered

### No versioning (status quo ante)

- **Pros:** Zero work.
- **Cons:** Impossible to tell what version generated an output. Debugging by timestamp only. No upgrade path.

### `importlib.metadata` from installed package

- **Pros:** Auto-syncs with `pyproject.toml`, standard approach.
- **Cons:** Requires `pip install -e .` or installed package — CLI-only usage via `python3 -m` without install would have no version. Fragile for a project that runs via `python3 -m` not `pip install`.

### Git-based version (`git describe`)

- **Pros:** Auto-generated, no manual bumps.
- **Cons:** Requires git tree to be clean. Wrong version on detached HEAD or shallow clones. Output version would change between CI and local runs.

### Version in `pyproject.toml` only

- **Pros:** Standard Python convention.
- **Cons:** Not readable at runtime without `importlib.metadata`. Dashboard would need extra import logic.

## Rationale

- A single `__version__` string in `__main__.py` is importable anywhere in the project without extra dependencies.
- Semantic versioning (`MAJOR.MINOR.PATCH`) provides clear upgrade signals for a pipeline with external integrations.
- Output `metadata.json` with `pipeline_version` enables forensic debugging — you can tell exactly which code version produced a given video.
- Dashboard visibility lets operators confirm the running version at a glance.
- Bump discipline is low ceremony for the value it provides.

## Consequences

- **Positive:** Every output package is self-documenting about which pipeline version produced it.
- **Positive:** CLI and dashboard always agree on version (single source).
- **Positive:** Easy to communicate "upgrade to X.Y.Z" in a multi-agent workflow.
- **Negative:** Manual version bump required per release (low overhead, semantic).
- **Neutral:** The `1.0.0` starting point reflects "initial production release" — not an indicator of maturity.
