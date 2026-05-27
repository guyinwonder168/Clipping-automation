# ADR 0008: File-Based Research Caching with Token Guard

**Date:** 2026-05-27
**Status:** Accepted
**Commits:** `da4aafd` (partial)
**Phase:** 11 (logging, model config, SC cache, test-agent CLI)

## Context

The Researcher agent called ScrapeCreators and Firecrawl APIs on every pipeline run, even for the same topic. This burned through ScrapeCreators' 75 free credits rapidly. Additionally, the raw ScrapeCreators responses could be 1-2MB per request (from TikTok's `aweme_info` payloads), causing LLM prompt overflow when the full response was passed to the synthesis step — in one case reaching 551K characters for a single LLM call, far exceeding context limits and wasting tokens on irrelevant data.

Two separate problems needed solving:
1. **Cache to save API credits** — same-topic research should reuse cached results.
2. **Token guard to prevent LLM overflow** — source data fed to the LLM must be bounded.

## Decision

### File-Based Cache (Per-Job Directory)

Cache ScrapeCreators, Firecrawl, and the synthesized research brief as JSON files in a per-job `research/` subdirectory:

- **Cache paths** (from `clipper_agency/core/paths.py`):
  - `{output_dir}/job_{id}/research/scrapecreators.json`
  - `{output_dir}/job_{id}/research/firecrawl.json`
  - `{output_dir}/job_{id}/research/research_brief.json`
- **Cache-first read**: Before any API call, check if the cache file exists. If hit, return cached data immediately (zero API cost).
- **Cache writes**: After successful API calls, save to cache. API failures return `[]` without saving (so retries re-attempt the call).
- **TTL**: Re-validation happens at the gate level (G3 Research Cache Check) — cache freshness is evaluated separately from data retrieval.

### Token Guard

Bound the total source text passed to the LLM synthesis step:

- **`MAX_SOURCE_CHARS = 40000`** — hard cap on total aggregated source text.
- **`MAX_CHARS_PER_SOURCE = 500`** — per-source truncation to prevent one massive source from dominating.
- Applied in `_aggregate_data()` before the research brief LLM call.

### ScrapeCreators Data Minimization

- **`trim=true`** API parameter reduces raw response size server-side.
- **`_extract_fields()`** extracts only pipeline-relevant fields (description, author, likes, comments, shares, URL, video URLs, music, hashtags), discarding 1-2MB of irrelevant `aweme_info` metadata.
- **`MAX_RESULTS = 20`** limits the number of processed results.
- **`MAX_CHARS_PER_DESC = 300`** truncates individual descriptions.

## Alternatives Considered

### Database cache

- **Pros:** Centralized, queryable, TTL-managed.
- **Cons:** Adds DB schema migration, couples cache to database availability. File cache is simpler and survives DB resets.

### No caching (status quo ante)

- **Pros:** Always fresh data.
- **Cons:** 75 free ScrapeCreators credits would deplete rapidly in testing. Firecrawl daily quota also limited. Not viable for any real usage.

### In-memory cache only

- **Pros:** Fastest reads.
- **Cons:** Lost on process restart. Pipeline runs are sequential (SQLite advisory lock), so in-memory caching provides limited benefit.

### No token guard

- **Pros:** Simpler code.
- **Cons:** 551K character LLM overflow produces unusable output at full API cost. The token guard pays for itself on the first "long source" encounter.

## Rationale

- File-based cache is zero-dependency, transparent (anyone can `cat` the JSON files), and per-job — no cross-job cache pollution.
- The `research/` subdirectory per job groups all research artifacts together for debugging.
- Cache-first reads make repeated runs on the same topic free (no API calls).
- The token guard prevents an expensive failure mode (LLM overflow on huge source data) with a simple character cap.
- `MAX_SOURCE_CHARS=40000` was chosen because it fits comfortably within most LLM context windows (~128K tokens) while still allowing for substantial context — the actual bottleneck was the 551K raw source that exceeded even generous limits.

## Consequences

- **Positive:** Repeated runs on the same topic cost zero API credits.
- **Positive:** LLM synthesis receives bounded input — no more overflow failures.
- **Positive:** Cache files serve as debuggable artifacts — you can inspect exactly what the Researcher saw.
- **Positive:** Cache persists across process restarts.
- **Negative:** Cache is per-job, not cross-job — same topic in two different jobs re-runs API calls. (Acceptable: the cache directory includes job_id, and the TTL gate handles cross-job dedup at the DB level.)
- **Negative:** Cache is never invalidated per-job — if you re-run job_id=5, it uses the old cache. (Acceptable: jobs are meant to be one-shot; retries use the same job_id with fresh gate evaluation.)
- **Negative:** Empty cache (no results found) saves `[]` silently — users don't know if the API returned zero results or wasn't called. (Mitigated: logging shows cache hit vs miss.)
