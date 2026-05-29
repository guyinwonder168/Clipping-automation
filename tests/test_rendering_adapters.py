"""Tests for rendering template adapters — pure plan builder verification."""

from pathlib import Path

import pytest

from clipper_agency.rendering.renderers.news_card import build_news_card_plan
from clipper_agency.rendering.templates import load_render_template


class TestNewsCardAdapter:
    """Verify build_news_card_plan produces a valid RenderPlan."""

    def test_news_card_adapter_builds_headline_plan(self, tmp_path: Path):
        """Build a RenderPlan from a single source with caption+title+thumbnail."""
        template = load_render_template("news_card", Path("templates"))
        source = tmp_path / "source.mp4"
        source.write_bytes(b"placeholder")

        plan = build_news_card_plan(
            template=template,
            source_paths=[source],
            caption="Breaking: artis rilis kabar baru",
            title="Breaking News",
            diagnostics_dir=tmp_path,
        )

        assert plan.template_name == "news_card"
        assert len(plan.scenes) == 1
        assert plan.scenes[0].source_path == str(source)
        assert plan.scenes[0].captions, "scene must have captions"
        assert "Breaking" in plan.scenes[0].captions[0].text
        assert plan.thumbnail is not None
        assert plan.thumbnail.title == "Breaking News"
        assert plan.thumbnail.output_path is not None
        assert plan.thumbnail.output_path.endswith("news_card.png")

    def test_news_card_adapter_handles_multiple_sources(self, tmp_path: Path):
        """Multiple source_paths produce multiple scenes with captions."""
        template = load_render_template("news_card", Path("templates"))
        sources = []
        for i in range(3):
            src = tmp_path / f"clip_{i}.mp4"
            src.write_bytes(b"placeholder")
            sources.append(src)

        plan = build_news_card_plan(
            template=template,
            source_paths=sources,
            caption="Multi source update",
            title="Multi Test",
            diagnostics_dir=tmp_path,
        )

        assert plan.template_name == "news_card"
        assert len(plan.scenes) == 3
        for i, scene in enumerate(plan.scenes):
            assert scene.source_path == str(sources[i])
            assert scene.captions, f"scene {i} must have captions"
            assert scene.duration_seconds > 0

    def test_news_card_adapter_uses_template_transition(self, tmp_path: Path):
        """Each scene transition matches the template's configured transition."""
        template = load_render_template("news_card", Path("templates"))
        source = tmp_path / "source.mp4"
        source.write_bytes(b"placeholder")

        plan = build_news_card_plan(
            template=template,
            source_paths=[source],
            caption="Test",
            title="Test",
            diagnostics_dir=tmp_path,
        )

        for scene in plan.scenes:
            assert scene.transition == template.transitions.type

    def test_news_card_adapter_thumbnail_path_in_diagnostics(self, tmp_path: Path):
        """Thumbnail output_path lives under diagnostics_dir/thumbnails/."""
        template = load_render_template("news_card", Path("templates"))
        source = tmp_path / "source.mp4"
        source.write_bytes(b"placeholder")

        plan = build_news_card_plan(
            template=template,
            source_paths=[source],
            caption="Test",
            title="Test Title",
            diagnostics_dir=tmp_path,
        )

        expected_subpath = str(tmp_path / "thumbnails" / "news_card.png")
        assert plan.thumbnail is not None
        assert plan.thumbnail.output_path == expected_subpath


class TestBRollNarrationAdapter:
    """Verify build_b_roll_narration_plan produces a valid RenderPlan."""

    def test_b_roll_narration_adapter_uses_multiple_clips(self, tmp_path: Path):
        """Multiple source_paths produce one scene each with crossfade transitions."""
        from clipper_agency.rendering.renderers.b_roll_narration import (
            build_b_roll_narration_plan,
        )

        sources = [tmp_path / f"clip_{i}.mp4" for i in range(3)]
        for src in sources:
            src.write_bytes(b"placeholder")

        template = load_render_template("b_roll_narration", Path("templates"))
        plan = build_b_roll_narration_plan(
            template=template,
            source_paths=sources,
            caption="narasi panjang untuk dua klip",
            title="Konteks",
            diagnostics_dir=tmp_path,
        )

        assert plan.template_name == "b_roll_narration"
        assert len(plan.scenes) == 3
        for scene in plan.scenes:
            assert scene.transition == template.transitions.type
            assert scene.captions, "scene must have captions"
            for caption in scene.captions:
                assert caption.style == "dynamic"

    def test_b_roll_narration_adapter_splits_captions_across_scenes(
        self, tmp_path: Path
    ):
        """Long caption text is split deterministically across scenes."""
        from clipper_agency.rendering.renderers.b_roll_narration import (
            build_b_roll_narration_plan,
        )

        source = tmp_path / "source.mp4"
        source.write_bytes(b"placeholder")

        template = load_render_template("b_roll_narration", Path("templates"))
        plan = build_b_roll_narration_plan(
            template=template,
            source_paths=[source],
            caption="narasi panjang untuk dua klip",
            title="Test",
            diagnostics_dir=tmp_path,
        )

        assert len(plan.scenes) == 1
        captions = plan.scenes[0].captions
        assert captions, "must have captions"
        # Words should be grouped (6 words, default wpg produces at least 1 group)
        assert len(captions) >= 1

    def test_b_roll_narration_adapter_thumbnail(self, tmp_path: Path):
        """Thumbnail is created under diagnostics_dir/thumbnails/b_roll_narration.png."""
        from clipper_agency.rendering.renderers.b_roll_narration import (
            build_b_roll_narration_plan,
        )

        source = tmp_path / "source.mp4"
        source.write_bytes(b"placeholder")

        template = load_render_template("b_roll_narration", Path("templates"))
        plan = build_b_roll_narration_plan(
            template=template,
            source_paths=[source],
            caption="Test",
            title="Test Title",
            diagnostics_dir=tmp_path,
        )

        assert plan.thumbnail is not None
        assert plan.thumbnail.title == "Test Title"
        assert plan.thumbnail.template_name == "b_roll_narration"
        assert plan.thumbnail.output_path is not None
        assert plan.thumbnail.output_path.endswith("b_roll_narration.png")


class TestRapidUpdateAdapter:
    """Verify build_rapid_update_plan produces a valid RenderPlan."""

    def test_rapid_update_adapter_uses_punchy_centered_captions(
        self, tmp_path: Path
    ):
        """All captions use position=center and transition=cut."""
        from clipper_agency.rendering.renderers.rapid_update import (
            build_rapid_update_plan,
        )

        source = tmp_path / "rapid.mp4"
        source.write_bytes(b"placeholder")

        template = load_render_template("rapid_update", Path("templates"))
        plan = build_rapid_update_plan(
            template=template,
            source_paths=[source],
            caption="viral sekarang cek faktanya",
            title="Viral",
            diagnostics_dir=tmp_path,
        )

        assert plan.template_name == "rapid_update"
        assert plan.scenes[0].transition == template.transitions.type
        assert plan.scenes[0].captions, "must have captions"
        for caption in plan.scenes[0].captions:
            assert caption.position == "center"
            assert caption.style == "punchy_centered"

    def test_rapid_update_adapter_short_caption_groups(self, tmp_path: Path):
        """Rapid Update uses short (2-3 word) caption groups for punchy feel."""
        from clipper_agency.rendering.renderers.rapid_update import (
            build_rapid_update_plan,
        )

        source = tmp_path / "rapid.mp4"
        source.write_bytes(b"placeholder")

        template = load_render_template("rapid_update", Path("templates"))
        plan = build_rapid_update_plan(
            template=template,
            source_paths=[source],
            caption="viral sekarang cek faktanya update terbaru",
            title="Trending",
            diagnostics_dir=tmp_path,
        )

        assert len(plan.scenes) == 1
        captions = plan.scenes[0].captions
        assert captions, "must have captions"
        # 6 words with words_per_caption=2 → 3 groups
        assert len(captions) >= 3

    def test_rapid_update_adapter_thumbnail(self, tmp_path: Path):
        """Thumbnail under diagnostics_dir/thumbnails/rapid_update.png."""
        from clipper_agency.rendering.renderers.rapid_update import (
            build_rapid_update_plan,
        )

        source = tmp_path / "rapid.mp4"
        source.write_bytes(b"placeholder")

        template = load_render_template("rapid_update", Path("templates"))
        plan = build_rapid_update_plan(
            template=template,
            source_paths=[source],
            caption="Test",
            title="Test Title",
            diagnostics_dir=tmp_path,
        )

        assert plan.thumbnail is not None
        assert plan.thumbnail.title == "Test Title"
        assert plan.thumbnail.template_name == "rapid_update"
        assert plan.thumbnail.output_path is not None
        assert plan.thumbnail.output_path.endswith("rapid_update.png")
