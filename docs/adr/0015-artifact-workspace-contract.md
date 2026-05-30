# ADR 0015: Artifact Workspace Contract — File-Based Agent Communication

**Date:** 2026-05-31
**Status:** Accepted
**Commits:** Phase 12 implementation (multiple commits)
**Phase:** 12 (Artifact Contracts + Debug Observability)

## Context

The original agent framework had no standardized way for agents to exchange data. Each agent received in-memory arguments from the Orchestrator and returned results through return values. This created several problems:

- **No debuggability:** When a job failed, there was no persisted record of what each agent received or produced. Developers had to reproduce failures with logging.
- **No resumability:** A failed agent required restarting the entire pipeline. Partial results from successful upstream agents were lost.
- **No cache reuse:** Re-running a job re-executed all agents, even those whose inputs hadn't changed.
- **Tight coupling:** The Orchestrator needed to know each agent's internal data shape to pass arguments correctly. Adding a new field to an agent's input required Orchestrator code changes.
- **No validation boundary:** There was no clear contract between agents. A malformed output from one agent would cause confusing errors in the next agent.

As the pipeline grew to 7 agents with complex data shapes (research contracts, scene plans, voice files, visual assets), the lack of a formal inter-agent contract became a reliability and debugging bottleneck.

## Decision

Establish a **file-based artifact workspace** where each agent reads input from and writes output to well-known JSON files on disk, managed by shared path conventions in `clipper_agency/core/paths.py`.

### Workspace layout

```
data/assets/cache/job_{job_id}/
├── agents/
│   ├── safety/
│   │   ├── input.json      # Orchestrator writes, Safety reads
│   │   └── output.json     # Safety writes, Orchestrator reads
│   ├── researcher/
│   │   ├── input.json
│   │   ├── output.json
│   │   ├── research_brief.md
│   │   └── research_contract.json
│   ├── scriptwriter/
│   │   ├── input.json
│   │   └── output.json
│   ├── voice_producer/
│   │   ├── input.json
│   │   ├── output.json
│   │   └── voices/
│   │       ├── scene_0.mp3
│   │       └── scene_1.mp3
│   ├── visual_director/
│   │   ├── input.json
│   │   ├── output.json
│   │   ├── scenes/
│   │   │   └── scene_0.mp4
│   │   └── cards/
│   │       └── card_0.png
│   ├── composer/
│   │   ├── input.json
│   │   └── output.json
│   └── reviewer/
│       ├── input.json
│       └── output.json
└── gates/
    ├── G1.json
    ├── G2.json
    └── ...
```

### Key conventions

- **`core/paths.py`** provides all path functions: `agent_input_file()`, `agent_output_file()`, `agent_dir()`, `gate_result_file()`, plus specialized paths (`voice_scene_file()`, `visual_scene_file()`, `researcher_brief_file()`).
- **Orchestrator responsibility:** Write `input.json` before calling agent, read `output.json` after agent completes.
- **Agent responsibility:** Read `input.json`, execute, write `output.json`. Agents don't call other agents.
- **Gate results:** Persisted as `gates/{gate_name}.json` for audit trail.
- **Validation:** `core/validation.py` checks `output.json` existence and valid JSON for every agent as part of G10.

## Alternatives Considered

### In-memory agent communication (original approach)

- **Pros:** Fast, no disk I/O, simpler code.
- **Cons:** No debug trail. No resumability. No cache reuse. Tight coupling between Orchestrator and agents.

### Database-mediated contracts (SQLite tables)

- **Pros:** Transactional, queryable, concurrent access.
- **Cons:** Complex schema management. Binary assets (audio, video) don't fit well in SQLite. Adds DB migration burden for each agent's changing contract shape. Overkill for single-client MVP.

### Message queue (Redis/pubsub)

- **Pros:** Asynchronous, scalable, supports multiple consumers.
- **Cons:** Infrastructure dependency. Operational complexity. Single-client MVP doesn't need async agent execution. Premature optimization.

## Rationale

- **Debuggability:** Every agent's input and output is persisted on disk. When a job fails, inspect `agents/{agent}/input.json` and `output.json` to see exactly what happened. The job debug dashboard (`core/job_debug.py`) reads these files to surface diagnostics.
- **Resumability:** The dashboard/CLI can resume a failed job by re-invoking just the failed agent. Upstream agents' `output.json` files are already on disk. No need to re-run the entire pipeline.
- **Cache reuse:** If upstream agent outputs haven't changed, downstream agents can be skipped. The validation layer (`core/validation.py`) checks cached artifacts.
- **Loose coupling:** The Orchestrator writes `input.json` and reads `output.json`. It doesn't need to know each agent's internal data shape — only the contract schema. Adding new fields to an agent's contract doesn't require Orchestrator changes.
- **Testability:** Tests can create `input.json` files and verify `output.json` without mocking the entire Orchestrator. Agent tests become self-contained.
- **File-based simplicity:** JSON files are human-readable, diffable, and require no infrastructure beyond a filesystem. Appropriate for single-client SQLite-backed MVP.

## Consequences

- **Positive:** Full debug trail for every job — every agent's input and output persisted and inspectable.
- **Positive:** Job resumability — failed agents can be retried without re-running upstream.
- **Positive:** Agent independence — agents don't import or call each other. Communication is through file contracts only.
- **Positive:** Simple testing — create input files, run agent, assert output files.
- **Negative:** Disk I/O overhead — every agent reads/writes JSON files. Negligible for MVP scale.
- **Negative:** Contract schema evolution — changing an agent's input/output schema requires backward-compatible migration or versioning. Not yet implemented.
- **Negative:** No concurrent job isolation — two jobs writing to the same `assets_cache` path could collide. Mitigated by `job_{job_id}` isolation, but not enforced at the filesystem level.
- **Neutral:** Binary artifacts (audio, video) live alongside JSON contracts in the same workspace. The workspace serves as both a contract store and an asset cache.
