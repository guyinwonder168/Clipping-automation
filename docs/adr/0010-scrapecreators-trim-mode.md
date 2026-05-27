# ADR 0010: ScrapeCreators Trim Mode with Dual-Format Field Extraction

**Date:** 2026-05-27
**Status:** Accepted
**Commits:** `da4aafd` (partial), `978a462`, `1e52b2e` (partial)
**Phase:** 11 + post-Phase 11

## Context

The ScrapeCreators TikTok search API returned massive raw responses — 1-2MB per request — because each result included the full TikTok `aweme_info` object (video metadata, creators, comments, music, hashtags, user profiles, etc.). The pipeline needed only a handful of fields (description, engagement stats, video URL, music metadata).

Two additional issues emerged after initial implementation:
1. **Missing `url` key**: The orchestrator read the key `url` from extracted results to pass source URLs to the Visual Director, but the extraction emitted `share_url` instead — causing the Visual Director to receive empty source URLs and produce video-less output.
2. **Trim vs full response format**: With `trim=true`, the API returns flat objects (fields at the top level), but without trim, fields are nested inside `aweme_info`. The extraction code only handled the nested format.

## Decision

### Data Minimization at the API Level

- **`trim=true`** parameter: Instructs the ScrapeCreators API to return flat, minimal responses instead of full `aweme_info` payloads. This reduces response size from 1-2MB to ~500 chars per result.
- **`MAX_RESULTS = 20`**: Caps the number of results processed.
- **`MAX_CHARS_PER_DESC = 300`**: Truncates long descriptions.

### Field Extraction (`_extract_fields`)

Extract only pipeline-relevant fields from each result:

| Field | Source | Purpose |
|-------|--------|---------|
| `desc` | `desc` (trimmed) | Niche-relevant description for context |
| `author` | `author.unique_id` | Creator attribution |
| `likes` | `statistics.digg_count` | Popularity signal |
| `comments` | `statistics.comment_count` | Engagement signal |
| `shares` | `statistics.share_count` | Engagement signal |
| `plays` | `statistics.play_count` | Reach signal |
| `url` / `share_url` | `share_url` or `url` (trim mode) | Source URL for Visual Director |
| `video_urls` | `video.bit_rate[].play_addr.url_list` | Download URLs |
| `music` | `music.title` / `music.author` | Background music candidates |
| `hashtags` | `cha_list[].cha_name` | Topic categorization |

### Dual-Format Handling

Both response formats are handled via a single fallback pattern:

```python
source = item.get("aweme_info") or item
```

- **Without trim**: `item` has `aweme_info` wrapper → unwrap it.
- **With trim**: `item` is the flat object → use it directly.
- **Trimmed limitations**: Flat mode has no `music` or `hashtags` keys (API limitation). These return empty defaults.

### URL Key Fix

Extraction emits **both** `url` and `share_url` keys, where `url` falls back from `share_url` → `url` (trim mode uses the flat `url` key). This ensures the orchestrator always finds a source URL regardless of the API response format.

### Default Output Directory Fix

`job_output_dir()` defaults empty `output_dir` to `"outputs"` instead of empty string, preventing path construction artifacts at the filesystem root.

## Alternatives Considered

### Full API responses (no trim)

- **Pros:** All data available.
- **Cons:** 1-2MB per request. 75 credits would exhaust faster due to bandwidth. LLM overflow inevitable (551K char scenarios). No benefit for pipeline needs.

### Post-processing only (no `trim=true`)

- **Pros:** All response data available for future needs.
- **Cons:** Still downloads 1-2MB per request — bandwidth cost, latency. Trim reduces API processing time too.

### Separate endpoints for different data needs

- **Pros:** Clean separation of concerns.
- **Cons:** Multiple API calls per research phase. ScrapeCreators search endpoint is the single entry point for TikTok data.

## Rationale

- `trim=true` reduces both API latency and response size by an order of magnitude with zero loss of pipeline-relevant data.
- Dual-format handling (`source = item.get("aweme_info") or item`) makes the extraction robust regardless of API configuration — adding or removing `trim` doesn't break the pipeline.
- The `url` + `share_url` dual-emit pattern fixes the orchestrator→Visual Director data flow without requiring the orchestrator to know which API format was used.
- Default `output_dir = "outputs"` is a defensive fix that prevents paths like `/job_5/research/` (filesystem root) when `OUTPUT_DIR` is blank.

## Consequences

- **Positive:** Response size reduced from 1-2MB to ~500 chars per result — 2000x reduction.
- **Positive:** Field extraction produces consistent, pipeline-ready dicts regardless of API format.
- **Positive:** `url` key always present — Visual Director always receives source URLs.
- **Positive:** Empty `OUTPUT_DIR` no longer creates paths at filesystem root.
- **Negative:** Trimmed responses lack `music` and `hashtags` — background music selection and topic categorization are degraded (acceptable: music is "none by default" per policy, and hashtags are reconstructed from niche config).
- **Negative:** Dual-format handling adds complexity — new fields added to extraction must account for both formats.
- **Negative:** `_extract_fields()` is a static method with side-effect-free logic but relies on instance attributes (`MAX_CHARS_PER_DESC`) — minor coupling.
