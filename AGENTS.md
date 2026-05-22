# AGENTS.md

## Global Rules

- **Documentation**: For checking latest API/docs, use Context7 MCP (`mcp({ connect: "context7" })` then ask).
- **Coding**: Do NOT over-engineer. Keep code simple, minimal, and proportional to the problem. No abstraction layers, no premature patterns, no unnecessary complexity regardless of language.

## Pipeline Reference

Agent reference for the claude-auto-tok pipeline. Each agent is a standalone async function in `src/agents/`. Contracts defined in `src/state.ts`.

---

## 1. Researcher — `src/agents/researcher.ts`

**Model:** Claude Sonnet 4 (via OpenRouter `callClaudeJSON`)

**Input:** `topic: string`

**Output:** `ResearchOutput` — trend status, scored hooks, hashtags, GO/WAIT/PIVOT decision

**How it works:**
1. Queries ScrapeCreators v1 API — `GET /v1/tiktok/search/keyword` and `/v1/tiktok/search/hashtag` with `trim=true` (lightweight results, no music data)
2. Deduplicates videos, sorts by `play_count`, takes top 30
3. Extracts hooks from video descriptions, scores them with heuristic rules (contradiction, knowledge gap, specific number patterns)
4. Calls `getVideoTranscript()` on the top video via ScrapeCreators
5. Sends pre-processed data (top 5 hooks, aggregate stats, trend timing) to Claude for LLM analysis
6. Forces `GO` decision if no real TikTok data was found (LLM can't reliably judge trends without data)

**Key helpers:** `scrapeFetch<T>()` (generic ScrapeCreators wrapper), `searchByKeyword()`, `searchByHashtag()`, `extractHookFromDesc()`, `scoreHook()`, `determineTrendStatus()`

**Edge case:** Dead code at line 332 — `throw new Error("Researcher failed after 3 attempts")` is unreachable (after the return).

---

## 2. Scriptwriter — `src/agents/scriptwriter.ts`

**Model:** Claude Sonnet 4 (via OpenRouter `callClaudeJSON`)

**Input:** `topic`, `research: ResearchOutput`, optional `revisionNotes?: string`

**Output:** `ScriptOutput` — 3 hook variants, chosen hook, full script with voiceover text, caption, hashtags

**How it works:**
1. System prompt specifies target audience (AI coding beginners aged 18-30), tone (casual, excited), and 7 content format options (personal story, hot take, comparison, speed build, myth busting, tutorial bite, reaction)
2. Generates 3 hook variants using 6 proven formulas (contradiction, knowledge gap, bold claim, you're doing it wrong, specific number, POV/relatable)
3. Writes full script for best hook: 0-2s hook → 3-8s tension → 9-20s reveal → 21-28s payoff → last 2-3s CTA
4. Self-reviews on 1-10 scale, rewrites if below 7
5. Overlays are set to `[]` (unused in current templates)

**Revision:** Re-runs with `REVISION NOTES` appended to user prompt when Reviewer targets `scriptwriter` or `both`.

---

## 3. Voice Producer — `src/agents/voice-producer.ts`

**Model:** ElevenLabs `eleven_v3` via voice ID `TX3LPaxmHKxFdv7VOQHJ` (Liam — young, energetic)

**Input:** `voiceoverText`, `jobPath`, `slug`, `publicDir`

**Output:** `VoiceProducerOutput` — word timings with ms precision, voiceover MP3 path, duration

**How it works:**
1. Calls `POST /v1/text-to-speech/{VOICE_ID}/with-timestamps` with character-level alignment
2. Decodes base64 audio to `jobPath/voiceover.mp3`, copies to `publicDir/voiceover-{slug}.mp3`
3. Parses word timings from character-level alignment (`parseWordTimings()`) — maps each word to start/end ms
4. Falls back to proportional timing (`fallbackTimings()`) if alignment data is missing
5. Validates word count matches expected; logs mismatch but proceeds with parsed timings

**Voice settings:** stability 0.40, similarity_boost 0.80, style 0.35, speed 1.05, speaker_boost on.

**Skip optimization:** Orchestrator skips Voice Producer if `voiceover_text` is unchanged from previous revision.

---

## 4. Visual Director — `src/agents/visual-director.ts`

**Model:** Claude Sonnet 4 (via OpenRouter `callClaudeJSON`)

**Input:** `script: ScriptOutput`, `voice: VoiceProducerOutput`, `topic`, `jobPath`, `publicDir`, `slug`

**Output:** `VisualPlan` — template ID, color palette, resolved scenes with assets, CTA timing, thumbnail, background music

**How it works:**
1. **Scene resolution:** `resolveScenes()` maps script overlays to word timing boundaries. If overlays are empty (current default), generates time-based segments (5s each, capped at 6 scenes or available B-roll count)
2. **Template selection:** Always forced to `TerminalReveal` (TemplateA). Has a `FORMULA_TO_TEMPLATE` mapping for future use.
3. **Asset planning:** Sends scene descriptions to Claude with either Pexels system prompt (stock video search queries) or Kling AI prompt (cinematic shot descriptions). Claude returns `scene_assets` array + thumbnail prompt.
4. **Asset generation** (in parallel):
   - Local B-roll library (`public/broll/`) checked first via `selectBrollForScenes()`
   - If Kling API key set: generates AI video clips, falls back to Pexels for failures
   - Otherwise: Pexels stock video search
   - Screenshots and Imagen generations run in parallel
5. **Thumbnail:** Generates via Gemini Imagen 4.0 API (`generateThumbnail()`) — 9:16 vertical
6. **Background music:** Currently hardcoded to `process.env.DEFAULT_BG_MUSIC || null`

**Color palette:** Always `daemon`. Template forced to `TerminalReveal`.

---

## 5. Composer — `src/agents/composer.ts`

**Model:** None (Remotion render)

**Input:** `script`, `voice`, `visual`, `jobPath`, `projectRoot`

**Output:** `videoPath: string | null` — path to rendered MP4

**How it works:**
1. Calculates video duration: `ceil(ctaStartMs / 1000) + 2` seconds
2. Builds `renderProps` JSON with all template data (script, word timings, scenes, palette, voiceover, background music)
3. Saves render props to `jobPath/render-props.json`
4. Executes `npx remotion render src/remotion/Root.tsx {templateId} "{videoOutput}" --props="{propsPath}"` via `execSync` with 5-minute timeout
5. Returns null on render failure (logged, not thrown)

---

## 6. Reviewer — `src/agents/reviewer.ts`

**Model:** Gemini 2.5 Pro (with video) or Gemini 2.5 Flash (metadata only)

**Input:** `topic`, `script`, `voice`, `visual`, `jobPath`

**Output:** `ReviewOutput` — 6-category scores (20 points total), APPROVE/CONDITIONAL/DENY decision, revision notes with target agent

**How it works:**
1. Builds metadata context (word count, duration, words/sec, scene count, hook details, caption stats)
2. Uploads rendered video to Gemini File API via resumable upload (`uploadVideoToGemini()`) — polls until ACTIVE state
3. If video upload succeeds: sends video + metadata to `gemini-2.5-pro` for multimodal review
4. If video upload fails: sends metadata-only to `gemini-2.5-flash`
5. Uploads thumbnail as inline base64 image if available
6. Scores on 6 categories: Hook (0-5), Pacing (0-4), Visual Quality (0-4), Overlay/Subtitles (0-3), Caption/SEO (0-2), Thumbnail (0-2)
7. Hook score < 3 = automatic DENY regardless of total
8. Thresholds: >= 16 APPROVE, 12-15 CONDITIONAL, < 12 DENY

**Revision targeting:** Returns `revision_target` as `"scriptwriter"`, `"visual_director"`, `"both"`, or `null`.

---

## Shared Infrastructure

**`src/agents/llm.ts`** — `callClaudeJSON<T>()` wraps OpenRouter API (`anthropic/claude-sonnet-4`). Retries up to 3 times with exponential backoff (3s, 6s, 9s). Strips markdown code fences before JSON parse.

**`src/agents/prompts.ts`** — System prompts for all agents (currently inlined in agent files; this file may contain shared prompt fragments).

**`src/agents/asset-generator.ts`** — Functions: `takeMultipleScreenshots()`, `generateSceneImages()`, `searchPexelsVideos()`, `generateAIVideos()` — fetch and save assets to `publicDir`.

**`src/agents/broll-library.ts`** — `getAvailableClips()` scans `public/broll/`, `selectBrollForScenes()` picks clips matching scene content.

**`src/state.ts`** — All inter-agent TypeScript interfaces (`ResearchOutput`, `ScriptOutput`, `VoiceProducerOutput`, `VisualPlan`, `ReviewOutput`, `PipelineState`) plus `log()` and `slugify()` helpers.
