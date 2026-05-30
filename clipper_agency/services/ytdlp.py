"""yt-dlp media download service."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


UNSAFE_URL_CHARS = re.compile(r"[\x00-\x20\x7f]")


@dataclass
class DownloadResult:
    """Result of a media download operation."""

    path: str
    title: str = ""
    duration: float = 0.0


class YtDlpService:
    """Download media using the yt-dlp CLI tool."""

    def _validated_url(self, url: str) -> str:
        """Return a normalized URL safe to pass as a yt-dlp operand."""
        if UNSAFE_URL_CHARS.search(url):
            raise ValueError(f"Invalid download URL: {url}")

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.fragment:
            raise ValueError(f"Invalid download URL: {url}")

        safe_url = parsed.scheme + "://" + parsed.netloc + parsed.path
        if parsed.query:
            safe_url += "?" + parsed.query
        return safe_url

    def download(
        self,
        url: str,
        output_path: str,
    ) -> Optional[DownloadResult]:
        """Download a video from a URL.

        Returns:
            DownloadResult on success, None on failure.
        """
        safe_url = self._validated_url(url)

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
                    "--",
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
