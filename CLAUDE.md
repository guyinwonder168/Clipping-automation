# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pnpm swarm:run "topic here"   # Run full pipeline (takes ~5-8 min)
pnpm remotion:studio           # Preview templates in browser
pnpm typecheck                 # TypeScript check (no test suite)
```

No test framework is configured. Verify changes with `pnpm typecheck` and manual pipeline runs.

## Architecture

**Pipeline:** 6 agents chained sequentially by `src/orchestrator.ts`, with a revision loop (max 2 retries) driven by the Reviewer agent's score.

```
Topic → Researcher → Scriptwriter → VoiceProducer → VisualDirector → Composer → Reviewer
                                                                      ↑              │
                                                                      └── revision ←──┘
```

**Agent contracts** are all defined in `src/state.ts` as typed interfaces. Each agent reads its upstream contract and produces its own. The `PipelineState` object threads through the whole pipeline and gets checkpointed to `output/jobs/<slug>/pipeline-state.json` after each agent.

**LLM calls:** Two providers — `src/agents/llm.ts` wraps Claude via OpenRouter, Gemini is called directly via `@google/generative-ai`. Claude is used for Scriptwriter and Visual Director. Gemini is used for Researcher and Reviewer.

**Rendering:** Remotion 4.x renders 9:16 video from 6 template components (`TemplateA-F.tsx`). All templates share `TemplateProps` from `src/remotion/palettes.ts` which includes `backgroundMusic`, voiceover, word timings, scenes, and color palette. Templates use `<Audio src={staticFile(backgroundMusic)} volume={0.12} />` — the prop is already wired, only the value needs to be set.

**Assets:** Visual Director plans scenes with `SceneAsset` types (screenshot, imagen, stock-video, code-typing, none). `src/agents/asset-generator.ts` fetches from Pexels/Kling/Imagen. B-roll clips managed by `src/agents/broll-library.ts`.

**Environment:** All API keys in `.env` (see `.env.example`). Required: OpenRouter, Gemini, ElevenLabs, ScrapeCreators, Pexels. System requires Node 18+, pnpm, Chrome/Chromium.

## Key patterns

- **Agent functions** follow the signature: `runXxx(input, ...) => Promise<XxxOutput>` — they don't mutate PipelineState directly, the orchestrator assigns the result.
- **ScrapeCreators API** calls in Researcher use v1 search with `trim=true` (returns lightweight results without music data). The v2 video info endpoint returns full `aweme_detail` including `music.play_url`.
- **Slug convention:** Topic is slugified (`slugify()` in `state.ts`) and appended with timestamp for job folder uniqueness.
- **Debug output:** Every agent writes structured JSON to `output/debug/<agent>.json`. Pipeline state checkpointed after each agent step.
- **Revision targeting:** Reviewer specifies `revision_target` as `"scriptwriter"`, `"visual_director"`, or `"both"` — orchestrator only re-runs the targeted agents.
- **Voice skip optimization:** If script revision doesn't change `voiceover_text`, Voice Producer is skipped (text comparison in orchestrator).
