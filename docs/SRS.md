# Clipper Agency — Software Requirements Specification

**Version:** 2.2
**Date:** 2026-05-27
**Status:** Final — MVP Implementation Complete (Phase 0-10)
**Related:** `docs/PRD.md`, `docs/technical_design.md`, `docs/requirements_traceability.md`, `docs/plans/2026-05-26-mvp-implementation.md`

---

## 1. Platform Requirements

| Requirement | Specification |
|-------------|---------------|
| **OS** | Linux (primary), macOS (development), Windows (WSL2 acceptable) |
| **CPU** | x86_64, 4+ cores recommended for parallel FFmpeg |
| **GPU** | Not required (CPU-only FFmpeg rendering) |
| **RAM** | 8 GB minimum, 16 GB recommended |
| **Storage** | 20 GB free for outputs, assets, database |
| **Python** | 3.11+ |
| **FFmpeg** | 5.0+ with libx264, aac, mp3 support |
| **Docker** | Docker Compose for VPS deployment |

---

## 2. Functional Requirements

### 2.1 Pipeline

| ID | Requirement | Priority | Stage |
|----|-------------|----------|-------|
| FR-01 | Gated agent pipeline executes topic-to-output with pass/soft-fail/hard-fail at every transition | P0 | MVP |
| FR-02 | Safety Agent pre-checks topic before any paid generation using ultra-cheap model (GLM-4-9B) | P0 | MVP |
| FR-03 | Researcher Agent gathers context + source URLs + music candidates via ScrapeCreators + Firecrawl | P0 | MVP |
| FR-04 | Post-research risk gate: second safety check after real entities/claims/URLs are known | P0 | MVP |
| FR-05 | Scriptwriter Agent writes script + caption in niche tone, rotates angle from creative history | P0 | MVP |
| FR-06 | Voice Producer generates voiceover via ElevenLabs only after script passes validation | P0 | MVP |
| FR-07 | Visual Director downloads assets via yt-dlp + Pexels/local fallback, plans scene sequence | P0 | MVP |
| FR-08 | Composer assembles video via FFmpeg: scenes, transitions, captions, audio mixing, thumbnail | P0 | MVP |
| FR-09 | Reviewer Agent performs quality + safety + duplicate check (multimodal). Max 2 retries by Admin/Creative Lead | P0 | MVP |
| FR-10 | Output packager produces `video.mp4` + `caption.txt` + `thumbnail.png` + `metadata.json` | P0 | MVP |
| FR-11 | Research cache with Time To Live (TTL): fresh <60min, stale 60-240min, expired >240min or new Asia/Jakarta day | P0 | MVP |
| FR-12 | Creative memory: pre-generation check prevents repetition; post-generation update records usage | P0 | MVP |
| FR-13 | Lightweight cost + credit estimate displayed before generation. Blocks job if insufficient credits. | P0 | MVP |
| FR-14 | All agent states visible in dashboard (idle/running/completed/failed) | P0 | MVP |
| FR-15 | Asset caching: downloaded clips and Pexels images cached locally to avoid redundant downloads | P0 | MVP |

### 2.2 User Interfaces

| ID | Requirement | Priority | Stage |
|----|-------------|----------|-------|
| FR-15 | Web dashboard for job management, agent configuration, niche profiles | P0 | MVP |
| FR-16 | CLI: `python3 cli.py run --topic "..." --niche indonesian_artists` | P0 | MVP |
| FR-17 | Configurable agent autonomy levels | P1 | MVP |
| FR-18 | Selectable video templates (manual or agent-auto) | P1 | MVP |

### 2.3 Configuration

| ID | Requirement | Priority | Stage |
|----|-------------|----------|-------|
| FR-19 | Configuration hierarchy: Agent defaults → Niche → Account → Job-level overrides | P0 | MVP |
| FR-20 | All agent settings configurable per level (LLM model, prompt version, temperature, max tokens, voice ID) | P0 | MVP |
| FR-21 | Config versioning with diff and rollback | P0 | MVP |
| FR-22 | Niche profiles swappable without code changes | P0 | MVP |

---

## 3. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Video generation time | < 15 minutes per video |
| NFR-02 | Pipeline success rate | > 90% |
| NFR-03 | Human review pass rate | > 80% |
| NFR-04 | LLM cost per video | < $0.01 (Budget East) |
| NFR-05 | CLI startup | < 2 seconds |
| NFR-06 | Dashboard page load | < 3 seconds |
| NFR-07 | All agent state transitions logged with timestamps | Required |
| NFR-08 | Jobs restartable at any stage (state persisted in DB) | Required |
| NFR-09 | Agent contracts identical at all scales (MVP → 1000+ accounts) | Required |

---

## 4. Integration Requirements

### 4.1 External Services (Required for MVP)

| Service | Purpose | Auth | Rate/Credits |
|---------|---------|------|--------------|
| OpenRouter | LLM access for all agents | API key | Per-model limits |
| ElevenLabs | Voice generation | API key | Free tier sufficient for MVP; 1 default voice ID |
| Pexels API | Stock video/images fallback | API key (free) | 200 requests/hr |
| yt-dlp | Video/audio download from 1000+ sites | None | Site-specific limits |
| ScrapeCreators | TikTok video URLs, creator data, song metadata | API key (`x-api-key`) | 75 free credits |
| Firecrawl | Web search + structured page scraping | API key | Daily free runs |

### 4.2 Provider Routing

```
Cache → ScrapeCreators (TikTok video/music) + Firecrawl (context/news)
→ If quota exhausted or no usable URL: ask user for source URL
→ If no source URL: Pexels/local asset/generated cards
Stage 2: + Serper. Stage 2+: + DuckDuckGo site-filtered.
```

ScrapeCreators credits reserved for TikTok video URLs, creator profiles, engagement data, and song metadata. Results cached with TTL to minimize credit burn.

### 4.3 External Services (Future)

| Service | Purpose | Stage |
|---------|---------|-------|
| Cobalt/pybalt | Video download, different engine | Stage 2+ |
| instaloader | Instagram media | Stage 2+ |
| Douyin_TikTok_Download_API | TikTok/Douyin specialist | Stage 2+ |
| Serper API | Backup search | Stage 2 |
| DuckDuckGo site-filtered | Free fallback search | Stage 2+ |

---

## 5. Security Requirements

### 5.1 Secrets Management

- **No secrets stored in database** — only environment variable name references.
- Secrets via `.env` (local) or environment variables (production).
- `.env` loaded at CLI entry point via `python-dotenv` `load_dotenv()` in `__main__.py`; `pydantic-settings` `AppSettings` provides typed access for dashboard and CLI.
- Dashboard shows `configured ✅` or `missing ❌`, never exposes values.

### 5.2 Authentication & Authorization

| Requirement | MVP | Future |
|-------------|-----|--------|
| Dashboard auth | Basic auth + 2 groups (privileged, creative/ops) | OAuth2 / SSO |
| Role-based access | 2 groups | 4 roles (admin, creative lead, creative user, reviewer) |
| API auth | Not required (local only) | API keys |

### 5.3 Data Protection

- Client revenue, gross profit, margin **restricted** to privileged group.
- Creative users see operational budget only (estimated cost, remaining).
- Budget overrides and approvals logged in audit log.
- Soft deletes for data recovery.

---

## 6. Data Requirements

### 6.1 Database

| Requirement | MVP | Scale |
|-------------|-----|-------|
| Engine | SQLite | PostgreSQL |
| Schema | Same schema | Migrates with Alembic |
| Access | Local file | TCP connection |

### 6.2 Data Entities

| Entity | Description | Sensitive |
|--------|-------------|-----------|
| Jobs | Generation jobs with status, timestamps, config snapshot | No |
| Agent states | Per-agent inputs, outputs, state per job | No |
| Agent configs | Per-agent LLM, prompt, model, voice settings | Yes (API key refs) |
| Niche profiles | Language, tone, rules, video length | No |
| Accounts | TikTok accounts (1 for MVP) | Yes (credentials) |
| Outputs | Final package metadata, paths, scores | No |
| Creative history | Used angles, templates, assets per topic | No |
| Assets | Source metadata, license, hash, provider | No |
| Research cache | Cached research with Time To Live (TTL) (URLs, metadata, entities, tags, facts, risk flags, music) | No |
| Audit log | All actions | Yes (compliance) |
| Config versions | Patches with rollback snapshots | No |
| Prompt versions | Prompt version tracking with diffs | No |
| Templates | Video template definitions (layout, fonts, colors, animations) | No |
| Preflight estimates | Lightweight cost estimate before job | No |
| Job snapshots | Full reproducibility data | No |

### 6.3 Retention Policy

| Data Type | Duration |
|-----------|----------|
| Job metadata, config snapshots, output metadata | Indefinite |
| Agent inputs/outputs | 180 days |
| Raw research payloads | 90 days |
| Heavy intermediate assets | 30 days |
| Failed render artifacts | 14 days |
| Final output packages | 365 days |

### 6.4 Audit Requirements

- All budget overrides, config patches, and role changes logged.
- Every approved prompt/config/template change versioned with diff.
- Rollback to any previous config version.

---

## 7. Compliance Requirements

| Area | Requirement |
|------|-------------|
| **Platform policy** | TikTok: max 60s, 9:16, caption 150 chars, 5 hashtags max |
| **Copyright** | Third-party clips <5s, transformed, multi-source, original voiceover |
| **Content safety** | Safety Agent pre-checks before generation (cheapest model). Hard-block illegal/banned/high-risk defamation. Soft-warning for unverified claims. |
| **Unverified claims** | Soft wording required ("dikabarkan" — reported/said to be, "ramai dibahas netizen" — widely discussed by netizens) |
| **FFmpeg output** | Metadata stripping for platform-native appearance |

---

## 8. Deployment Requirements

| Requirement | MVP | Stage 2+ |
|-------------|-----|----------|
| Deployment | Local machine + manual | Docker Compose on VPS |
| Scaling | Single worker, sequential jobs | Parallel workers, DB-backed queue |
| Concurrency | SQLite Write-Ahead Logging (WAL) + advisory lock prevents concurrent CLI runs | DB-backed queue handles concurrency |
| Container | Dockerfile + docker-compose.yml | Same |
| CLI | `python3 cli.py run --topic "..."` | Same |
| Dashboard | Flask/FastAPI + basic auth + 2 groups | Same + full role auth |

### Scaling Path

```
MVP (1 account)              Scale (10-100)              Full (1000+)
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Single worker    │     │ Docker Compose   │     │ K8s / Multi-VPS  │
│ Sequential jobs  │ →   │ PostgreSQL       │ →   │ PG + Redis       │
│ SQLite           │     │ DB-backed queue  │     │ RQ/Celery workers│
│ CLI + Dashboard  │     │ 2-3 workers      │     │ Auto-scale       │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

Agent contracts remain identical at all scales. Queue interface abstract. Workers stateless.
