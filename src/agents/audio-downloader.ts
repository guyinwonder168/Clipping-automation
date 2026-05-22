import * as fs from "node:fs";
import * as path from "node:path";
import { execFileSync } from "node:child_process";
import { ResearchOutput, log } from "../state";

const SCRAPECREATORS_BASE = "https://api.scrapecreators.com";

interface TikTokMusic {
  play_url?: {
    url_list?: string[];
  };
}

interface VideoInfoResponse {
  aweme_detail?: {
    music?: TikTokMusic;
    added_sound_music_info?: TikTokMusic;
  };
}

interface AudioDownloaderDebug {
  source: "tiktok" | "youtube" | null;
  output: string | null;
  error: string | null;
  searchQuery: string | null;
}

async function fetchTikTokAudioUrl(videoUrl: string): Promise<string | null> {
  const apiKey = process.env.SCRAPECREATORS_API_KEY;
  if (!apiKey) {
    return null;
  }

  const url = new URL(`${SCRAPECREATORS_BASE}/v2/tiktok/video`);
  url.searchParams.set("url", videoUrl);

  const res = await fetch(url.toString(), {
    headers: { "x-api-key": apiKey },
  });

  if (!res.ok) {
    throw new Error(`ScrapeCreators ${res.status}: ${res.statusText}`);
  }

  const data = (await res.json()) as VideoInfoResponse;
  const music = data.aweme_detail?.added_sound_music_info ?? data.aweme_detail?.music;
  return music?.play_url?.url_list?.[0] ?? null;
}

async function downloadFile(url: string, targetPath: string): Promise<void> {
  const parsedUrl = new URL(url);
  if (parsedUrl.protocol !== "https:" && parsedUrl.protocol !== "http:") {
    throw new Error(`Invalid protocol in download URL: ${parsedUrl.protocol}`);
  }

  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Download failed ${res.status}: ${res.statusText}`);
  }

  const buffer = Buffer.from(await res.arrayBuffer());
  fs.writeFileSync(targetPath, buffer);
}

function downloadFromYouTube(searchQuery: string, targetPath: string): boolean {
  const outputTemplate = targetPath.replace(/\.mp3$/i, ".%(ext)s");

  try {
    execFileSync("yt-dlp", [
      "--extract-audio",
      "--audio-format",
      "mp3",
      "--output",
      outputTemplate,
      `ytsearch1:${searchQuery}`,
    ], {
      stdio: "ignore",
      timeout: 120_000,
    });
    return fs.existsSync(targetPath);
  } catch (err) {
    log("audio-downloader", `YouTube fallback skipped/failed: ${(err as Error).message}`);
    return false;
  }
}

function writeDebug(jobPath: string, debug: AudioDownloaderDebug): void {
  const debugDir = path.join(process.cwd(), "output", "debug");
  fs.mkdirSync(debugDir, { recursive: true });
  fs.writeFileSync(path.join(debugDir, "audio-downloader.json"), JSON.stringify(debug, null, 2));
  fs.writeFileSync(path.join(jobPath, "audio-downloader.json"), JSON.stringify(debug, null, 2));
}

export async function runAudioDownloader(
  research: ResearchOutput,
  jobPath: string,
  publicDir: string,
  slug: string
): Promise<string | null> {
  const trendingAudio = research.trending_audio;
  const publicName = `bgm-${slug}.mp3`;
  const jobAudioPath = path.join(jobPath, "bgm-trending.mp3");
  const publicAudioPath = path.join(publicDir, publicName);

  const debug: AudioDownloaderDebug = {
    source: null,
    output: null,
    error: null,
    searchQuery: trendingAudio?.search_query ?? null,
  };

  if (!trendingAudio) {
    debug.error = "No trending_audio metadata available";
    writeDebug(jobPath, debug);
    return null;
  }

  fs.mkdirSync(publicDir, { recursive: true });

  try {
      const audioUrl = await fetchTikTokAudioUrl(trendingAudio.video_url);
    if (audioUrl) {
      await downloadFile(audioUrl, jobAudioPath);
      fs.copyFileSync(jobAudioPath, publicAudioPath);
      debug.source = "tiktok";
      debug.output = publicName;
      writeDebug(jobPath, debug);
      log("audio-downloader", `Downloaded TikTok audio: ${publicName}`);
      return publicName;
    }
  } catch (err) {
    debug.error = `TikTok download failed: ${(err as Error).message}`;
    log("audio-downloader", debug.error);
  }

  if (downloadFromYouTube(trendingAudio.search_query, jobAudioPath)) {
    fs.copyFileSync(jobAudioPath, publicAudioPath);
    debug.source = "youtube";
    debug.output = publicName;
    writeDebug(jobPath, debug);
    log("audio-downloader", `Downloaded YouTube fallback audio: ${publicName}`);
    return publicName;
  }

  debug.output = null;
  debug.error = debug.error ?? "No audio source available";
  writeDebug(jobPath, debug);
  log("audio-downloader", "No trending audio downloaded; falling back to DEFAULT_BG_MUSIC");
  return null;
}
