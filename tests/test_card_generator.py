"""Tests for generated card fallback."""
from clipper_agency.core.card_generator import CardGenerator, CardType


class TestCardGenerator:
    def test_generate_card_creates_1080x1920_png(self, tmp_path):
        gen = CardGenerator()
        output = tmp_path / "card.png"
        gen.generate(CardType.HEADLINE, "Test Title", str(output))
        assert output.exists()
        from PIL import Image

        img = Image.open(output)
        assert img.size == (1080, 1920)
        assert output.stat().st_size > 1024

    def test_all_card_types_generate_valid_images(self, tmp_path):
        gen = CardGenerator()
        for ct in CardType:
            output = tmp_path / f"card_{ct.name}.png"
            gen.generate(ct, "Sample text for " + ct.name, str(output))
            assert output.exists()
            assert output.stat().st_size > 512

    def test_long_text_truncates_and_wraps(self, tmp_path):
        gen = CardGenerator()
        output = tmp_path / "long_card.png"
        long_text = "A" * 1000
        gen.generate(CardType.FACT, long_text, str(output))
        assert output.exists()
        assert output.stat().st_size > 1024

    def test_empty_text_still_generates_valid_card(self, tmp_path):
        gen = CardGenerator()
        output = tmp_path / "empty_card.png"
        gen.generate(CardType.HEADLINE, "", str(output))
        assert output.exists()
        assert output.stat().st_size > 512

    def test_generate_overwrites_existing_file(self, tmp_path):
        gen = CardGenerator()
        output = tmp_path / "card.png"
        output.write_text("not a png")
        gen.generate(CardType.CTA, "Subscribe!", str(output))
        assert output.exists()
        from PIL import Image

        img = Image.open(output)
        assert img.size == (1080, 1920)
