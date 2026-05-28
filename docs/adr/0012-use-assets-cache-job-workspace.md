# ADR 0012: Use ASSETS_CACHE for Job Workspaces

**Date:** 2026-05-28
**Status:** Accepted
**Phase:** 12 (artifact contracts + debug observability)

## Context

Phase 12 repaired a drift between the MVP documents and the implementation artifact layout. Intermediate files were being mixed into `OUTPUT_DIR/job_{id}` alongside final deliverables, which made jobs harder to inspect, harder to retry safely, and easier to package incorrectly.

The pipeline needs two different storage semantics:

1. **Debug and restart material** — agent inputs/outputs, raw provider responses, gate results, manifests, diagnostics, temporary media, and failed-job evidence.
2. **Customer-ready package** — only the final files intended for review/upload: `video.mp4`, `caption.txt`, `thumbnail.png`, and `metadata.json`.

Mixing these in one directory creates unclear ownership, risks leaking internal files into final packages, and makes future retry/resume cache validation ambiguous.

## Decision

Intermediate artifacts, raw provider responses, agent inputs/outputs, gate results, diagnostics, and failed-job debug material live under:

```text
ASSETS_CACHE/job_{id}
```

Final customer-ready packages live under:

```text
OUTPUT_DIR/job_{id}
```

The canonical Phase 12 layout is:

```text
ASSETS_CACHE/job_{id}/
├── manifest.json
├── agents/
│   ├── safety/
│   ├── researcher/
│   ├── scriptwriter/
│   ├── voice_producer/
│   ├── visual_director/
│   ├── composer/
│   └── reviewer/
├── gates/
└── diagnostics/

OUTPUT_DIR/job_{id}/
├── video.mp4
├── caption.txt
├── thumbnail.png
└── metadata.json
```

Path construction must go through `clipper_agency/core/paths.py` helpers rather than ad-hoc string concatenation. Dashboard and CLI diagnostics may read from both roots, but must keep traversal inside the configured job directories and must not inline binary files or secrets.

## Alternatives Considered

### Keep everything in OUTPUT_DIR/job_{id}

- **Pros:** Simplest short-term layout; existing code already wrote many files there.
- **Cons:** Blurs final output vs internal state, risks packaging debug artifacts, and makes retry/resume cache validation less trustworthy.

### Store intermediate artifacts only in SQLite

- **Pros:** Queryable and centralized.
- **Cons:** Poor fit for binary media, large provider JSON payloads, FFmpeg logs, and operator inspection. Would also bloat the SQLite database and complicate backups.

### Use one global cache without per-job workspaces

- **Pros:** Maximizes reuse of downloaded/provider artifacts.
- **Cons:** Hard to audit what a specific job consumed, harder to reproduce failures, and creates cross-job contamination risk. Global download caches can still exist as an optimization, but each job needs its own manifest and artifact references.

## Consequences

- **Positive:** Final output packages stay clean and match PRD/SRS expectations.
- **Positive:** Debug pages and CLI commands can inspect one canonical per-job workspace.
- **Positive:** Future Phase 13 retry/resume can validate cached artifacts before skipping paid provider calls.
- **Positive:** Agent and gate contracts are auditable because each stage persists its input/output under a predictable path.
- **Positive:** Failed jobs retain enough diagnostic evidence to explain the failed stage, failed gate, provider attempts, and FFmpeg errors without rerunning the job.
- **Negative:** Code must pass both `assets_cache` and `output_dir` through more call sites.
- **Negative:** Existing ADR 0008's older `{output_dir}/job_{id}/research/` cache description is superseded for Phase 12+ jobs by the `ASSETS_CACHE/job_{id}/agents/researcher/` layout.
- **Negative:** Operators must understand that deleting `ASSETS_CACHE/job_{id}` removes retry/debug material, while deleting `OUTPUT_DIR/job_{id}` removes only final deliverables.
