"""FFmpeg preflight probe — checks binary presence and required codecs."""
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class FFmpegPreflightResult:
    ffmpeg_found: bool = False
    ffprobe_found: bool = False
    libx264_available: bool = False
    aac_available: bool = False
    mp3_decode_available: bool = False

    def all_ok(self) -> bool:
        return all([
            self.ffmpeg_found,
            self.ffprobe_found,
            self.libx264_available,
            self.aac_available,
            self.mp3_decode_available,
        ])


class FFmpegPreflight:
    @staticmethod
    def probe() -> FFmpegPreflightResult:
        fields: dict[str, bool] = {
            "ffmpeg_found": False,
            "ffprobe_found": False,
            "libx264_available": False,
            "aac_available": False,
            "mp3_decode_available": False,
        }

        # Check ffmpeg + ffprobe existence
        for tool, attr in [("ffmpeg", "ffmpeg_found"), ("ffprobe", "ffprobe_found")]:
            try:
                subprocess.run(
                    [tool, "-version"], capture_output=True, check=True, timeout=10,
                )
                fields[attr] = True
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass

        # Check codec support via ffmpeg -codecs
        try:
            codecs = subprocess.check_output(
                ["ffmpeg", "-codecs"], stderr=subprocess.DEVNULL, timeout=10,
            ).decode()
            fields["libx264_available"] = "libx264" in codecs
            fields["aac_available"] = "aac" in codecs
            fields["mp3_decode_available"] = "mp3" in codecs
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

        return FFmpegPreflightResult(**fields)
