# ADR 0013: Use YAML + FFmpeg + Pillow for Template-Driven Video Rendering

**Date:** 2026-05-30
**Status:** Accepted
**Phase:** 15a

## Context

Phase 15a requires deterministic MVP template rendering for TikTok-style short videos. The system needs to support multiple video templates (news card, b-roll narration, rapid update) with:

- Caption overlays (drawtext)
- Scene transitions (cut, fade, crossfade)
- Template-specific thumbnails
- Offline-testable rendering pipeline
- Integration with existing Composer agent

## Decision

Adopt a hybrid architecture:

- **YAML templates** (`templates/*.yaml`) define layout, transitions, and timing declaratively.
- **Shared rendering primitives** (`rendering/primitives.py`) provide pure functions for drawtext escaping, caption overlays, lower thirds, and transitions.
- **Per-template adapters** (`rendering/renderers/*.py`) convert template config + source assets into render plans.
- **FFmpeg render engine** (`rendering/engine.py`) converts render plans into video via subprocess calls.
- **Pillow thumbnails** (`rendering/thumbnails.py`) generates template-specific thumbnail images.
- **Composer integration** via early-return `_render_via_template()` method when `template_name` is provided.

## Alternatives Considered

### Full rendering framework (e.g., MoviePy, VidGear)

- **Pros:** Higher-level API, more features.
- **Cons:** New dependency, harder to offline-test, potential Sonar/security issues, version churn.
- **Rejected:** Violates YAGNI and low-dependency principle.

### Hardcoded Composer-only templates

- **Pros:** Simplest implementation.
- **Cons:** Tight coupling, not data-driven (violates AGENTS.md "changing template should never require code changes"), hard to add new templates.
- **Rejected:** Violates data-driven architecture principle.

### Browser/HTML rendering (Playwright → video)

- **Pros:** Rich layout capabilities.
- **Cons:** Heavy dependency, slow, requires display server, hard to test offline.
- **Rejected:** Overkill for MVP caption/transition needs.

## Rationale

- YAML templates keep content/layout configuration data-driven — adding a new template requires only a YAML file, no code changes.
- FFmpeg is already a required dependency (ADR 0001); Pillow is already used for generated card fallback.
- Rendering primitives are pure functions, enabling deterministic offline testing without FFmpeg installed.
- The adapter pattern cleanly separates template-specific logic from shared rendering infrastructure.
- Fixed job-owned paths throughout the pipeline ensure OWASP-safe filesystem access (no user-controlled data at filesystem sinks, per the S6549 lesson in AGENTS.md).

## Consequences

- **Positive:** Offline-testable — all rendering primitives are pure functions; engine uses mocked FFmpeg subprocess.
- **Positive:** Low dependency risk — only uses FFmpeg (already required) + Pillow (already used for card generation) + PyYAML (already used).
- **Positive:** Data-driven — new templates via YAML files without code changes.
- **Positive:** OWASP-safe — fixed job-owned paths, no user-controlled data at filesystem sinks.
- **Negative:** FFmpeg filter complexity — complex filter graphs require careful construction; mitigated by helper functions in `primitives.py`.
- **Negative:** Rendering metrics/telemetry remain Stage 2 scope — no observability in Phase 15a.
- **Positive:** 566 offline tests pass — including rendering-specific test suites.
