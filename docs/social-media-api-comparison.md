# Social Media API Comparison for Clipper Agency

> **Tujuan:** Membandingkan platform social media scraping/intelligence API untuk kebutuhan trending video analysis di Clipper Agency.
> **Tanggal:** 2026-05-25

---

## Daftar Isi

1. [Ringkasan Eksekutif](#1-ringkasan-eksekutif)
2. [Platform Dibandingkan](#2-platform-dibandingkan)
3. [Perbandingan Pricing Detail](#3-perbandingan-pricing-detail)
4. [Endpoint Trending Analysis](#4-endpoint-trending-analysis)
5. [Perbandingan Fitur](#5-perbandingan-fitur)
6. [MCP & Agent Integration](#6-mcp--agent-integration)
7. [Rekomendasi Bertahap](#7-rekomendasi-bertahap)
8. [ScrapeCreators vs Semua Alternatif](#8-scrapecreators-vs-semua-alternatif)
9. [Head-to-Head: ScrapeCreators vs Alternatif](#9-head-to-head-scrapecreators-vs-alternatif)
10. [Daftar Alternatif Lengkap](#10-daftar-alternatif-lengkap)

---

## 1. Ringkasan Eksekutif

Dari riset terhadap **16+ platform** social media intelligence API, tiga kandidat terkuat untuk kebutuhan trending video analysis Clipper Agency adalah:

| Peringkat | Platform | Keunggulan Utama | Harga Mulai | Cocok Untuk |
|-----------|----------|-----------------|-------------|-------------|
| 🥇 | **TikHub** | Paling murah, 16 platform, 1000+ endpoint, dataset 1B+ | $0.001/req | Production scale, trending historis |
| 🥇 | **CreatorCrawl** | MCP native, setup 5 menit, 250 free credits | $29 (5k req) | MVP, quick start, agent-integration |
| 🥈 | **Social Fetch** | 20+ platform global, normalized schema, TypeScript SDK | $25 (10k req) | Multi-platform global, production |
| 🥉 | **ScrapeCreators** | MCP + CLI + Claude Skill, 33+ platform | $47 (25k req) | All-in-one, agent-first ecosystem |

---

## 2. Platform Dibandingkan

### 2.1 TikHub (tikhub.io)

**Deskripsi:** Platform data infrastruktur sosial media terlengkap — API, AI Gateway, datasets, dan MCP server dalam satu ekosistem.

| Aspek | Detail |
|-------|--------|
| **Website** | https://tikhub.io |
| **Platform Support** | **16+** — TikTok, Douyin, Instagram, YouTube, X/Twitter, RedNote (XHS), Bilibili, Weibo, WeChat, Lemon8, Zhihu, Reddit, LinkedIn, Kuaishou, Threads, Pinterest |
| **Total Endpoint** | 1000+ API endpoints |
| **MCP Tools** | 990+ MCP tools |
| **AI Gateway** | 75+ AI models (GPT, Claude, Gemini) |
| **Datasets** | 1B+ pre-collected records (CSV/JSON/Parquet) |
| **Free Trial** | ~50 free requests |

### 2.2 CreatorCrawl (creatorcrawl.com)

**Deskripsi:** MCP server dan API sosial media yang dibangun khusus untuk AI agents. Paling simple untuk setup.

| Aspek | Detail |
|-------|--------|
| **Website** | https://creatorcrawl.com |
| **Platform Support** | **6** — TikTok, Instagram, YouTube, LinkedIn, Twitter/X, Reddit |
| **Total Endpoint** | 58-60 endpoints |
| **MCP** | ✅ Native MCP server |
| **Free Trial** | 250 free API calls |
| **Response Time** | <5 detik |

### 2.3 Social Fetch (socialfetch.dev)

**Deskripsi:** Unified social media scraper API dengan normalized JSON schema. Paling banyak platform global.

| Aspek | Detail |
|-------|--------|
| **Website** | https://socialfetch.dev |
| **Platform Support** | **20+** — TikTok, Instagram, YouTube, X, LinkedIn, Reddit, Facebook, Google, Threads, Bluesky, Pinterest, Snapchat, Twitch, Kick, Linktree, Truth Social |
| **Total Endpoint** | 150+ API endpoints |
| **MCP** | ❌ Tidak ada (hanya REST API + TypeScript SDK) |
| **Free Trial** | 100 free credits |
| **Uptime** | 99.8% |

### 2.4 ScrapeCreators (scrapecreators.com) — Baseline

**Deskripsi:** Social media scraping API dengan ekosistem agent terlengkap (MCP + CLI + Claude Skill).

| Aspek | Detail |
|-------|--------|
| **Website** | https://scrapecreators.com |
| **Platform Support** | **33+** — TikTok, IG, YT, X, LinkedIn, FB, Reddit, Threads, Pinterest, Truth Social, Bluesky, dll |
| **Total Endpoint** | 110+ |
| **MCP** | ✅ MCP server + CLI + Claude Code Skill |
| **Free Trial** | 100 free credits |
| **Model** | Pay-as-you-go, credits never expire |

---

## 3. Perbandingan Pricing Detail

### 3.1 TikHub

| Tier | Harga | Volume Harian | $ per 1k req | Catatan |
|------|-------|--------------|-------------|---------|
| Free | $0 | ~50 req | — | Coba gratis |
| Pay-as-you-go | $0.001/req | 0 - 1.000 | **$1.00** | Volume discount otomatis |
| Volume 1k-5k | $0.0009/req | 1.000 - 5.000 | **$0.90** | -10% |
| Volume 5k-10k | $0.0008/req | 5.000 - 10.000 | **$0.80** | -20% |
| Volume 10k-20k | $0.0007/req | 10.000 - 20.000 | **$0.70** | -30% |
| Volume 20k-30k | $0.0006/req | 20.000 - 30.000 | **$0.60** | -40% |
| Volume 30k+ | $0.0005/req | 30.000+ | **$0.50** | -50% |
| Enterprise | Custom | Custom | Custom | Min $3.000 |

> **🔥 Termurah di semua platform** — volume discount otomatis setiap hari.
> Dataset pricing terpisah: $150 (100k records) - $8,000 (20M+ records).

### 3.2 CreatorCrawl

| Pack | Harga | Credits | $ per 1k req | Catatan |
|------|-------|---------|-------------|---------|
| Free | $0 | 250 | — | No credit card |
| Starter | $29 | 5.000 | **$5.80** | Paling mahal per request |
| Pro | $99 | 20.000 | **$4.95** | Most popular |
| Scale | $299 | 100.000 | **$2.99** | Best value |
| Enterprise | Custom | 1M+ | Custom | Custom pricing |

> ⚠️ **Termahal per request** — tapi paling simple setup dengan MCP native.

### 3.3 Social Fetch

| Pack | Harga | Credits | $ per 1k req | Catatan |
|------|-------|---------|-------------|---------|
| Free | $0 | 100 | — | No card required |
| Starter | $25 | 10.000 | **$2.50** | Entry level |
| Growth | $99 | 50.000 | **$1.98** | Most popular |
| Scale | $379 | 230.000 | **$1.65** | Best value |
| Business | Custom | 1M+ | Custom | Volume pricing |

### 3.4 ScrapeCreators (Baseline)

| Plan | Harga | Credits | $ per 1k req | Catatan |
|------|-------|---------|-------------|---------|
| Free | $0 | 100 | — | No card required |
| Freelance | $47 | 25.000 | **$1.88** | 33+ platform |
| Business | $497 | 500.000 | **$0.99** | Production |
| Enterprise | Custom | 1M+ | Custom | Custom pricing |

### 3.5 Summary Pricing

| Platform | Termurah/1k req | Entry Cost | Free Trial |
|----------|---------------|------------|------------|
| **TikHub** 🔥 | **$0.50** (high volume) | $0 (PAYG) | ~50 req |
| Social Fetch | $1.65 | $25 | 100 req |
| **ScrapeCreators** | $0.99 | $47 | 100 req |
| CreatorCrawl | $2.99 | $29 | 250 req |

---

## 4. Endpoint Trending Analysis

### 4.1 Trending TikTok

| Fitur | TikHub | CreatorCrawl | Social Fetch | ScrapeCreators |
|-------|--------|-------------|-------------|---------------|
| Trending Feed | ✅ | ✅ | ✅ | ✅ |
| Popular Songs/Audio | ✅ | ✅ | ❌ | ✅ |
| Popular Creators | ✅ | ✅ | ❌ | ✅ |
| Popular Hashtags | ✅ | ✅ | ❌ | ✅ |
| Trending by Region | ✅ | ❌ | ❌ | ❌ |
| Billboard/Daily Chart | ✅ (Douyin) | ❌ | ❌ | ❌ |
| Keyword Search | ✅ | ✅ | ✅ | ✅ |
| Hashtag Search | ✅ | ✅ | ✅ | ✅ |

### 4.2 Trending YouTube

| Fitur | TikHub | CreatorCrawl | Social Fetch | ScrapeCreators |
|-------|--------|-------------|-------------|---------------|
| Trending Shorts | ✅ | ✅ | ✅ | ✅ |
| Trending Videos | ✅ | ❌ | ❌ | ❌ (via search) |
| Hashtag Search | ✅ | ✅ | ✅ | ✅ |
| Keyword Search | ✅ | ✅ | ✅ | ✅ |
| Trending by Category | ✅ | ❌ | ❌ | ❌ |

### 4.3 Trending Instagram

| Fitur | TikHub | CreatorCrawl | Social Fetch | ScrapeCreators |
|-------|--------|-------------|-------------|---------------|
| Hashtag Search | ✅ | ❌ | ❌ | ✅ (via reels search) |
| Reels Search | ✅ | ❌ | ✅ | ✅ |
| Trending Audio | ✅ | ❌ | ❌ | ❌ |
| Location Search | ✅ | ❌ | ❌ | ❌ |

### 4.4 Keunikan TikHub (Platform China)

Platform China yang hanya ada di TikHub:

| Platform | Endpoint Trending | Potensi untuk Clipper |
|----------|------------------|----------------------|
| **Douyin** | Billboard API, Trending, Hot Search | Deteksi trend sebelum viral global |
| **RedNote (XHS)** | Trending topics, Hot search | Trend lifestyle & fashion |
| **Weibo** | Hot topics, Trending | Trend berita & entertainment |
| **Bilibili** | Popular, Trending | Trend video & anime culture |
| **Lemon8** | Trending topics | Trend lifestyle Asia |
| **Kuaishou** | Trending videos | Short video trend China |

---

## 5. Perbandingan Fitur

### 5.1 Platform Coverage

| Platform | TikHub | CreatorCrawl | Social Fetch | ScrapeCreators |
|----------|--------|-------------|-------------|---------------|
| TikTok | ✅ | ✅ | ✅ | ✅ |
| Instagram | ✅ | ✅ | ✅ | ✅ |
| YouTube | ✅ | ✅ | ✅ | ✅ |
| Twitter/X | ✅ | ✅ | ✅ | ✅ |
| LinkedIn | ✅ | ✅ | ✅ | ✅ |
| Reddit | ✅ | ✅ | ✅ | ✅ |
| Facebook | ❌ | ❌ | ✅ | ✅ |
| Threads | ✅ | ❌ | ✅ | ✅ |
| Pinterest | ❌ | ❌ | ✅ | ✅ |
| Bluesky | ❌ | ❌ | ✅ | ✅ |
| Snapchat | ❌ | ❌ | ✅ | ✅ |
| Twitch | ❌ | ❌ | ✅ | ✅ |
| **Douyin** | ✅ | ❌ | ❌ | ❌ |
| **RedNote/XHS** | ✅ | ❌ | ❌ | ❌ |
| **Weibo** | ✅ | ❌ | ❌ | ❌ |
| **Bilibili** | ✅ | ❌ | ❌ | ❌ |
| **Lemon8** | ✅ | ❌ | ❌ | ❌ |
| **WeChat** | ✅ | ❌ | ❌ | ❌ |
| **Zhihu** | ✅ | ❌ | ❌ | ❌ |
| **Kuaishou** | ✅ | ❌ | ❌ | ❌ |
| **Total Platform** | **16+** | **6** | **20+** | **33+** |

### 5.2 Fitur Teknis

| Fitur | TikHub | CreatorCrawl | Social Fetch | ScrapeCreators |
|-------|--------|-------------|-------------|---------------|
| REST API | ✅ | ✅ | ✅ | ✅ |
| MCP Server | ✅ (990+ tools) | ✅ (native) | ❌ | ✅ |
| CLI | ❌ | ❌ | ❌ | ✅ |
| Claude Skill | ❌ | ❌ | ❌ | ✅ |
| TypeScript SDK | ❌ | ❌ | ✅ | ❌ |
| Python SDK | ✅ | ❌ | ❌ | ❌ |
| Datasets/Historical | ✅ 1B+ | ❌ | ❌ | ❌ |
| AI Gateway | ✅ 75+ models | ❌ | ❌ | ❌ |
| Webhook | ❌ | ❌ | ❌ | ❌ |
| Live Room/Streaming | ✅ | ❌ | ❌ | ❌ |

### 5.3 Fitur Agent-Ready

| Fitur | TikHub | CreatorCrawl | Social Fetch | ScrapeCreators |
|-------|--------|-------------|-------------|---------------|
| MCP Native | ✅ | ✅ | ❌ | ✅ |
| Setup ke Claude | 3 baris config | 1 baris config | REST manual | 1 baris config |
| Natural Language Query | ✅ (via MCP) | ✅ (via MCP) | ❌ | ✅ (via Skill) |
| Auto-pagination | ❌ | ❌ | ❌ | ✅ (via CLI) |
| Agent Skill File | ❌ | ❌ | ❌ | ✅ |

---

## 6. MCP & Agent Integration

### 6.1 Setup Comparison

```json
// CreatorCrawl — 1 baris
{
  "mcpServers": {
    "creatorcrawl": {
      "url": "https://mcp.creatorcrawl.com/sse",
      "headers": { "Authorization": "Bearer YOUR_KEY" }
    }
  }
}
```

```json
// TikHub — 1 baris per platform
{
  "mcpServers": {
    "tikhub-tiktok": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.tikhub.io/tiktok/mcp",
               "--header", "Authorization: Bearer YOUR_KEY"]
    }
  }
}
```

```json
// ScrapeCreators — 1 baris
{
  "mcpServers": {
    "scrape-creators": {
      "command": "npx",
      "args": ["@scrape-creators/mcp"]
    }
  }
}
```

### 6.2 Agent Integration Matrix

| Agent | TikHub | CreatorCrawl | Social Fetch | ScrapeCreators |
|-------|--------|-------------|-------------|---------------|
| Claude Desktop | ✅ | ✅ | ❌ | ✅ |
| Claude Code | ✅ | ✅ | ❌ | ✅ |
| Cursor | ✅ | ✅ | ❌ | ✅ |
| Windsurf | ✅ | ✅ | ❌ | ✅ |
| Zed | ❌ | ✅ | ❌ | ❌ |
| Cline | ✅ | ❌ | ❌ | ❌ |
| LangChain | ✅ | ✅ | ✅ (SDK) | ✅ |
| n8n | ✅ | ✅ | ❌ | ✅ (n8n node) |
| Custom Agent | ✅ REST | ✅ REST | ✅ REST/SDK | ✅ REST/MCP/CLI |

---

## 7. Rekomendasi Bertahap

### 🚀 Fase 1: MVP (Sekarang)

**Pilihan: CreatorCrawl** atau **ScrapeCreators**

Alasan:
- Setup 5 menit (MCP native)
- 250 / 100 free credits
- Trending feed langsung bisa
- Cukup untuk validasi konsep

Estimasi biaya:
- CreatorCrawl: $0 (250 free) → $29 (5k req)
- ScrapeCreators: $0 (100 free) → $47 (25k req)

### 📈 Fase 2: Scale

**Pilihan: CreatorCrawl + TikHub**

Alasan:
- CreatorCrawl untuk real-time trending (MCP)
- TikHub untuk data historis + trending lebih murah + platform China
- TikHub datasets untuk training model trend detection

Estimasi biaya:
- CreatorCrawl: $99/bln (20k req)
- TikHub: ~$10-30/bln (10k-30k req, tergantung volume)

### 🏭 Fase 3: Production Full

**Pilihan: TikHub + ScrapeCreators**

Alasan:
- TikHub sebagai data utama (termurah per request, $0.001/req)
- ScrapeCreators sebagai backup MCP + Claude Skill
- TikHub AI Gateway untuk analisis trending lanjutan
- ScrapeCreators untuk platform yang tidak ada di TikHub

Estimasi biaya:
- TikHub: $30-200/bln (30k-200k req)
- ScrapeCreators: $47-497/bln (25k-500k req)

---

## 8. ScrapeCreators vs Semua Alternatif

### 8.1 Keunggulan ScrapeCreators

| Keunggulan | Detail |
|-----------|--------|
| **Platform terbanyak** | 33+ platform (lebih dari semua alternatif) |
| **Ekosistem Agent** | MCP + CLI + Claude Skill — tidak ada yang menandingi |
| **Pricing kompetitif** | $1.88/1k (Freelance), $0.99/1k (Business) |
| **Credit tidak expired** | Sama seperti alternatif lain |
| **No rate limit** | Unlimited concurrent requests |
| **Personal support** | Founder sendiri yang handle |

### 8.2 Kelemahan ScrapeCreators

| Kelemahan | Dibanding |
|-----------|-----------|
| **Tidak ada platform China** | Kalah dengan TikHub (Douyin, Weibo, dll) |
| **Tidak ada datasets historis** | Kalah dengan TikHub (1B+ records) |
| **Tidak ada AI Gateway** | Kalah dengan TikHub (75+ models) |
| **Harga lebih mahal dari TikHub** | TikHub $0.001/req vs ScrapeCreators $0.0019/req |
| **Free trial lebih kecil (100)** | Kalah dengan CreatorCrawl (250) |

### 8.3 Kapan Pilih ScrapeCreators

✅ **Pilih ScrapeCreators kalau:**
- Butuh platform terbanyak (33+)
- Mau MCP + CLI + Claude Skill dalam satu paket
- Harga masih masuk akal ($0.99-1.88/1k)
- Target pasar internasional (non-China)

❌ **Jangan pilih ScrapeCreators kalau:**
- Target pasar China (butuh Douyin/Weibo)
- Butuh data historis/datasets
- Mau pricing paling murah (TikHub 50% lebih murah)

---

## 9. Head-to-Head: ScrapeCreators vs Alternatif

### 9.1 ScrapeCreators vs TikHub

| Aspek | ScrapeCreators | TikHub | Pemenang |
|-------|---------------|--------|----------|
| **Platform** | 33+ (global) | 16+ (global + China) | **ScrapeCreators** (lebih banyak global) |
| **Endpoint Trending** | TikTok: trending, songs, creators, hashtags | TikTok: trending, songs, creators, hashtags, **region, billboard** + **Douyin billboard** | **TikHub** (lebih banyak trending endpoint) |
| **MCP Server** | ✅ 1 baris config | ✅ 990+ tools, 16 dedicated servers | **TikHub** (lebih banyak tools) |
| **CLI** | ✅ scrape-creators CLI | ❌ | **ScrapeCreators** |
| **Claude Skill** | ✅ First-party | ❌ | **ScrapeCreators** |
| **Datasets Historis** | ❌ | ✅ 1B+ records | **TikHub** |
| **AI Gateway** | ❌ | ✅ 75+ AI models | **TikHub** |
| **Harga/1k req** | $0.99 - $1.88 | **$0.50 - $1.00** 🔥 | **TikHub** (2x lebih murah) |
| **Platform China** | ❌ | ✅ Douyin, Weibo, Bilibili, dll | **TikHub** |
| **Free Trial** | 100 credits | ~50 req | **ScrapeCreators** |
| **SDK** | ❌ | ✅ Python SDK | **TikHub** |

**Kesimpulan:** ScrapeCreators menang di ekosistem agent (CLI + Skill) dan jumlah platform global. TikHub menang di **harga (2x lebih murah)** + **datasets historis** + **platform China** + **AI Gateway**. Kalau budget tipis dan butuh data China → TikHub. Kalau butuh agent integration lengkap → ScrapeCreators.

### 9.2 ScrapeCreators vs CreatorCrawl

| Aspek | ScrapeCreators | CreatorCrawl | Pemenang |
|-------|---------------|-------------|----------|
| **Platform** | **33+** | 6 | **ScrapeCreators** (5x lebih banyak) |
| **Endpoint Trending** | ✅ TikTok trending, songs, creators, hashtags | ✅ TikTok trending, songs, creators, hashtags + shorts YT | **Seri** |
| **MCP Server** | ✅ 1 baris config | ✅ 1 baris config, native | **Seri** |
| **CLI** | ✅ | ❌ | **ScrapeCreators** |
| **Claude Skill** | ✅ | ❌ | **ScrapeCreators** |
| **Harga/1k req** | **$0.99 - $1.88** 🔥 | $2.99 - $5.80 | **ScrapeCreators** (3x lebih murah) |
| **Free Trial** | 100 credits | **250 credits** 🔥 | **CreatorCrawl** |
| **Mudah Setup** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **CreatorCrawl** (lebih simple) |
| **Dukungan Agent** | MCP + CLI + Skill | MCP native | **ScrapeCreators** (lebih lengkap) |
| **Response Time** | ~3.12s | <5s | **ScrapeCreators** |

**Kesimpulan:** ScrapeCreators unggul **di hampir semua aspek** — platform 5x lebih banyak, harga 3x lebih murah, ekosistem agent lebih lengkap. CreatorCrawl hanya unggul di **free trial lebih besar (250)** dan **kesederhanaan setup**. Kalau mau coba cepat → CreatorCrawl. Kalau mau serius → ScrapeCreators.

### 9.3 ScrapeCreators vs Social Fetch

| Aspek | ScrapeCreators | Social Fetch | Pemenang |
|-------|---------------|-------------|----------|
| **Platform** | **33+** | 20+ | **ScrapeCreators** |
| **Endpoint Trending** | ✅ TikTok trending, songs, creators, hashtags | ✅ TikTok trending feed, YT shorts, hashtag search | **ScrapeCreators** (lebih lengkap) |
| **MCP Server** | ✅ | ❌ | **ScrapeCreators** |
| **CLI** | ✅ | ❌ | **ScrapeCreators** |
| **Claude Skill** | ✅ | ❌ | **ScrapeCreators** |
| **TypeScript SDK** | ❌ | ✅ | **Social Fetch** |
| **Harga/1k req** | **$0.99 - $1.88** | $1.65 - $2.50 | **ScrapeCreators** (lebih murah di high volume) |
| **Free Trial** | 100 | 100 | **Seri** |
| **Response Time** | ~3.12s | ~3.16s | **Seri** |
| **Normalized Schema** | ❌ (per platform beda) | ✅ (sama antar platform) | **Social Fetch** |
| **Uptime** | Tidak disebut | **99.8%** | **Social Fetch** (transparan) |

**Kesimpulan:** ScrapeCreators unggul di **ekosistem agent (MCP + CLI + Skill)**, **jumlah platform**, dan **harga high-volume**. Social Fetch unggul di **TypeScript SDK** dan **normalized schema** (lebih rapi untuk codebase). Kalau agent-first → ScrapeCreators. Kalau developer-first (SDK, schema rapi) → Social Fetch.

### 9.4 Matrix Keputusan: Pilih yang Mana?

| Situasi | Pilihan | Alasan |
|---------|---------|--------|
| **Buat MVP cepat, agent langsung jalan** | **CreatorCrawl** | Setup 5 menit, MCP native, 250 free |
| **Production dengan budget kecil** | **TikHub** | $0.001/req — termurah |
| **Butuh platform paling banyak** | **ScrapeCreators** | 33+ platform, MCP + CLI + Skill |
| **Butuh data historis / training AI** | **TikHub** | 1B+ records datasets |
| **Target pasar China / Asia** | **TikHub** | Douyin, Weibo, Bilibili, dll |
| **Developer team, pengen SDK bagus** | **Social Fetch** | TypeScript SDK, normalized schema |
| **All-in-one, agent ecosystem** | **ScrapeCreators** | MCP + CLI + Claude Skill |
| **Combined approach terbaik** | **TikHub + ScrapeCreators** | TikHub untuk data murah + trending China, ScrapeCreators untuk agent tooling + platform global |

---

## 10. Daftar Alternatif Lengkap

### Tier 1: Agent-Ready (MCP Native)

| Platform | Harga Mulai | Platform | MCP | Catatan |
|----------|-----------|----------|-----|---------|
| **ScrapeCreators** | $47 (25k req) | 33+ | ✅ | Paling lengkap |
| **TikHub** | $0.001/req | 16+ | ✅ 990+ tools | Termurah + China |
| **CreatorCrawl** | $29 (5k req) | 6 | ✅ Native | Paling simple |
| **XPOZ** | Free - $200/bln | 4 | ✅ | Social listening via MCP |

### Tier 2: Developer API (REST/SDK)

| Platform | Harga Mulai | Platform | Catatan |
|----------|-----------|----------|---------|
| **Social Fetch** | $25 (10k req) | 20+ | Normalized schema |
| **KeyAPI** | $29-699/bln | 20+ | Historical 1000 hari |
| **EnsembleData** | Custom units | 3 | Proven since 2020 |
| **ImbueData** | $25 (25k req) | 3 | $0.99/1k |

### Tier 3: Specialized / Niche

| Platform | Fokus | Harga | Catatan |
|----------|-------|-------|---------|
| **NIXUS** | Trend detection | Free - $99/bln | YT, TT, IG — khusus trending analytics |
| **Shofo** | SQL query 100M+ video | $0.0005/record | Termurah untuk big data |
| **SocialKit** | Video transcript/summary | Credits | YT, TT, IG, FB |
| **Supadata** | Video analysis API | Free tier | Extract data dari video URL |
| **Modash** | Creator raw data | Custom | IG, TT, YT |

### Tier 4: Enterprise

| Platform | Harga | Catatan |
|----------|-------|---------|
| **Infatica** | Custom | 40M proxy, ISO certified |
| **ZenAPI** | $49-499/bln | TLS fingerprint, 1000+ conc/s |
| **ScraperScoop** | $299-999/bln | Built-in sentiment analysis |

---

> **Catatan:** Dokumen ini akan diupdate seiring perubahan pricing dan fitur dari masing-masing platform.
> Review terakhir: 2026-05-25
