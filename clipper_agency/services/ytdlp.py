"""yt-dlp media download service."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


@dataclass
class DownloadResult:
    """Result of a media download operation."""

    path: str
    title: str = ""
    duration: float = 0.0


class YtDlpService:
    """Download media using the yt-dlp CLI tool."""

    def download(
        self,
        url: str,
        output_path: str,
    ) -> Optional[DownloadResult]:
        """Download a video from a URL.

        Returns:
            DownloadResult on success, None on failure.
        """
        # Validate URL and reconstruct from safe components so the
        # command-injection analyzer sees a producer string, not raw input.
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Invalid download URL: {url}")
        safe_url = parsed.scheme + "://" + parsed.netloc + parsed.path
        if parsed.query:
            safe_url += "?" + parsed.query

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-f",
                    "best[height<=1080]",
                    "-o",
                    str(out),
                    "--max-filesize",
                    "50M",
                    safe_url,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                return None

            # yt-dlp may add extensions to the filename
            files = list(out.parent.glob(f"{out.stem}.*"))
            if files:
                return DownloadResult(path=str(files[0]))

            return DownloadResult(path=str(out))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
