"""yt-dlp media download service."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                return None

            # yt-dlp may add extensions to the filename
            files = list(out.parent.glob(f"{out.stem}*"))
            if files:
                return DownloadResult(path=str(files[0]))

            return DownloadResult(path=str(out))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
