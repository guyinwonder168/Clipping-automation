# AGENTS.md

Project-specific instructions for AI agents working in this repository.

## Repository State

- **Greenfield project** — early implementation phase (Phase 0-2 complete).
- All implementation is ahead of us.

## Python Commands

- Use `python3` for all Python commands.
- Do **not** use `python`; this environment may not provide it.
- Prefer module execution when applicable:

```bash
python3 -m pytest          # run all tests
python3 -m pytest tests/path/test_file.py::test_name -v  # single test
python3 -m pip install -r requirements.txt
python3 -m clipper_agency  # run the app (once implemented)
```

## Shell Command Notes

- The project path contains a space: `clipper agency`.
- Always quote paths when needed.
- Prefer setting the command working directory instead of using `cd` in commands.

## Git Branching & PR Workflow

**Never push directly to `master`.** Every phase of work must go through a branch + PR + SonarCloud gate.

```
                         Create     Push     Open      SonarCloud   Merge    Delete
 Phase N Start ────────► branch ──► push ──► PR ────► passes? ──► PR ────► branch
                                    │         │         │           │
                                    │         │         └─ fix ────┘
                                    │         │
                                    └─────────┘
```

### Per-Phase Workflow

1. **Create feature branch** — `phase/N-short-description`
   ```bash
   git checkout -b phase/N-short-description
   ```
2. **Implement** — TDD: tests first, code, commit incrementally. Multiple commits per phase are fine.
3. **Push branch** — `git push -u origin phase/N-short-description`
4. **Create PR** — via `gh pr create`:
   ```bash
   gh pr create --base master --title "Phase N: Feature Title" --body "Implements feature per the implementation plan."
   ```
5. **Wait for SonarCloud** — PR must show ✅ green from SonarCloud Quality Gate.
   - If SonarCloud fails (bugs, vulnerabilities, code smells), fix issues on the branch, push again, and wait for re-check.
   - **Do NOT merge until SonarCloud passes.**
6. **Merge** — **without squashing** (retain commit history):
   ```bash
   gh pr merge phase/N-short-description --merge
   ```
   - Never squash or rebase-merge. Use `--merge` (true merge commit).
7. **Delete branch** — after merge succeeds:
   ```bash
   git branch -d phase/N-short-description           # local
   git push origin --delete phase/N-short-description  # remote
   git checkout master && git pull origin master
   ```
8. **Update docs** — update `AGENTS.md` (Repository State) and the plan document to reflect the completed phase.
9. **Start next phase** — create new branch from updated master.

### Commit Message Convention

```
feat: brief description of change
fix: brief description of fix
docs: brief description of doc change
test: brief description of test change
refactor: brief description of refactor
```

### Branch Naming

```
phase/0-scaffolding     phase/4-agent-framework   phase/8-config-prompts
phase/1-config          phase/5-agents            phase/9-docker
phase/2-database        phase/6-orchestrator
phase/3-services        phase/7-dashboard
```

### Rules

- ❌ NEVER push directly to `master`.
- ❌ NEVER merge a PR before SonarCloud passes.
- ❌ NEVER squash or rebase-merge — always use `--merge` (true merge commit).
- ✅ Always delete the feature branch after successful merge.
- ✅ Always pull master after deleting branch to stay in sync.

## Architecture (MVP)

Agentic pipeline coordinated by a DB-driven orchestrator:

```
Topic → Safety → Researcher → Scriptwriter → Voice Producer → Visual Director → Composer → Reviewer → Output
  G1      G2      G3/G4/G5       G6              G7                G8                G9        G10
```

- 7 agents, 10 gates (G1-G10), state persisted in SQLite.
- Agents communicate via DB state — no direct agent-to-agent calls.
- Output package: `video.mp4` + `caption.txt` + `thumbnail.png` + `metadata.json`.
- **MVP scope:** 1 client, 1 TikTok account, Indonesian artist infotainment niche.

## Tech Stack

| Component | Choice |
|-----------|--------|
| Language  | Python 3.11+ |
| Video     | FFmpeg 5.0+ (CPU-only, no GPU) |
| Database  | SQLite (WAL mode, advisory locks) |
| LLM       | OpenRouter API (multi-model routing) |
| Voice     | ElevenLabs |
| Media     | yt-dlp (primary), Pexels (fallback) |
| Research  | ScrapeCreators + Firecrawl |
| Auth      | Basic auth, 2 groups (privileged, creative/ops) |

## Documentation Structure

```
docs/
├── PRD.md                          # Product requirements (v2.0)
├── SRS.md                          # Software requirements spec (v2.0)
├── technical_design.md             # Architecture & design (v3.0)
├── requirements_traceability.md    # Traceability matrix
├── social-media-api-comparison.md  # Research output
├── adr/                            # Architecture Decision Records
│   ├── 0001-use-python-ffmpeg.md
│   ├── 0002-use-agentic-pipeline.md
│   └── 0003-use-ytdlp-as-mvp-media-layer.md
├── design/
│   └── evolution_plan.md           # Future-stage details (out of MVP)
├── plans/                          # Implementation plans
└── old/                            # Archived previous versions
```

**Key doc rule:** Keep product requirements, technical specs, and architecture in **separate** documents — never merge them.

### ADR Format

When making a significant decision, create an ADR in `docs/adr/NNNN-title.md` following the existing format: Context → Decision → Alternatives Considered → Consequences.

## Directories & Conventions

| Path | Purpose |
|------|---------|
| `refference/` | External reference projects (note: misspelled dir name, intentional) |
| `.firecrawl/` | Auto-generated Firecrawl research outputs — do not edit |
| `.memsearch/` | Auto-generated memsearch data directory |

- No `opencode.json` exists yet — this repo has no OpenCode-local config.

## Testing Expectations

Once code exists:
- Unit tests live in `tests/` mirroring package structure.
- Integration tests require: FFmpeg 5.0+, SQLite, API keys for OpenRouter/ElevenLabs/Pexels/ScrapeCreators/Firecrawl.
- Tests that call external APIs must use `pytest` markers to allow offline runs:
  ```bash
  python3 -m pytest -m "not external"  # skip API-dependent tests
  ```

## Niche & Template Config

Content rules (language, tone, platform) are **data-driven, not hardcoded**:
- Niches: `niches/*.yaml`
- Templates: `templates/*.yaml`
- Changing niche or template should never require code changes.
