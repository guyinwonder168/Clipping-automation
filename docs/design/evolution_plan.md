# Clipper Agency — Evolution Plan

**Version:** 2.1
**Date:** 2026-05-27
**Status:** Final — MVP Implementation Complete (Phase 0-9)

---

## Purpose

This document contains all future-stage details that were removed from MVP docs to keep them lean. Every item here is explicitly out of MVP scope. Referenced by `docs/PRD.md` §14.

---

## Stage 1.5 — MVP+ Analytics

### Scope

- Post URL input after manual upload
- Public metrics collector (views, likes, comments, shares) from public TikTok post URLs
- Basic snapshot dashboard showing collected metrics over time
- Snapshot schedule: 15m, 1h, 3h, 6h, 24h, 48h, 7d, 30d after posting

### New Tables

| Table | Purpose |
|-------|---------|
| `posted_videos` | post_id, platform, account_id, post_url, posted_at, job_id, thumbnail_url |
| `analytics_snapshots` | video_id, collected_at, views, likes, comments, shares, source, source_method |

### Input

Manual: user enters post URL + platform + account + posted_at + job_id after uploading.

---

## Stage 2 — Dashboard, Approval, Providers, Budget

### Scope

- Improved dashboard with job history and advanced approval workflow
- Serper API as backup search when Firecrawl daily quota exhausted (2,500 free credits)
- CSV import for Creator Studio / Insights export
- Budget envelope with daily/monthly limits per client/account
- Actual cost tracking per agent/tool per job
- Full preflight cost/risk estimator (not just lightweight warning)
- Creative Director Agent: proposes new angles/templates when variation exhausted

### Budget Envelope

```yaml
budget_governance:
  monthly_visible_budget_for_creatives: $50
  per_job_creative_approval_limit: $0.50
  daily_spend_limit: $5.00
  emergency_override:
    max_per_day: 1
    max_multiplier: 2x
    requires_reason: true
    alerts_admin: true
```

### New Tables

| Table | Purpose |
|-------|---------|
| `budget_envelopes` | Per-client/account limits and spend |
| `actual_costs` | Per-agent/per-tool actual cost |
| `client_financials` | Payment, revenue, margin (restricted) |
| `agent_proposals` | Creative Director proposals for approval |

### Full Role Model

| Role | Access |
|------|--------|
| Admin | Everything + financial data |
| Creative Lead | Approve jobs, emergency override, operational budget |
| Creative User | Create jobs, see estimated cost |
| Reviewer | Approve/reject output packages |

### Media Provider Expansion

- Cobalt/pybalt (Layer 2, different download engine)
- Serper API for backup search

### Cost Tracking

Estimated vs actual cost per job, per agent, per tool. Enables profitability calculation.

---

## Stage 2+ — Official API Connectors, Baselines, Outlier Detection

### Scope

- Official API connectors with OAuth:
  - TikTok Display API (video.list → view_count, like_count, comment_count, share_count)
  - Instagram Graph API (media insights → views, likes, comments, saved, shares, reach)
  - YouTube Data + Analytics API (views, likes, comments, engagedViews, averageViewDuration)
- Account baseline tracking (rolling median of key metrics per account per platform)
- View velocity calculation
- Outlier detection
- DuckDuckGo site-filtered search (unlimited, free fallback)

### Source Priority Chain for Analytics

```
1. Official API → 2. Public scraper → 3. CSV import → 4. Manual correction
```

### New Tables

| Table | Purpose |
|-------|---------|
| `account_baselines` | Rolling median views/likes/comments per account per platform |
| `analytics_collection_runs` | Collector run history, errors, retries per post |

### Derived Metrics

```text
engagement_rate  = (likes + comments + shares + saves) / views
view_velocity    = (views_now - views_prev) / hours_since_previous
outlier_score    = views / account_median_views_at_same_age
growth_accel     = current_velocity / previous_velocity
```

### Trending Status Logic

| Status | Rule |
|--------|------|
| New | Posted < 1h |
| Rising | velocity > 1.5x baseline AND < 3x |
| Trending | velocity > 3x baseline AND engagement_rate > baseline |
| Outlier | outlier_score > 2x |
| Flat | Velocity decays 2+ consecutive snapshots |
| Underperforming | views < 50% median after 24h |

### Metrics Availability

| Metric | Public Scraper | Official API | CSV Export |
|--------|---------------|-------------|-----------|
| views, likes, comments, shares | ✅ | ✅ | ✅ |
| saves, reach, impressions | ❌ | ✅ | ✅ |
| watch time, retention | ❌ | ✅ (limited) | ✅ |
| profile visits, follows | ❌ | ✅ (permissions) | ✅ |

### Media Provider Expansion

- instaloader (Instagram specialist, Layer 3)
- Douyin_TikTok_Download_API (TikTok/Douyin specialist, Layer 3)
- gallery-dl (image galleries, Layer 3)

### Selection Flow (Stage 2+)

URL → extract platform → try specialist → try yt-dlp → try Cobalt → fallback to Pexels. All config-driven, all optional via toggle.

---

## Stage 3 — Automation, Multi-Account, Learning Loop

### Scope

- Scheduled automated content generation
- Multi-account management per client
- TikTok Direct Post API integration (requires 3-4 week approval)
- Posting automation with auto-track after upload
- Job queues with DB-backed queue
- Learning loop: analytics feeds Creative Memory
- Parallel workers (2-3)

### Learning Loop

```text
analytics_snapshots
    → content_performance_by: hook_type, template, topic, video_length, posting_time, asset_source
    → Creative Memory: hard-avoid underperforming patterns
    → Template Selection: recommend best-performing template per topic
    → Posting Schedule: recommend optimal posting hour per account
    → Niche Profile: auto-adjust rules based on what works
```

### Deployment

Docker Compose on VPS. PostgreSQL. DB-backed queue. 2-3 parallel workers. Per-account limiter.

### Automatic Input (Stage 3+)

Researcher finds trending topics without user input via:
- Google Trends RSS
- News RSS feeds
- Deeper creator history/profile research via ScrapeCreators

---

## Stage 3+ — Multi-Platform, Multilogin

### Scope

- Multi-platform publishing (Instagram Reels, YouTube Shorts)
- Multilogin + Playwright for per-account workspace isolation
- Browser automation for dashboard-only metrics fallback
- Automated upload via browser automation

### Analytics Configuration (Full Example)

```yaml
analytics:
  collection_enabled: true
  schedule_hours: [0.25, 1, 3, 6, 24, 48, 168, 720]
  sources:
    official_api:
      tiktok_display: true
      instagram_graph: true
      youtube_analytics: true
    public_scraper:
      enabled: true
    csv_import:
      enabled: true
    multilogin_browser:
      enabled: true
  baselines:
    min_videos_for_baseline: 10
    recalculate_days: 7
    outlier_threshold: 2.0
    trending_velocity_multiplier: 3.0
    rising_velocity_multiplier: 1.5
```

---

## Stage 4+ — Client Portal, Billing, Scale

### Scope

- Client-facing portal
- Billing and invoicing
- Scale to 1,000+ accounts across multiple niches
- Kubernetes / multi-VPS deployment
- PostgreSQL + Redis
- RQ/Celery workers with auto-scale
- Object storage for final outputs
- Monitoring dashboard
- Full compliance controls and immutable audit logging
- Per-client workspace isolation
- Rate-limit manager
- Advanced retry dashboard and observability

### Deployment

```
Full (1000+)
┌──────────────────┐
│ K8s / Multi-VPS  │
│ PG + Redis       │
│ RQ/Celery workers│
│ Auto-scale       │
│ Object storage   │
│ Monitoring       │
└──────────────────┘
```
