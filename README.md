```
 ██████╗██╗     ██╗██████╗ ██████╗ ███████╗██████╗     █████╗  ██████╗ ███████╗███╗   ██╗ ██████╗██╗   ██╗
██╔════╝██║     ██║██╔══██╗██╔══██╗██╔════╝██╔══██╗   ██╔══██╗██╔════╝ ██╔════╝████╗  ██║██╔════╝╚██╗ ██╔╝
██║     ██║     ██║██████╔╝██████╔╝█████╗  ██████╔╝   ███████║██║  ███╗█████╗  ██╔██╗ ██║██║      ╚████╔╝ 
██║     ██║     ██║██╔═══╝ ██╔═══╝ ██╔══╝  ██╔══██╗   ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║██║       ╚██╔╝  
╚██████╗███████╗██║██║     ██║     ███████╗██║  ██║   ██║  ██║╚██████╔╝███████╗██║ ╚████║╚██████╗   ██║   
 ╚═════╝╚══════╝╚═╝╚═╝     ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝   ╚═╝   
```

# Clipper Agency

**AI-powered TikTok content factory.** Seven autonomous agents work together in a DB-driven pipeline to research, script, voice, compose, and publish short-form video content — all from a single command.

```
Topic ──► Safety ──► Researcher ──► Scriptwriter ──► Voice Producer ──► Visual Director ──► Composer ──► Reviewer ──► Output
  G1         G2         G3/G4/G5       G6                G7                    G8                G9            G10
```

---

## Architecture

Agentic pipeline coordinated by a SQLite-backed orchestrator. Agents never call each other directly — they communicate through database state.

| Gate | Component | Responsibility |
|------|-----------|----------------|
| G1 | Topic | Validate input topic |
| G2 | Safety | Content safety check |
| G3-G5 | Researcher | Gather sources, verify, enrich |
| G6 | Scriptwriter | Write TikTok-optimized script |
| G7 | Voice Producer | Generate voiceover (ElevenLabs) |
| G8 | Visual Director | Source B-roll, compose scene |
| G9 | Composer | Render final video (FFmpeg) |
| G10 | Reviewer | QA the output |

### Output Package

```
outputs/{job_id}/
├── video.mp4          # 9:16 TikTok-ready video
├── caption.txt        # Auto-generated caption
├── thumbnail.png      # Video thumbnail
└── metadata.json      # Job metadata
```

---

## Tech Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.11+ |
| Video | FFmpeg 5.0+ (CPU-only) |
| Database | SQLite (WAL mode, advisory locks) |
| LLM | OpenRouter API (multi-model routing) |
| Voice | ElevenLabs |
| Media | yt-dlp (primary), Pexels (fallback) |
| Research | ScrapeCreators + Firecrawl |

---

## Quick Start

```bash
git clone https://github.com/guyinwonder168/Clipping-automation.git
cd "clipper agency"
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required keys:
- `OPENROUTER_API_KEY` — LLM routing
- `ELEVENLABS_API_KEY` — Voice generation
- `PEXELS_API_KEY` — Stock media
- `FIRECRAWL_API_KEY` — Web research
- `SCRAPECREATORS_API_KEY` — Web scraping

---

## Usage

```bash
# Run the pipeline with a topic
python3 -m clipper_agency "Berita terbaru artis Indonesia"

# Or using the CLI
python3 -m clipper_agency.cli run --topic "Trending topic" --niche indonesian_artists --template news_card
```

### Niche & Template System

Content rules are data-driven — no code changes needed to change platform or tone:

```
niches/         # Niche configurations (language, tone, platform rules)
  └── indonesian_artists.yaml

templates/      # Video templates (scene structure, duration, overlays)
  ├── news_card.yaml
  ├── b_roll_narration.yaml
  └── rapid_update.yaml
```

---

## Project Structure

```
clipper_agency/
├── __init__.py
├── __main__.py              # Entry point: python3 -m clipper_agency
├── cli.py                   # CLI interface
├── config/                  # Configuration loading & schema
├── db/                      # SQLite schema, queries, migrations
├── orchestrator/            # State machine, engine, gates
├── agents/                  # 7 pipeline agents
│   ├── safety.py
│   ├── researcher.py
│   ├── scriptwriter.py
│   ├── voice_producer.py
│   ├── visual_director.py
│   ├── composer.py
│   └── reviewer.py
├── llm/                     # OpenRouter client & model routing
├── services/                # External API integrations
│   ├── elevenlabs.py
│   ├── pexels.py
│   ├── ytdlp.py
│   └── firecrawl.py
├── output/                  # Video packaging & thumbnail
└── dashboard/               # Web UI (future)
```

---

## Development

```bash
# Run tests
python3 -m pytest

# Run a single test
python3 -m pytest tests/path/test_file.py::test_name -v

# Skip external API tests
python3 -m pytest -m "not external"
```

Tests live in `tests/` mirroring the package structure. Integration tests require FFmpeg, SQLite, and API keys.

---

## Status

**MVP in development.** See `docs/plans/2026-05-26-mvp-implementation.md` for the implementation plan.

Detailed specifications: `docs/PRD.md` | `docs/SRS.md` | `docs/technical_design.md`
