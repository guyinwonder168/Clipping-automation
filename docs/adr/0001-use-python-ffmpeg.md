# ADR 0001: Use Python + FFmpeg for Video Automation

**Date:** 2026-05-25
**Status:** Accepted

## Context

Clipper Agency needs to automate short-form video production including downloading, editing, compositing, and rendering. We need a language and tooling choice that supports AI pipelines, video manipulation, and web dashboards.

## Decision

Use **Python 3.11+** as the primary language with **FFmpeg** as the video engine (CPU-only, no GPU).

## Alternatives Considered

### TypeScript/Node.js + Remotion

- **Pros:** Web-native, good for React-based video templates.
- **Cons:** Remotion is brittle for complex compositing. Weaker AI pipeline ecosystem. Less mature FFmpeg wrappers. Remotion requires headless browser for rendering (slow, resource-heavy).

### Go + FFmpeg

- **Pros:** Fast, good concurrency.
- **Cons:** Weak AI/ML ecosystem. Fewer LLM SDKs. Less natural for prompt engineering workflows.

## Rationale

- Python has the strongest FFmpeg automation ecosystem (ffmpeg-python, moviepy, pydub).
- AI pipeline libraries (LangChain, etc.) are Python-native.
- Queue/worker ecosystem (Celery, RQ) is mature in Python.
- FFmpeg is the real rendering engine regardless of language — Python is the best glue layer.
- No GPU required for MVP — FFmpeg CPU rendering is battle-tested.
- OpenRouter API has first-class Python SDK support.

## Consequences

- All agent code in Python.
- Video rendering via FFmpeg subprocess calls.
- Web dashboard in Flask/FastAPI (Python).
- CLI in Python.
- Team needs Python familiarity (mitigated: Python is widely known).
