# Clipper Agency — Technical Design Document

**Version:** 3.5
**Date:** 2026-05-28
**Status:** MVP Repair In Progress — Phase 12 Artifact Contracts + Debug Observability
**Related:** `docs/PRD.md`, `docs/SRS.md`, `docs/requirements_traceability.md`, `docs/plans/2026-05-26-mvp-implementation.md`, `docs/plans/2026-05-27-MVP Pipeline Repair Roadmap — Phases 12-15.md`

---

## 1. System Architecture

### Design Decision: Fully Agentic (Approach B)

Seven MVP agents, each independently configurable and observable. Orchestrator coordinates via database-driven state. Creative Director deferred to Stage 2.

```
                     DASHBOARD (Web UI)
   Safety | Researcher | Scriptwriter | Voice | Visual | Composer | Reviewer
                     ┌───────────────────────┐
                     │     ORCHESTRATOR      │
                     │ Gated State Machine   │
                     └──────┬────────────────┘
                            ▼
                     DATABASE (SQLite → PG)
```

**Why Fully Agentic:** Each agent independently testable, configurable, observable. Scales naturally. Avoids rigid monolith and limited-visibility structured pipeline.

### Agent Communication

- **Database-driven state** — each agent reads/writes `JobState` in DB.
- Orchestrator checks DB to determine "can next agent run?"
- Every agent state visible in dashboard (idle, running, completed, failed).
- Jobs are restartable in principle from persisted DB state plus `ASSETS_CACHE/job_{id}` artifacts. Write-enabled retry/resume is added after the Phase 12 artifact/debug contract stabilizes.
- **Manual retry from failed step** — no auto-retry loops in MVP.
- CLI and dashboard both create the same `jobs` record type.
- Running jobs cannot be edited or retried until paused, failed, or completed.

### Job Workspace and Final Package Boundaries

Each job has two separate roots:

```text
ASSETS_CACHE/job_{id}/   # intermediate agent/gate artifacts, diagnostics, manifest
OUTPUT_DIR/job_{id}/     # final customer-ready package only
```

`ASSETS_CACHE/job_{id}` contains agent `input.json`/`output.json`, gate result JSON, raw provider payloads, normalized research contracts, TTS provider attempts, FFmpeg diagnostics, and `manifest.json`. `OUTPUT_DIR/job_{id}` contains only `video.mp4`, `caption.txt`, `thumbnail.png`, and `metadata.json`.

---

## 2. Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.11+ | Best FFmpeg/video automation ecosystem, AI pipelines |
| **Video Engine** | FFmpeg (CPU-only) | No GPU required, battle-tested, programmable |
| **Database** | SQLite → PostgreSQL | Same schema, swap for scale |
| **Queue** | None/sequential (MVP) → DB-backed → Redis + RQ/Celery | Avoid overhead until multi-account |
| **LLM Access** | OpenRouter API | Large Language Model (LLM) access, multi-model, single key |
| **Secrets** | `python-dotenv` + `pydantic-settings` `AppSettings` | `.env` loaded at CLI entry (`__main__.py`); services use `os.getenv()`. No secrets in DB. |
| **Logging** | Python `logging` + `clipper_agency/core/logging.py` | `setup_logging()` + `get_logger()`. All agents, services, orchestrator, and LLM client log at DEBUG/INFO/ERROR. Configurable via `LOG_LEVEL` env var. |
| **Prompts** | Filesystem (`prompts/`) | Git-tracked, versioned |
| **Container** | Docker Compose | VPS-ready |

### External Services (MVP Required)

| Service | Purpose |
|---------|---------|
| OpenRouter | LLM for all agents |
| ElevenLabs | Voice generation |
| Google AI Studio Gemini TTS | Voice generation fallback after ElevenLabs |
| Fish Audio | Voice generation fallback after Gemini TTS |
| Pexels API | Stock video/images fallback |
| yt-dlp | Source video/audio download |
| ScrapeCreators | TikTok video URL + song metadata |
| Firecrawl | Web search + structured scraping |

### Layered Media Providers

```
MVP:
    ├── Layer 1: yt-dlp (default, 1000+ sites) — PRIMARY
    └── Fallback: Pexels/user asset/generated cards

Stage 2+:
    ├── Layer 2: Cobalt/pybalt (different engine)
    ├── Layer 3a: instaloader (Instagram)
    ├── Layer 3b: Douyin_TikTok_Download_API (TikTok specialist)
    ├── Layer 3c: gallery-dl (image galleries)
    └── Fallback: Pexels (always available)
```

**MVP selection flow:** source URL → try yt-dlp → if missing/fails: approved local user asset, Pexels, or generated cards.

**Stage 2+ selection flow:** URL → extract platform → try specialist → try yt-dlp → try Cobalt → fallback to Pexels. All providers config-driven, all optional via toggle.

---

## 3. Gated Agent Pipeline

### 3.1 Pipeline Flow

```text
1.  Topic Input
2.  Gate G1: Input Preflight
3.  Gate G2: Lightweight Cost + Credit Estimate
4.  Agent A1: Safety Pre-Check (ultra-cheap model)
5.  Gate G3: Research Cache Check
6.  Agent A2: Researcher (ScrapeCreators + Firecrawl)
7.  Gate G4: Post-Research Risk Gate
8.  Gate G5: Source Quality Gate
9.  Gate G6: Creative Memory Gate
10. Agent A3: Scriptwriter
11. Gate G7: Script Validation Gate
12. Agent A4: Voice Producer (ElevenLabs → Gemini TTS → Fish Audio fallback)
13. Gate G8: Audio Validation Gate
14. Agent A5: Visual Director (yt-dlp + fallback)
15. Gate G9: Asset Validation Gate
16. Agent A6: Composer (FFmpeg)
17. Gate G10: Deterministic Video Validation
18. Agent A7: Reviewer (multimodal)
19. Output Package
```

### 3.2 Gate Definitions

#### G1: Input Preflight

| Field | Value |
|-------|-------|
| **Purpose** | Validate topic input before any processing |
| **Input** | Topic string, optional source URL, niche config |
| **Check type** | Deterministic (no LLM) |
| **Pass** | Topic non-empty after trim, niche config loaded, source URL valid format if provided, configured language supported by assigned LLM models |
| **Soft fail** | Missing source URL — show warning, continue |
| **Hard fail** | Empty/whitespace-only topic, invalid niche, malformed URL, language-model incompatibility |
| **Cost protection** | Zero cost. Blocks all downstream spending on invalid input. |
| **Next** | User must fix input (CLI error message or dashboard validation error). Then G2. |

#### G2: Lightweight Cost + Credit Estimate

| Field | Value |
|-------|-------|
| **Purpose** | Show estimated cost and credit usage before generation |
| **Input** | Niche config, model presets, cached research availability |
| **Check type** | Deterministic calculation |
| **Pass** | Estimate within acceptable range, sufficient credits for all required providers |
| **Soft fail** | Estimate exceeds expected range — show warning to user, require acknowledgment |
| **Hard fail** | Insufficient credits for any required provider |
| **Cost protection** | Zero marginal cost. Prevents jobs that cannot complete. |
| **Next** | User must add credits or acknowledge warning. Then A1. |

#### G3: Research Cache Check

| Field | Value |
|-------|-------|
| **Purpose** | Avoid redundant paid research calls |
| **Input** | Topic, entities, niche, date |
| **Check type** | Deterministic DB lookup |
| **Pass** | Fresh cache (<60 min) exists → skip to G4 with cached data |
| **Soft fail** | Stale cache (60-240 min) → reuse with stale marking, log |
| **Hard fail** | No cache or expired (>240 min or new Asia/Jakarta day) → proceed to A2 |
| **Cost protection** | Saves ScrapeCreators credits + Firecrawl API calls |
| **Next** | G4 (if cached) or A2 (if not) |

#### G4: Post-Research Risk Gate

| Field | Value |
|-------|-------|
| **Purpose** | Catch risk discovered after research finds real entities, claims, URLs |
| **Input** | Researcher output: entities, risk_flags, source URLs, context_notes |
| **Check type** | Deterministic keyword/flag scan → GLM-4-9B (ultra-cheap) only if flags or new entities detected |
| **Pass** | No illegal/banned/high-defamation risk detected |
| **Soft fail** | Unverified rumor detected — require cautious wording in downstream agents |
| **Hard fail** | Clear defamation, illegal content, banned platform policy — stop job, no override |
| **Cost protection** | Blocks script, voice, visual, composer spending on unsafe content |
| **Next** | Admin/Creative Lead if hard fail or unclear. G5 if pass/soft-fail. |

#### G5: Source Quality Gate

| Field | Value |
|-------|-------|
| **Purpose** | Ensure enough usable source material exists before expensive generation |
| **Input** | Resolved video_sources list from researcher, researcher topic_brief and context_notes |
| **Check type** | Deterministic count + URL domain validation against yt-dlp supported sites |
| **Pass** | ≥2 usable source URLs on yt-dlp-supported domains, research has topic_brief and context |
| **Soft fail** | 1 usable URL — proceed with Pexels/generated cards, log risk warning. Or empty research context but URLs exist — proceed with URL-only mode. |
| **Hard fail** | 0 usable URLs and no Pexels fallback configured — ask user for source URL. Or completely empty research output (no URLs, no context) — stop job. |
| **Cost protection** | Prevents script/voice/render spend on jobs with no visual material or research grounding |
| **Next** | Admin/Creative Lead if hard fail. G6 if pass/soft-fail. |

#### G6: Creative Memory Gate

| Field | Value |
|-------|-------|
| **Purpose** | Prevent repetitive content without wasting generation tokens |
| **Input** | Topic cluster, account history, used angles/templates/assets |
| **Check type** | Deterministic DB lookup |
| **Pass** | Sufficient variation available — select next angle |
| **Soft fail** | Variation running low — log warning, continue with remaining angles |
| **Hard fail** | All angles exhausted — MVP: flag for human review; Stage 2: route to Creative Director |
| **Cost protection** | Prevents generation of duplicate content |
| **Next** | Human if hard fail. A3 if pass/soft-fail. |

#### G7: Script Validation Gate

| Field | Value |
|-------|-------|
| **Purpose** | Validate script before spending ElevenLabs credits on voice |
| **Input** | Script text, caption text |
| **Check type** | Deterministic (length, format, safety keyword scan) + GLM-4-9B (ultra-cheap) |
| **Pass** | Script within length, no safety issues, proper formatting |
| **Soft fail** | Minor issues (too long, weak hook) — auto-trim or flag for review |
| **Hard fail** | Safety violation detected — stop, route to human |
| **Cost protection** | Blocks ElevenLabs spend on invalid/unsafe scripts |
| **Next** | Human if hard fail. A4 if pass/soft-fail. |

#### G8: Audio Validation Gate

| Field | Value |
|-------|-------|
| **Purpose** | Validate voiceover file before spending FFmpeg time on render |
| **Input** | Audio file path, expected duration |
| **Check type** | Deterministic (file exists, file size > 0, duration check, format validation) |
| **Pass** | Audio file valid, duration within ±2s of expected |
| **Soft fail** | Minor duration mismatch (<2s) — log, continue |
| **Hard fail** | File missing, 0 bytes, 0 seconds, corrupt, or duration >10s off expected — stop |
| **Cost protection** | Prevents FFmpeg render with missing/broken audio |
| **Next** | Admin/Creative Lead if hard fail. A5 if pass/soft-fail. |

#### G9: Asset Validation Gate

| Field | Value |
|-------|-------|
| **Purpose** | Validate downloaded assets before FFmpeg render |
| **Input** | Asset file paths, expected counts |
| **Check type** | Deterministic (file exists, file size > 0, format check, duration 1-5s for clips) |
| **Pass** | All assets valid, clips 1-5s, files non-zero |
| **Soft fail** | Some assets missing/clips <1s (rejected) but enough for composition — log warning |
| **Hard fail** | No valid assets — stop |
| **Cost protection** | Prevents FFmpeg render with no visual material |
| **Next** | Admin/Creative Lead if hard fail. A6 if pass/soft-fail. |

#### G10: Deterministic Video Validation

| Field | Value |
|-------|-------|
| **Purpose** | Validate rendered video before spending multimodal Reviewer tokens |
| **Input** | Output video file path |
| **Check type** | Deterministic (file exists, file size > 0, duration, resolution, codec, audio track present) |
| **Pass** | Video 9:16, 1080x1920, duration 20-60s, audio track present, file size > 1KB |
| **Soft fail** | Minor deviations — log, continue to reviewer |
| **Hard fail** | File missing, 0 bytes, wrong resolution, no audio, or duration out of range |
| **Cost protection** | Prevents multimodal Reviewer spend on broken video files |
| **Next** | Admin/Creative Lead if hard fail. A7 if pass/soft-fail. |

### 3.3 State Machine

Each job has a state tracked in the database:

```text
CREATED → PREFLIGHT → COST_ESTIMATED → SAFETY_CHECKED → RESEARCHING
→ RESEARCH_REVIEWED → SOURCES_VALIDATED → MEMORY_CHECKED → SCRIPTING
→ SCRIPT_VALIDATED → VOICING → AUDIO_VALIDATED → VISUALIZING
→ ASSETS_VALIDATED → COMPOSING → VIDEO_VALIDATED → REVIEWING
→ COMPLETED

Any state → PAUSED (Admin/Creative Lead action via dashboard or CLI signal)
Any state → FAILED (with gate/agent that caused failure)
PAUSED → same state where paused (resume re-runs current step with same config snapshot)
FAILED → any earlier state (Admin/Creative Lead triggers retry from that point)
```

**PAUSED state rules:**
- Config snapshot frozen at job creation time; resume uses same snapshot even if global config changed.
- Cached research may be stale after pause — G3 re-checks cache freshness on resume.
- ScrapeCreators credits re-validated on resume (G2 re-checks credits).

---

## 4. Agent Roles

| Agent | Role | Cost Tier | Caching |
|-------|------|-----------|---------|
| **Safety Agent** | Pre-checks topic. Ultra-cheap model (GLM-4-9B). Hard-blocks illegal/banned/high-risk defamation; soft-warns unverified claims. | Ultra Budget | Not cached |
| **Researcher** | Gathers context + source URLs + music candidates. MVP: ScrapeCreators (`trim=true` + field extraction via `_extract_fields()` handling both `aweme_info`-wrapped and flat trimmed responses, max 20 results) + Firecrawl (lean url/title/desc only). Cache-first: reads/writes raw responses, `research_brief.md`, `research_contract.json`, and normalized files under `ASSETS_CACHE/job_{id}/agents/researcher/`. Token guard: `MAX_SOURCE_CHARS=40000` prevents LLM overflow. Returns structured data with entities, tags, risk_flags, cache_key. | Budget East | TTL-based + job workspace file cache |
| **Scriptwriter** | Writes script + caption in niche tone. Rotates angle from creative history. Always fresh. | Budget East | Never |
| **Voice Producer** | Generates voiceover via provider fallback: ElevenLabs → Google AI Studio Gemini TTS → Fish Audio → fail clearly. `GeminiTTSService` uses `gemini-2.5-flash-preview-tts` with configured voice (default `Kore`) and wraps PCM audio as WAV when needed. `FishAudioService` uses `s2-pro` model, `POST /v1/tts`, `reference_id` for voice model. Voice files and sanitized `provider_attempts.json` are saved under `ASSETS_CACHE/job_{id}/agents/voice_producer/`. Always fresh. | API cost | Never |
| **Visual Director** | Selects assets, plans scene sequence. MVP: yt-dlp + Pexels/local fallback. | Budget East | Never |
| **Composer** | FFmpeg assembly: scenes, transitions, captions, audio mixing, thumbnail. | N/A | Never |
| **Reviewer** | Quality + safety + duplicate check. Multimodal (video + text). Max 2 human-triggered retries. | Moderate | Never |
| **Creative Director** | Stage 2. Proposes new angles/templates when variation exhausted. | Agentic East | Triggered |

### Researcher Structured Output

#### Research Query Construction

Before calling providers, the Researcher builds queries from:
1. **Topic** + detected entities (artist names, event names from topic string).
2. **Niche infotainment terms** (configurable list per niche, e.g., `viral`, `ramai dibahas`, `klarifikasi`, `hubungan`, `rilis lagu`).
3. **Language** from niche config (e.g., `id` → queries in Bahasa Indonesia).
4. **ScrapeCreators queries:** Artist name + TikTok-specific terms → TikTok video URLs, song metadata, creator profiles.
5. **Firecrawl queries:** Topic + news terms → recent Indonesian entertainment/news articles with title, author, published date, key facts.

Query construction is config-driven: the niche profile defines search terms, language, and preferred source domains. No hardcoded queries.

#### Agent Input/Output Contracts

| Agent | Input | Output | On Failure |
|-------|-------|--------|------------|
| **Safety** | Topic string, niche safety_rules; persisted as `agents/safety/input.json` | Pass/soft-warning/hard-fail + reason; persisted as `agents/safety/output.json` + `summary.md` | Hard-fail stops pipeline |
| **Researcher** | Topic, niche config, cached research (if fresh); persisted as `agents/researcher/input.json` | Markdown brief (`research_brief.md`), raw provider payloads, normalized files, `research_contract.json`, and `output.json` | Empty result → G5 handles |
| **Scriptwriter** | Researcher contract/output, creative history; persisted as `agents/scriptwriter/input.json` | `script.json`, `caption.txt`, `hashtags.json`, selected angle, and `output.json` | N/A (always produces output) |
| **Voice Producer** | Validated script text, voice_id from config; persisted as `agents/voice_producer/input.json` | Voice files under `agents/voice_producer/voices/`, `provider_attempts.json`, duration metadata, and `output.json` | All providers fail → stop, retry by Admin/Creative Lead |
| **Visual Director** | Researcher video_sources, Pexels query from tags, local asset paths, generated card config; persisted as `agents/visual_director/input.json` | `scene_plan.json`, `provenance.json`, scene files under `scenes/`, cards under `cards/`, and `output.json` | Download failures → G9 handles |
| **Composer** | Validated audio file, scene plan, template config, caption text; persisted as `agents/composer/input.json` | Final `OUTPUT_DIR/job_{id}/video.mp4`, plus `ffmpeg_command.txt`, `ffmpeg_stderr.log`, and `output.json` in job workspace | FFmpeg failure → stop, retry by Admin/Creative Lead |
| **Reviewer** | Rendered video file, script text, caption, creative history; persisted as `agents/reviewer/input.json` | Pass/reject + specific issues + recommended retry step; persisted as `agents/reviewer/output.json` + `review.md` | Reject → Admin/Creative Lead decides |

#### Researcher Output Schema

```yaml
researcher_output:
  topic_brief: "2-3 sentence summary"

  video_sources:
    - url: "https://..."
      platform: "youtube"
      media_type: "video"
      duration_seconds: 180
      thumbnail_url: "https://..."
      title: "Video title"
      author: "Channel name"
      published_at: "ISO-8601"
      credibility_score: 0.8
      candidate_moments:
        - timestamp: "00:45-00:52"
          description: "Key moment"
          relevance: "high"
      song:
        title: "Song title"
        artist: "Artist"
        tiktok_song_id: "id"
        usage_count: "1.2M videos"

  background_music:
    - title: "Song"
      artist: "Artist"
      tiktok_song_id: "id"
      source: "tiktok"
      mood: "upbeat"
      fallback: "no background music or safe stock music"

  context_sources:
    - url: "https://..."
      type: "news_article"
      summary: "Article summary"
      key_facts: ["fact1", "fact2"]

  tags: ["artist_name:X", "event_type:Y", "sentiment:neutral"]
  entities:
    artists: ["Artist Name"]
    locations: ["Location"]
    events: ["Event description"]
  context_notes: "Notes about verification status"
  risk_flags: ["flag_type"]

  cache_key: "niche:platform:language:topic_cluster:entities:date"
  cache_freshness: "fresh|stale|expired"
```

#### Persisted Research Artifacts

The Researcher writes a human-readable brief and a machine-readable contract:

```text
ASSETS_CACHE/job_{id}/agents/researcher/research_brief.md
ASSETS_CACHE/job_{id}/agents/researcher/research_contract.json
ASSETS_CACHE/job_{id}/agents/researcher/raw/scrapecreators_response.json
ASSETS_CACHE/job_{id}/agents/researcher/raw/firecrawl_response.json
ASSETS_CACHE/job_{id}/agents/researcher/normalized/video_sources.json
ASSETS_CACHE/job_{id}/agents/researcher/normalized/context_sources.json
ASSETS_CACHE/job_{id}/agents/researcher/normalized/music_candidates.json
ASSETS_CACHE/job_{id}/agents/researcher/normalized/entities.json
ASSETS_CACHE/job_{id}/agents/researcher/normalized/risk_flags.json
```

`research_contract.json` is the downstream machine contract consumed by gates, Scriptwriter, and Visual Director. Raw provider responses remain as close to provider payloads as possible; normalized files are derived summaries for deterministic gates and retry/reuse validation.

---

## 5. Researcher Cache Policy

| Freshness | Age | Behavior |
|-----------|-----|----------|
| Fresh | 0-60 min | Use directly |
| Stale | 60-240 min | Reuse with stale marking, log |
| Expired | >240 min or new Asia/Jakarta day | Force new research |

**Cache key:** `niche:platform:language:topic_cluster:entities:date`

Entities (named: specific people, places, events) are included in cache key to prevent returning research about Artist A when user asks about Artist B.

---

## 6. Background Music Policy

| Priority | Option |
|----------|--------|
| 1 (default) | No background music |
| 2 (if configured) | Safe stock music |
| 3 (reviewer note) | Recommend platform-native sound during manual TikTok upload |

MVP does not automatically extract or embed copyrighted TikTok audio. ScrapeCreators provides song metadata for reference only.

---

## 7. Asset Safeguards

| Rule | Value |
|------|-------|
| Max clip duration | 5 seconds |
| Min clip duration | 1 second (clips <1s are flash frames, rejected by G9) |
| Min unique sources target | 2. If <2 usable: proceed with 1 + Pexels/generated cards, log risk warning |
| Original voiceover | Required |
| Transformation required | Re-encode → micro-crop → brightness shift → hue shift → pitch shift → metadata strip → per-account parameter variation |
| Attribution | When source is known |
| Risk logging | Always |

### Asset Caching

The primary per-job cache is the job workspace:
- Workspace directory: `ASSETS_CACHE/job_{id}`.
- Agent/gate artifacts and diagnostics live in that workspace for audit, debug observability, and future retry/resume.
- Final deliverables are copied/packaged separately under `OUTPUT_DIR/job_{id}`.

Downloaded clips (yt-dlp) and stock footage (Pexels) may also use an optional source URL hash cache to avoid redundant downloads:
- Global cache pattern: `ASSETS_CACHE/downloads/{url_hash}.{ext}`.
- Cache checked before any download attempt (saves Pexels API calls and yt-dlp I/O).
- Reused media is still copied or referenced through the per-job workspace and recorded in provenance.
- Cache invalidated by source URL change or manual cleanup per retention policy (SRS §6.3).

### Generated Cards

When no source clips or stock footage are available, the Visual Director generates text-based card images:
- **Rendered by:** Pillow or FFmpeg drawtext filter.
- **Format:** Static PNG at 1080x1920.
- **Content:** Headline text from script + colored background from niche template + optional avatar.
- **Style:** Fonts, colors, layout from niche config template definition.
- **Usage:** Integrated into scene sequence by Composer as full-screen slides between other clips.
- **Quality signal:** Jobs using only generated cards (no real clips or stock footage) get escalated risk warning; Reviewer notified.

---

## 8. Variation Strategy & Creative Memory

### Pre-Generation Memory Check

Each creative agent checks `creative_history` **before** generating — prevents repetition without wasting generation tokens.

### Variation Rotation

Script angle, template, and asset mix rotate per topic cluster.

Example angles: `breaking_update` → `fan_reaction` → `timeline_recap` → `what_this_means` → `controversy_context`.

### Creative History Record

Per topic cluster: stores used angles, hooks, templates, assets, CTAs.
Checks: same topic cluster + same generation batch (strict), same account recent history (light signal, not block).

---

## 9. Configuration Hierarchy

```
Agent Defaults (global base config)
    → Niche Profile Overrides (e.g., indonesian_artists)
        → Account Overrides (per-client customizations)
            → Job-Level Overrides (one-off changes)
```

Every level overrides the previous. Config patches versioned with rollback support.

| Setting | Researcher | Scriptwriter | Voice | Visual | Composer | Reviewer | Safety |
|---------|-----------|-------------|-------|--------|----------|---------|--------|
| LLM Model | ✅ | ✅ | N/A | ✅ | N/A | ✅ | ✅ |
| API Key | ✅ | ✅ | ✅ | ✅ | N/A | ✅ | ✅ |
| Prompt Version | ✅ | ✅ | N/A | ✅ | ✅ | ✅ | ✅ |
| Temperature | ✅ | ✅ | N/A | ✅ | N/A | ✅ | ✅ |
| Max Tokens | ✅ | ✅ | N/A | ✅ | N/A | ✅ | ✅ |
| Voice ID | N/A | N/A | ✅ | N/A | N/A | N/A | N/A |

### Niche Profile Example

```yaml
niche:
  name: indonesian_artists
  language: id
  tone: casual_tiktok
  video_length:
    target: 30s
    hard_limit: 60s
  voice:
    provider: elevenlabs
    default_voice_id: "configured_indonesian_casual_voice"
  thumbnail:
    template: headline_frame
    resolution: 1080x1920
  content_angle: trending_artist_update
  safety_rules:
    - no_defamation
    - mark_rumors_as_unconfirmed
    - soft_wording_for_unverified
  caption_style: short_with_hashtags
```

### Environment Configuration Layer

Below the agent-default level, the system loads base configuration from `.env` via `python-dotenv`:

- **`AppSettings`** (`pydantic-settings` `BaseSettings`) — typed config class at `clipper_agency/config/schema.py` mapping env vars 1:1 (uppercased) to fields.
- **`load_dotenv()`** — called once at `clipper_agency/__main__.py` import time, before any service reads `os.getenv()`.
- **Fields:** `db_path`, `assets_cache`, `output_dir`, `dashboard_secret_key`, `dashboard_username`, `dashboard_password`, `llm_api_key`, `elevenlabs_api_key`, `gemini_api_key`, `gemini_tts_voice_name`, `fish_audio_api_key` (alias `FISHAUDIO_KEY`), `fish_audio_voice_id`, `elevenlabs_voice_id`, `pexels_api_key`, `scrapecreators_api_key`, `firecrawl_api_key`, `log_level`, `safety_model` (default `mimo-v2-flash`), `researcher_model` (default `mimo-v2-flash`), `scriptwriter_model` (default `mimo-v2-flash`), `reviewer_model` (default `mimo-v2-flash`).
- **Usage:** CLI (`__main__.py`) and dashboard (`app.py`) call `load_settings()` to resolve paths and secrets. Services read keys directly via `os.getenv()`. Agents read their model from `load_settings().<agent>_model` instead of hardcoding.
- **Test isolation:** Tests must use both `AppSettings(_env_file=None)` and `patch.dict(os.environ, {}, clear=True)` to prevent the user's `.env` (loaded by `load_dotenv()` at import) from leaking into test expectations.
- **Cache path helpers:** `clipper_agency/core/paths.py` provides `job_cache_dir()`, `agent_dir()`, `agent_input_file()`, `agent_output_file()`, `gate_result_file()`, `researcher_brief_file()`, `researcher_contract_file()`, `voice_scene_file()`, `visual_scene_file()`, and `job_final_output_dir()` for consistent per-job cache/final paths.

#### Voice Provider Fallback

The `VoiceProducerAgent` attempts providers in order and records sanitized attempts:

| Priority | Env Var | Service | Model |
|----------|---------|---------|-------|
| 1 (highest) | `ELEVENLABS_API_KEY` | `ElevenLabsService` | Configured voice ID |
| 2 | `GEMINI_API_KEY` | `GeminiTTSService` | `gemini-2.5-flash-preview-tts`, default voice `Kore` |
| 3 | `FISH_AUDIO_API_KEY` or `FISHAUDIO_KEY` | `FishAudioService` | `s2-pro` via `POST /v1/tts` |

- **Fallback voice IDs** per provider: `elevenlabs_voice_id`, `gemini_tts_voice_name`, or `fish_audio_voice_id`.
- If a provider key is missing or a provider returns an API/HTTP error, the agent tries the next provider.
- If no provider succeeds, the pipeline stops with a clear error and `provider_attempts.json` records provider name, status, sanitized message, latency, HTTP code, and output path if successful.

---

### Agent Autonomy Levels

Each agent has a configurable autonomy level that controls how the orchestrator handles gate transitions. Configured per-agent via the hierarchy in §9 (agent defaults → niche → account → job).

| Level | Behavior | Use Case |
|-------|----------|----------|
| **Autonomous** (default) | Agent runs through gates without human intervention. Gates apply pass/soft-fail/hard-fail rules automatically. | Normal production runs (all 7 MVP agents) |
| **Semi-Autonomous** | Agent runs but orchestrator pauses for human approval at each gate transition. Dashboard shows gate result and awaits explicit continue/abort. | High-cost agents (Reviewer with premium models), high-risk topics, debugging |
| **Manual** | Agent requires explicit human trigger to start each step. No automatic gate transitions. | Training, testing new prompts, validating new niches |

**Orchestrator behavior by level:**

- **Autonomous:** Gate evaluates → action taken automatically (pass → next step, soft-fail → continue with warning, hard-fail → stop + notify).
- **Semi-Autonomous:** Gate evaluates → dashboard notification + await human response. Human can approve pass/soft-fail, escalate hard-fail, or abort.
- **Manual:** No gate evaluation until human triggers step. Human sees input and output at each stage.

**Override rules:** Autonomy level can be elevated (more human involvement) at runtime via dashboard or CLI. Cannot be lowered below configured minimum without Admin/Creative Lead approval. All autonomy changes logged in audit trail.

**SRS traceability:** Implements FR-17 (Configurable agent autonomy levels, P1 MVP).

---

## 10. Video Templates

| Template | Style | Best For |
|----------|-------|----------|
| **News Card** | Headline + image + facts + captions | Quick updates |
| **B-Roll Narration** | Voiceover + clips + dynamic captions | Context-rich stories |
| **Rapid Update** | Fast cuts + punchy captions | Trending gossip |

FFmpeg-based. Layout in config (positions, fonts, colors, animations). 1080x1920 vertical. Template mode: `manual | agent_select | hybrid`.

---

## 11. Database Schema (MVP)

| Table | Purpose |
|-------|---------|
| `niches` | Niche configurations |
| `accounts` | TikTok accounts (multi-tenant ready) |
| `jobs` | Video generation jobs |
| `agent_states` | Per-agent state per job |
| `agent_configs` | Per-agent LLM, prompt, model config |
| `templates` | Video template definitions |
| `assets` | Asset metadata (source, license, hash, provider) |
| `research_cache` | Cached research with Time To Live (TTL) expiry |
| `job_outputs` | Final output metadata |
| `audit_log` | All actions for compliance |
| `config_versions` | Versioned config patches |
| `prompt_versions` | Prompt version tracking |
| `creative_history` | Used angles/templates/assets per topic |
| `job_snapshots` | Full reproducibility data |
| `preflight_estimates` | Lightweight cost estimate |

SQLite for MVP (same schema migrates to PostgreSQL). Multi-tenant from day one.

---

## 12. Cost Optimization

### Model Selection (May 2026)

| Model | Input $/1M | Output $/1M | Best For |
|-------|-----------|-------------|----------|
| GLM-4-9B | $0.01 | $0.01 | Ultra-cheap: safety, memory checks |
| MiMo-V2-Flash | $0.09 | $0.29 | Default text (Claude quality at 3.5% cost) |
| Qwen3-32B | $0.18 | $0.28 | Indonesian-sensitive scripts |
| Gemini 2.5 Flash | $0.15 | $0.60 | Multimodal: reviewer |
| DeepSeek V3.2 | $0.25 | $0.38 | Multilingual reasoning |
| MiniMax M2.7 | $0.30 | $1.20 | Agentic planning (Stage 2) |
| Kimi K2.5 | $0.44 | $2.00 | Premium fallback |

### Presets

| Preset | Models | LLM Cost/Job |
|--------|--------|-------------|
| **Budget East** | MiMo-V2-Flash, Qwen3-32B, GLM-4-9B | ~$0.003 |
| **Agentic East** | MiniMax M2.7, DeepSeek V3.2 | ~$0.008 |
| **Premium East** | Kimi K2.5, Qwen Max, GLM-5.1 | ~$0.015 |
| **Premium West** | Claude Sonnet 4, GPT-5, Gemini Pro | ~$0.04 |

---

## 13. MVP Deliverables

1. **7 MVP Agents** — Safety, Researcher, Scriptwriter, Voice Producer, Visual Director, Composer, Reviewer
2. **Orchestrator** — Gated state machine with human-triggered retry
3. **Creative Memory** — Pre-generation check, variation rotation
4. **Web Dashboard** — Agent observability, config editing, basic auth + 2 groups
5. **CLI** — `python3 cli.py run --topic "..." --niche indonesian_artists`; `test-agent` subcommand for independent agent debugging; `--log-level` option
6. **3 Templates** — News Card, B-Roll Narration, Rapid Update
7. **Config System** — Agent → Niche → Account → Job hierarchy with versioning
8. **Output Packager** — `video.mp4` + `caption.txt` + `thumbnail.png` + `metadata.json`
