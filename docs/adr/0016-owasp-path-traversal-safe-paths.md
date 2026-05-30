# ADR 0016: OWASP Path Traversal Mitigation — Fixed Contract Paths + Safe Path Containment

**Date:** 2026-05-31
**Status:** Accepted
**Commits:** Phase 14 implementation (multiple commits)
**Phase:** 14 (Packager, Sonar S6549 Security Fix)

## Context

Phase 14 introduced the fixed-contract Packager that validates and probes the Composer's output video. During SonarCloud analysis, the `pythonsecurity:S6549` rule flagged multiple locations where file paths were constructed from data that could theoretically be user-controlled:

```python
# Flagged by Sonar S6549
video_path = data["video_path"]  # tainted input
probe_media(video_path)           # filesystem sink
```

Sonar's S6549 rule ("Change this code to not construct the path from user-controlled data") is a static analysis heuristic — it flags any path derived from external input reaching a filesystem operation. The pipeline has several such paths:

- Packager receiving `video_path` from Composer output
- Media probing (`ffprobe`) on video files
- Scene validation on clip paths
- Pexels service downloading to cache directories

### Failed mitigation attempts

| Attempt | Why it failed |
|---------|---------------|
| `# NOSONAR` suppression | Hides warning but doesn't fix the vulnerability. Sonar still flags it. |
| `os.path.realpath()` / `os.path.abspath()` / `os.path.normpath()` | Safer at runtime, but Sonar still sees tainted data reaching filesystem sinks. |
| Wrapping in sandbox helper with validation | Still looks like tainted input to static analysis. |
| `os.path.isfile()` check before opening | Validation doesn't remove taint in Sonar's analysis model. |

Each attempt addressed runtime safety but didn't satisfy the static analysis rule, because the fundamental issue was **user-controlled data reaching filesystem sinks**.

## Decision

Apply OWASP path traversal guidance at the architecture level — two complementary strategies:

### Strategy 1: Fixed contract paths (preferred)

For pipeline artifacts, use **known-good application-owned paths** instead of paths derived from agent output data:

- **Composer → Packager:** Packager does NOT read `video_path` from Composer's `output.json`. Instead, it uses the fixed contract path: `output_dir/job_{job_id}/video.mp4`. This path is constructed from `AppSettings` (trusted config) + `job_id` (integer from database), never from agent output.
- **Pattern:** "The agent owns its output directory. The consumer knows the path by convention, not by reading it from untrusted data."

### Strategy 2: Safe path containment (for unavoidable dynamic paths)

For paths that must be dynamic (e.g., Pexels download cache), use `clipper_agency/core/safe_paths.py`:

```python
def resolve_existing_file_under(base_dir, candidate) -> Path | None:
    """Return resolved path only if it's contained within base_dir."""
    base = Path(base_dir).resolve()
    resolved = (base / candidate).resolve()  # or absolute resolve
    resolved.relative_to(base)  # raises ValueError on escape
    return resolved if resolved.is_file() else None
```

This uses `pathlib.Path.resolve()` + `relative_to()` containment:
- `resolve()` eliminates `..`, symlinks, and double slashes
- `relative_to()` raises `ValueError` if the resolved path escapes the base directory
- Returns `None` on any failure (path escape, missing file, invalid input)

### What NOT to do (documented as anti-patterns in AGENTS.md)

- ❌ Suppress with `# NOSONAR`
- ❌ Sanitize then use tainted path
- ❌ Pass dynamic paths to validation/probing helpers, even wrapped
- ❌ Validate with `isfile()` then open — validation doesn't remove taint

## Alternatives Considered

### Runtime sanitization only (os.path.normpath + prefix check)

- **Pros:** Less architectural change. Works for most cases.
- **Cons:** Doesn't satisfy S6549 static analysis. Edge cases (symlinks, encoding tricks). Security is a runtime guarantee, not a structural one.

### Whitelisted path registry

- **Pros:** Complete control over which paths are accessible.
- **Cons:** Over-engineered for MVP. Every new path requires registry update. Maintenance burden.

### Container/sandbox isolation

- **Pros:** Complete filesystem isolation. No path traversal possible.
- **Cons:** Docker-only. Doesn't help for local development. Significant infrastructure change for a single security rule.

## Rationale

- **Fixed contract paths** eliminate the vulnerability at the source: if the code never reads a path from untrusted data, there's no path traversal vector. This is the OWASP-preferred approach.
- **Safe path containment** handles the remaining cases where dynamic paths are unavoidable (caching, downloads). The `resolve()` + `relative_to()` pattern is well-established and Sonar-accepted.
- The combination satisfies both Sonar S6549 (static analysis) and actual security requirements (runtime safety).
- This is a **design-level fix**, not a suppression. The architecture is safer, not just quieter.

## Consequences

- **Positive:** Sonar S6549 passes without suppression. Clean quality gate.
- **Positive:** Architectural improvement — agents communicate through fixed convention paths, reducing the attack surface of the inter-agent contract layer.
- **Positive:** `safe_paths.py` is reusable across the codebase. Any future dynamic path scenario has a vetted utility.
- **Positive:** Regression tests prove outside paths are rejected (`tests/test_safe_paths.py`).
- **Negative:** Fixed contract paths are rigid — if the output filename convention changes (e.g., `video.mp4` → `final.mp4`), every consumer must be updated. This is acceptable given the small number of consumers.
- **Negative:** `resolve_existing_file_under` only handles file reads, not writes. Write-path containment would need a separate utility (not yet needed in MVP).
- **Neutral:** The security lesson is significant enough to document in both AGENTS.md (operational guidance) and this ADR (architectural record).
