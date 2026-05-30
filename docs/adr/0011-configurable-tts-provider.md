# ADR 0011: Configurable TTS Provider with Auto-Detection (Fish Audio)

**Date:** 2026-05-27
**Status:** Accepted
**Commits:** `1e52b2e`
**Phase:** Post-Phase 11 (maintenance)

## Context

The pipeline relied exclusively on ElevenLabs for text-to-speech voice generation. During Phase 11 testing, the ElevenLabs free tier returned HTTP 401 with "Unusual activity detected. Free Tier usage disabled." Investigation revealed the free tier was blocked due to multiple free accounts detected on the same residential IP (common Indonesian ISP, not a datacenter).

Pipeline testing was blocked — no voice generation meant no complete video output. Two options emerged:
1. Pay for ElevenLabs Starter ($5/mo) to unblock the existing API key.
2. Add an alternative TTS provider with its own free/paid tier.

## Decision

Add Fish Audio as a configurable, auto-detected TTS provider alongside ElevenLabs:

- **`FishAudioService`** (`clipper_agency/services/fish_audio.py`):
  - Endpoint: `POST https://api.fish.audio/v1/tts`
  - Model: `s2-pro` (latest production model, ELO 1,128 on Speech Arena — #11 globally, competitive quality)
  - Voice: `reference_id` parameter (UUID from fish.audio/model, similar to ElevenLabs voice_id pattern)
  - Auth: Bearer token (`Authorization: Bearer <key>`)
  - Output: MP3 audio saved to `assets/voiceovers/{job_id}.mp3`

- **`VoiceProducerAgent._detect_provider()`** — auto-detection at runtime:

| Priority | Env Var Set | Provider |
|----------|-------------|----------|
| 1 (highest) | `FISHAUDIO_API_KEY` | Fish Audio |
| 2 | `ELEVENLABS_API_KEY` | ElevenLabs |
| — | Neither | Raise error, stop pipeline |

- **`_create_service(provider)`** — dispatches to the correct service class based on detected provider.

- **`AppSettings` fields**:
  - `fish_audio_api_key` (with `validation_alias="FISHAUDIO_API_KEY"`)
  - `fish_audio_voice_id` (env: `FISH_AUDIO_VOICE_ID`)
  - `elevenlabs_voice_id` (env: `ELEVENLABS_VOICE_ID`)

- **Provider-specific voice IDs**: Both `elevenlabs_voice_id` and `fish_audio_voice_id` can be configured simultaneously — switching provider only requires changing which env var is set (or their priority order).

## Alternatives Considered

### Pay for ElevenLabs Starter plan only ($5/mo)

- **Pros:** Zero code changes. Existing integration works.
- **Cons:** Single provider dependency. No fallback if ElevenLabs blocks again. No ability to compare quality/cost across providers. Vendor lock-in.

### Google Cloud Text-to-Speech

- **Pros:** $300 free credit (90 days), supports Indonesian (`id-ID`) voices, best free testing option.
- **Cons:** Requires GCP project setup. Different auth model (service account JSON, not API key). More complex integration than Fish Audio's single-endpoint API. $16/1M chars — more expensive per-character than Fish Audio.

### OpenAI TTS

- **Pros:** Simple API, $15/1M chars (same as Fish Audio), good quality.
- **Cons:** Lower ELO score (1,102 vs Fish Audio 1,128). No Indonesian-specific voice tuning. Single-provider dependency if also using OpenAI for LLM.

### Fish Audio selected because:

- **Cheapest** at $15/1M chars ($11/mo Plus plan for API access), vs ElevenLabs $100/1M chars ($5/mo Starter) — 6.7× cheaper per character.
- **80+ languages** including Indonesian — covers the MVP niche.
- **ELO 1,128** on Speech Arena — competitive quality.
- **Simple API** — single POST endpoint, Bearer auth, no SDK required.
- **Provider-agnostic interface** — same audio file contract as ElevenLabs, easy abstraction.

## Rationale

- Auto-detection (`Fish Audio > ElevenLabs`) means zero config change to switch providers — just set the corresponding env var.
- Provider-specific voice IDs allow both to be configured; switching is just env var ordering.
- The `VoiceProducerAgent` abstraction (`_detect_provider` → `_create_service`) makes adding a third provider a matter of adding one more entry to the detection chain and a new service class.
- Fish Audio's `reference_id` pattern matches ElevenLabs' `voice_id` pattern, keeping the mental model consistent.
- Both free tiers are effectively blocked (ElevenLabs 401, Fish Audio 402), so production use requires a paid plan regardless of provider choice.

## Consequences

- **Positive:** Pipeline is no longer blocked on ElevenLabs — Fish Audio provides a fallback path.
- **Positive:** 6.7× cheaper voice generation ($15/1M chars vs $100/1M chars for ElevenLabs).
- **Positive:** Provider abstraction is clean — adding a third provider (e.g., Google Cloud TTS) requires one new service class + one detection entry.
- **Positive:** Both providers' voice IDs can be configured simultaneously — quick toggle without editing `.env`.
- **Negative:** Fish Audio Plus plan ($11/mo) is more expensive than ElevenLabs Starter ($5/mo), though per-character cost is lower. Tradeoff: higher fixed cost, lower variable cost.
- **Negative:** Fish Audio has no free API tier (unlike ElevenLabs' now-blocked free tier). Testing requires a paid account.
- **Negative:** Fish Audio Indonesian voice quality is untested in production — may need tuning or fallback.
- **Negative:** `_detect_provider()` uses `os.getenv()` directly (not `AppSettings`), matching the pattern used by other services. This means the detection runs before `load_settings()` is called — acceptable because `load_dotenv()` at import populates `os.environ` first.
