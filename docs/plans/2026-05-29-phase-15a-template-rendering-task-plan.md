# Phase 15a Template Rendering Task Plan

**Status:** ✅ Complete (all 17 tasks done, 3 PRs merged to master)  
**Date:** 2026-05-29  
**Phase branch family:** `phase/15a-*`  
**Parent roadmap:** `docs/plans/2026-05-27-MVP Pipeline Repair Roadmap — Phases 12-15.md`

## Purpose

Phase 15a completes the MVP template-rendering promise without expanding into the Stage 2 observability scope. It makes the three MVP templates real and testable:

- News Card
- B-Roll Narration
- Rapid Update

This plan is an execution/task plan, not a replacement for `docs/PRD.md`, `docs/SRS.md`, `docs/technical_design.md`, or `docs/requirements_traceability.md`.

## Locked Brainstorming Decisions

| Decision | Chosen Direction |
|---|---|
| Scope | Implementation + tests + docs + ADR + requirements traceability updates |
| Architecture | Hybrid: shared primitives and render orchestration with small per-template adapters |
| Integration strategy | Build standalone renderer first, then integrate with Composer later in the phase |
| Delivery shape | Three PRs with smaller reviewable tasks |
| Testing level | Unit tests + small deterministic offline render fixtures |
| Rendering stack | Existing stack only: FFmpeg + Pillow + YAML templates |
| Artifact strategy | Final package stays clean; template diagnostics/artifacts persist under `ASSETS_CACHE/job_{id}` |

## Non-Goals

- Do not add a new rendering framework or large dependency.
- Do not implement the Stage 2 full observability dashboard, artifact browser, CLI parity commands, or debug bundle export.
- Do not add external API calls to template-rendering tests.
- Do not embed copyrighted TikTok audio.
- Do not replace the existing PRD/SRS/technical design documents.

## Target Runtime Shape

Template rendering should keep the current final output contract:

```text
data/outputs/job_{id}/
├── video.mp4
├── caption.txt
├── thumbnail.png
└── metadata.json
```

Intermediate diagnostics should remain in the job workspace, for example:

```text
data/assets/cache/job_{id}/agents/composer/
├── input.json
├── template_config.json
├── render_plan.json
├── ffmpeg_filtergraph.txt
├── ffmpeg_command.txt
├── ffmpeg_stderr.log
├── output.json
├── overlays/
├── cards/
└── thumbnails/
```

## Proposed Module Shape

```text
clipper_agency/rendering/
├── templates.py          # YAML loading and validation
├── contracts.py          # render contract dataclasses / typed models
├── primitives.py         # captions, overlays, lower-thirds, transitions
├── thumbnails.py         # template-specific thumbnails/cards via Pillow
├── engine.py             # shared standalone render orchestration
└── renderers/
    ├── news_card.py
    ├── b_roll_narration.py
    └── rapid_update.py
```

The exact file layout can be adjusted during implementation if existing code patterns suggest a simpler fit.

---

# PR 1 — Template Foundation

**Branch:** `phase/15a-template-foundation`

Goal: establish the reusable foundation for template-driven rendering without changing Composer behavior yet.

## Task 1: Add Template Loader and Validation

**Purpose:** Load and validate the existing MVP YAML templates:

- `templates/news_card.yaml`
- `templates/b_roll_narration.yaml`
- `templates/rapid_update.yaml`

**Expected outcome:** Invalid/missing template fields fail clearly before rendering starts.

**Test focus:** valid templates load; missing required fields fail; unknown template names fail clearly.

## Task 2: Add Render Contract Models

**Purpose:** Define the internal render contracts shared by adapters and the render engine.

Suggested concepts:

- template config
- render scene
- caption block
- overlay spec
- lower-third spec
- transition spec
- thumbnail config
- render plan

**Expected outcome:** Renderers return a deterministic render plan instead of directly building ad-hoc FFmpeg commands.

**Test focus:** contract serialization, default values, and validation behavior.

## Task 3: Add Shared Rendering Primitives

**Purpose:** Add reusable helpers for common visual instructions:

- burned-in captions
- headline overlays
- lower-third/source labels
- simple fade/cut transition metadata
- safe text wrapping and positioning metadata

**Expected outcome:** Template adapters reuse shared primitives instead of duplicating caption/overlay logic.

**Test focus:** generated primitive specs are deterministic and match expected positions/styles.

## Task 4: Add Thumbnail/Card Asset Generator

**Purpose:** Use Pillow to generate template-aware cards and thumbnails.

**Expected outcome:** The rendering layer can create deterministic 1080x1920 image assets for tests and fallback scenes.

**Test focus:** generated image exists, has expected dimensions, and does not require external assets.

## Task 5: Foundation Verification

**Purpose:** Verify foundation behavior before template adapters are added.

**Expected checks:**

```bash
.venv/bin/python3 -m pytest tests/test_rendering_templates.py tests/test_rendering_primitives.py tests/test_rendering_thumbnails.py -v
```

---

# PR 2 — Template Adapters + Standalone Render Fixtures

**Branch:** `phase/15a-template-adapters`

Goal: implement all three MVP template adapters and prove each can produce deterministic offline render output through a standalone path.

## Task 6: Implement News Card Adapter

**Purpose:** Convert script/research inputs into a News Card render plan.

Required behavior:

- headline card
- supporting image/video slot
- key facts
- caption overlays
- template thumbnail treatment

**Best for:** short breaking update stories.

## Task 7: Implement B-Roll Narration Adapter

**Purpose:** Convert voiceover-led stories into a B-Roll Narration render plan.

Required behavior:

- voiceover-led pacing
- b-roll clips/cards
- dynamic captions
- lower-thirds/source labels
- template thumbnail treatment

**Best for:** explanation/context clips.

## Task 8: Implement Rapid Update Adapter

**Purpose:** Convert short viral/trending stories into a Rapid Update render plan.

Required behavior:

- short clip/card sequence
- punchy captions
- quick transitions
- headline overlays
- template thumbnail treatment

**Best for:** trending gossip/viral updates.

## Task 9: Add Standalone Renderer Path

**Purpose:** Add an offline renderer entry point that renders from deterministic local fixtures without running the whole pipeline.

**Expected outcome:** Tests can create a small valid `video.mp4` using generated local clips/cards/audio.

**Implementation note:** Keep this path simple and internal; it is primarily for deterministic tests and future Composer integration.

## Task 10: Adapter and Fixture Verification

**Purpose:** Prove all three templates work offline.

**Expected checks:**

- each adapter creates the expected render plan
- generated overlays/cards exist
- template thumbnail exists
- standalone fixture render creates a valid video output
- no external API keys are required

Suggested command:

```bash
.venv/bin/python3 -m pytest tests/test_rendering_adapters.py tests/test_rendering_standalone.py -v
```

---

# PR 3 — Composer Integration + Documentation

**Branch:** `phase/15a-composer-template-integration`

Goal: wire template rendering into the production Composer path and update documentation/traceability.

## Task 11: Integrate Template Rendering into Composer

**Purpose:** Make Composer select/load the configured template and render through the Phase 15a rendering layer.

**Expected outcome:** Pipeline output uses template-specific captions, overlays, transitions, and thumbnail treatment.

**Safety note:** Preserve the existing fixed output package contract and Phase 14 validation behavior.

## Task 12: Persist Template Diagnostics and Artifacts

**Purpose:** Save template-rendering diagnostics in the job workspace.

Expected artifacts include:

- `template_config.json`
- `render_plan.json`
- `ffmpeg_filtergraph.txt`
- `ffmpeg_command.txt`
- `ffmpeg_stderr.log`
- generated overlays/cards/thumbnails metadata or files

**Expected outcome:** Debug-first observability can explain template-rendering failures without adding Stage 2 UI scope.

## Task 13: Update Final Output Package Metadata

**Purpose:** Ensure final package metadata records template information.

Expected additions may include:

- template name
- template version/config identifier
- render strategy
- generated thumbnail path/status

**Expected outcome:** Final package remains clean while metadata identifies the rendering template used.

## Task 14: Update Relevant Docs

**Purpose:** Update only docs that need Phase 15a implementation details after code is known.

Candidates:

- parent roadmap task status
- `docs/PRD.md` if product-level behavior changed
- `docs/SRS.md` if requirement wording needs tightening
- `docs/technical_design.md` for rendering architecture details

**Expected outcome:** Existing core docs remain aligned without duplicating this task plan.

## Task 15: Add ADR for Template-Driven Rendering

**Purpose:** Record the architecture decision to use YAML templates plus FFmpeg/Pillow rendering primitives rather than a new rendering framework.

Suggested ADR topic:

```text
Use YAML-driven FFmpeg/Pillow template rendering for MVP videos.
```

**Expected outcome:** Future contributors understand why Phase 15a avoided a new rendering framework.

## Task 16: Update Requirements Traceability

**Purpose:** Map Phase 15a requirements to implementation and tests.

Expected mappings:

- template loader tests
- adapter tests for all three templates
- standalone render fixture tests
- Composer integration tests
- final output metadata/artifact tests

## Task 17: Full Verification

**Purpose:** Verify the full Phase 15a implementation before PR merge.

Suggested checks:

```bash
.venv/bin/python3 -m pytest tests/test_rendering_templates.py tests/test_rendering_primitives.py tests/test_rendering_thumbnails.py tests/test_rendering_adapters.py tests/test_rendering_standalone.py -v
.venv/bin/python3 -m pytest -m "not external and not integration" -q
```

If Composer-specific tests are added under existing test files, include them in the targeted test command.

---

## Acceptance Criteria

- All three `templates/*.yaml` files are loaded and validated.
- News Card, B-Roll Narration, and Rapid Update each have a dedicated adapter.
- Shared primitives handle captions, overlays, lower-thirds, and transition metadata.
- Pillow-generated cards/thumbnails are deterministic and 1080x1920.
- Standalone offline render fixtures prove template rendering without external APIs.
- Composer uses template rendering for final pipeline output.
- Final videos include template-specific captions/overlays/thumbnail treatment.
- Template diagnostics are persisted under `ASSETS_CACHE/job_{id}/agents/composer/`.
- Final package remains limited to `video.mp4`, `caption.txt`, `thumbnail.png`, and `metadata.json`.
- Docs, ADR, and requirements traceability are updated after implementation details are known.
- Offline tests pass.
