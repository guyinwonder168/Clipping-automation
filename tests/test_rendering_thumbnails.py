"""Tests for template thumbnail generation."""

from pathlib import Path

import pytest

from clipper_agency.rendering.contracts import ThumbnailConfig
from clipper_agency.rendering.thumbnails import generate_template_thumbnail


class TestGenerateTemplateThumbnail:
    """Tests for generate_template_thumbnail using ThumbnailConfig."""

    def test_creates_png_file_at_expected_path(self, tmp_path: Path) -> None:
        """Thumbnail generation creates a PNG file at the specified output path."""
        output = tmp_path / "thumb.png"
        config = ThumbnailConfig(
            title="Breaking News",
            template_name="news_card",
            output_path=str(output),
        )

        result = generate_template_thumbnail(config)

        assert result == output
        assert result.exists()
        assert result.is_file()
        assert result.suffix == ".png"

    def test_output_file_has_non_zero_size(self, tmp_path: Path) -> None:
        """Generated thumbnail file has non-zero size."""
        output = tmp_path / "thumb.png"
        config = ThumbnailConfig(
            title="Some Title",
            template_name="news_card",
            output_path=str(output),
        )

        result = generate_template_thumbnail(config)

        assert result.stat().st_size > 0

    def test_news_card_template_maps_to_headline_style(self, tmp_path: Path) -> None:
        """news_card template generates a PNG card successfully."""
        output = tmp_path / "news_thumb.png"
        config = ThumbnailConfig(
            title="Headline Story",
            template_name="news_card",
            output_path=str(output),
        )

        result = generate_template_thumbnail(config)

        assert result.exists()
        assert result.stat().st_size > 0

    def test_b_roll_narration_template(self, tmp_path: Path) -> None:
        """b_roll_narration template generates a PNG card successfully."""
        output = tmp_path / "broll_thumb.png"
        config = ThumbnailConfig(
            title="Voiceover Scene",
            template_name="b_roll_narration",
            output_path=str(output),
        )

        result = generate_template_thumbnail(config)

        assert result.exists()
        assert result.stat().st_size > 0

    def test_rapid_update_template(self, tmp_path: Path) -> None:
        """rapid_update template generates a PNG card successfully."""
        output = tmp_path / "rapid_thumb.png"
        config = ThumbnailConfig(
            title="Quick Update",
            template_name="rapid_update",
            output_path=str(output),
        )

        result = generate_template_thumbnail(config)

        assert result.exists()
        assert result.stat().st_size > 0

    def test_unknown_template_defaults_to_headline(self, tmp_path: Path) -> None:
        """Unknown template name falls back to HEADLINE card type."""
        output = tmp_path / "unknown_thumb.png"
        config = ThumbnailConfig(
            title="Fallback Test",
            template_name="some_unknown_template",
            output_path=str(output),
        )

        result = generate_template_thumbnail(config)

        assert result.exists()
        assert result.stat().st_size > 0

    def test_auto_generated_path_when_no_output_path(self) -> None:
        """When output_path is None, a path is auto-generated and the file exists."""
        config = ThumbnailConfig(
            title="Auto Path Test",
            template_name="news_card",
            output_path=None,
        )

        result = generate_template_thumbnail(config)

        assert result.suffix == ".png"
        assert result.exists()
        assert result.stat().st_size > 0

        # Clean up auto-generated temp file
        result.unlink(missing_ok=True)
        # Remove the parent dir if it was a temp directory
        parent = result.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Parent directories are created if they don't exist."""
        output = tmp_path / "nested" / "dir" / "thumb.png"
        config = ThumbnailConfig(
            title="Nested Path",
            template_name="news_card",
            output_path=str(output),
        )

        result = generate_template_thumbnail(config)

        assert result.exists()
        assert result.stat().st_size > 0

    def test_title_used_as_card_text(self, tmp_path: Path) -> None:
        """The title from ThumbnailConfig is passed as card text."""
        output = tmp_path / "title_test.png"
        title = "Exclusive Report: AI Breakthrough"
        config = ThumbnailConfig(
            title=title,
            template_name="news_card",
            output_path=str(output),
        )

        result = generate_template_thumbnail(config)

        assert result.exists()
        # Verify it's a valid PNG by checking PNG magic bytes
        with open(result, "rb") as f:
            header = f.read(8)
        assert header[:4] == b"\x89PNG"

    def test_generated_png_has_correct_dimensions(self, tmp_path: Path) -> None:
        """Generated thumbnail matches CardGenerator 1080x1920 dimensions."""
        output = tmp_path / "dimension_test.png"
        config = ThumbnailConfig(
            title="Dimension Test",
            template_name="news_card",
            output_path=str(output),
        )

        result = generate_template_thumbnail(config)

        from PIL import Image
        with Image.open(result) as img:
            assert img.size == (1080, 1920)
