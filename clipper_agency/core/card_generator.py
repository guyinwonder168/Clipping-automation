"""Generated card fallback — creates 1080x1920 PNG cards via Pillow."""
import os
from enum import Enum, auto
from PIL import Image, ImageDraw, ImageFont


class CardType(Enum):
    """Card layout variants for different context types."""
    HEADLINE = auto()
    FACT = auto()
    CONTEXT = auto()
    CTA = auto()


class CardGenerator:
    """Generates 1080x1920 PNG cards with centered wrapped text."""

    WIDTH = 1080
    HEIGHT = 1920

    # Sensible colour defaults (config overrides in Phase 15)
    BG_COLOR = (20, 20, 30)          # dark navy
    TEXT_COLOR = (255, 255, 255)     # white
    ACCENT_COLOR = (64, 180, 255)    # light blue

    def __init__(self, font_path: str | None = None) -> None:
        self._font_path = font_path

    def generate(self, card_type: CardType, text: str, output_path: str) -> None:
        """Generate a 1080x1920 PNG card with centred wrapped text."""
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Load font with fallback
        try:
            font = self._load_font(72)
        except Exception:
            font = ImageFont.load_default()

        # Truncate and wrap text
        wrapped = self._wrap_text(text, draw, font, max_width=900)

        # Calculate vertical position (centered)
        if hasattr(font, "getbbox"):
            line_height = font.getbbox("Ag")[3] + 20
        else:
            line_height = 92
        total_height = len(wrapped) * line_height
        y_start = (self.HEIGHT - total_height) // 2

        # Draw each line horizontally centered
        for i, line in enumerate(wrapped):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (self.WIDTH - text_width) // 2
            y = y_start + i * line_height
            draw.text((x, y), line, fill=self.TEXT_COLOR, font=font)

        img.save(output_path, "PNG")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Load a TrueType font or fall back to the default bitmap font."""
        candidates = [
            self._font_path,
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
        for path in candidates:
            if path and os.path.isfile(path):
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    def _wrap_text(self, text: str, draw, font, max_width: int = 900) -> list[str]:
        """Wrap text word-by-word to fit within *max_width* pixels.

        Returns a list of lines (may be empty if *text* is empty).
        """
        if not text:
            return [""]

        words = text.split()
        lines: list[str] = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines if lines else [""]
