# ADR 0003: Use yt-dlp as MVP Media Layer

**Date:** 2026-05-25
**Status:** Accepted

## Context

Clipper Agency needs to download video/audio clips from social media platforms for compositing into generated content. The MVP must handle downloads from TikTok, YouTube, Instagram, and other platforms.

## Decision

Use **yt-dlp** as the primary (Layer 1) media downloader for MVP, with **Pexels** as fallback for stock footage.

## Alternatives Considered

### Pexels-Only (No Downloads)

- Use only licensed stock footage from Pexels API.
- **Pros:** No copyright risk. Simple.
- **Cons:** Defeats the purpose of "Clipper" — the system is specifically designed to clip trending content. Stock footage is generic and cannot capture trending artist moments. This would make the product generic and uncompetitive.

### Cobalt/pybalt

- Different download engine.
- **Pros:** Different architecture, may work when yt-dlp doesn't.
- **Cons:** Less mature. Fewer supported sites. Not enough benefit to justify as primary MVP downloader.

### Specialist APIs Only (Douyin, instaloader)

- Platform-specific downloaders.
- **Pros:** Better per-platform reliability.
- **Cons:** Multiple dependencies. More maintenance. Not needed for MVP with 1 account. Over-engineering for Stage 1.

## Rationale

- yt-dlp supports 1000+ sites including TikTok, YouTube, Instagram, Twitter.
- Single dependency for all platforms in MVP.
- Active community, frequently updated for site changes.
- Python-native (`pip install yt-dlp`).
- Pexels as fallback ensures content can always be generated even when downloads fail.
- Specialist providers (Cobalt, instaloader, Douyin API) deferred to Stage 2+ as Layer 2/3 fallbacks.
- Source URLs come from Researcher's structured output (ScrapeCreators + Firecrawl research).

## Safeguards

- All clips limited to 5 seconds.
- Multi-source target (2 unique sources per video).
- Transformation required (crop, speed, overlay, pitch shift, metadata strip).
- Original voiceover required.
- Risk logging always on.
- If download fails or no source URL: Pexels/local asset/generated cards fallback.

## Consequences

- yt-dlp must be kept updated (site changes happen frequently).
- Configurable sleep intervals and user-agent rotation for anti-detection.
- Cobalt fallback added in Stage 2 for resilience.
- Clip safeguards enforced by Visual Director and Asset Validation Gate.
