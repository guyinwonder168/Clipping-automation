# Plan: Add Trending TikTok Audio Download to claude-auto-tok

## Context
The `claude-auto-tok` pipeline currently uses a static `DEFAULT_BG_MUSIC` env var for background music. The user wants the pipeline to automatically download trending TikTok audio that matches the Researcher's trend data, with YouTube as fallback — making videos feel native to the platform.

**Current flow:** Researcher scrapes TikToks → ... → Visual Director hardcodes `backgroundMusic: process.env.DEFAULT_BG_MUSIC || null`
**New flow:** Researcher extracts trending audio metadata → Audio Downloader downloads MP3 (TikTok primary, YouTube fallback) → Visual Director uses downloaded audio

---

## Changes

### 1. NEW: `src/agents/audio-downloader.ts` (~120 lines)
Downloads trending audio with 3-tier fallback:
- **Layer 1:** ScrapeCreators v2 Video Info → `music.play_url.url_list[0]` → download MP3 via `fetch()`
- **Layer 2:** YouTube search via `yt-dlp` → download as MP3
- **Layer 3:** Return `null` → falls back to `DEFAULT_BG_MUSIC`

```typescript
export async function runAudioDownloader(
  research: ResearchOutput,
  jobPath: string,
  publicDir: string,
  slug: string
): Promise<string | null>
```

Returns the filename in `publicDir` or `null`. Never throws — always returns `string | null`.

**Filename convention:** `bgm-{topic-slug}.mp3` — derived from the research topic slug (same slug used throughout the pipeline). This makes it easy to identify which topic the audio belongs to. Example: topic `"why every dev needs an AI IDE"` → slug `why-every-dev-needs-an-ai-ide` → filename `bgm-why-every-dev-needs-an-ai-ide.mp3`. The slug is already computed by the orchestrator and passed as a parameter. Saves to `jobPath/bgm-trending.mp3`, copies to `publicDir/bgm-{slug}.mp3`.

### 2. MODIFY: `src/state.ts`
Add `TrendingAudio` interface and extend `ResearchOutput`:
```typescript
export interface TrendingAudio {
  video_id: string;       // aweme_id of the video with trending audio
  song_title: string;     // music.title from TikTok
  song_author: string;    // music.author from TikTok
  sound_id: string;       // music.id_str
  search_query: string;   // YouTube fallback query: "song_title song_author audio"
}
```
Add `trending_audio: TrendingAudio | null` to `ResearchOutput`.

### 3. MODIFY: `src/agents/researcher.ts`
- Add `TikTokMusic` interface (title, author, id_str, play_url, duration)
- Add optional `music?: TikTokMusic` to `TikTokVideoItem`
- Add `getVideoMusic(awemeId)` helper — calls ScrapeCreators v2 endpoint
- After sorting top videos by play count, call `getVideoMusic(topVideos[0].aweme_id)` to get trending audio metadata
- Force-set `parsed.trending_audio = trendingAudio` on the LLM output (no prompt changes needed)

### 4. MODIFY: `src/orchestrator.ts`
- Import `runAudioDownloader`
- Insert between Researcher and revision loop:
  ```typescript
  let trendingBgMusic: string | null = null;
  if (state.research?.trending_audio) {
    trendingBgMusic = await runAudioDownloader(state.research, jobPath, PUBLIC_DIR, slug);
  }
  ```
- Pass `trendingBgMusic` to `runVisualDirector` as new optional 8th parameter
- Audio is downloaded once, reused across all revision loops

### 5. MODIFY: `src/agents/visual-director.ts`
- Add `downloadedBgMusic?: string | null` parameter
- Change line 374 from:
  `backgroundMusic: process.env.DEFAULT_BG_MUSIC || null`
  to:
  `backgroundMusic: downloadedBgMusic || process.env.DEFAULT_BG_MUSIC || null`

### 6. MODIFY: `.env.example`
Add comment about `yt-dlp` for YouTube fallback (optional dependency).

---

## Data Flow
```
Researcher → extracts trending_audio {video_id, song_title, song_author, search_query}
    ↓
Orchestrator → runAudioDownloader()
    ↓ Layer 1: ScrapeCreators v2 → music.play_url → download MP3
    ↓ Layer 2: yt-dlp "ytsearch1:{song_title} {song_author} audio" → download MP3
    ↓ Layer 3: return null
    ↓
Visual Director → backgroundMusic = downloaded || DEFAULT_BG_MUSIC || null
    ↓
Composer → passes backgroundMusic to Remotion renderProps
    ↓
Remotion Template → <Audio src={staticFile(backgroundMusic)} volume={0.12} />
```

---

## New System Dependency
- **`yt-dlp`** — for YouTube audio fallback. Optional; if not installed, Layer 2 is skipped gracefully with a log message.
- Install: `pip install yt-dlp` or `sudo apt install yt-dlp`

No new npm packages needed. Uses existing `fetch()` and `child_process.execSync`.

---

## Edge Cases
- **TikTok audio URL expiry** — CDN URLs are time-limited, so download happens immediately after research
- **Revision loop** — audio downloaded once, reused across revisions (no redundant downloads)
- **Audio shorter than video** — Remotion handles gracefully (plays until audio ends, volume is 0.12)
- **yt-dlp not installed** — Layer 2 skipped, logged, falls through to Layer 3 → DEFAULT_BG_MUSIC
- **No ScrapeCreators API key** — Researcher already handles this (falls back to LLM-only), `trending_audio` will be `null`

---

## Verification
1. `pnpm typecheck` passes
2. Run `pnpm swarm:run "test topic"` — check `output/ready/<slug>/` contains video with trending background audio
3. Check `output/debug/audio-downloader.json` for source used (tiktok/youtube/null)
4. Test Layer 2 fallback: temporarily break ScrapeCreators v2 call → verify YouTube download works
5. Test Layer 3 fallback: remove yt-dlp + break ScrapeCreators → verify DEFAULT_BG_MUSIC is used

---

## ScrapeCreators v2 API Verification (Confirmed)

**Endpoint:** `GET /v2/tiktok/video?id={aweme_id}`

**Verified response fields** from actual API documentation (`aweme_detail.music`):
- `title`: e.g. `"original sound - stoolpresidente"`
- `author`: e.g. `"Dave Portnoy"`
- `id_str`: e.g. `"7463250381684476718"`
- `duration`: e.g. `89` (seconds)
- `owner_handle`: e.g. `"stoolpresidente"`
- `play_url.url_list[0]`: Direct MP3 download URL (e.g. `https://sf77-ies-music-va.tiktokcdn.com/obj/ies-music-ttp-dup-us/7463250409558133546.mp3`)

The `added_sound_music_info` field also exists with identical structure — this is the sound added by the creator, while `music` is the track used.

The plan's assumptions about available fields were **correct and verified**.
