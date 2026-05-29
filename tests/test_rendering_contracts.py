"""Tests for render contract models — CaptionOverlay, VisualOverlay, RenderScene,
ThumbnailConfig, RenderPlan, RenderResult."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from clipper_agency.rendering.contracts import (
    CaptionOverlay,
    RenderPlan,
    RenderResult,
    RenderScene,
    ThumbnailConfig,
    VisualOverlay,
)


# ---------------------------------------------------------------------------
# CaptionOverlay
# ---------------------------------------------------------------------------

def test_caption_overlay_valid():
    """Happy path: valid CaptionOverlay construction and serialization."""
    caption = CaptionOverlay(text="Halo", start_seconds=0.0, end_seconds=2.0)
    assert caption.text == "Halo"
    assert caption.start_seconds == 0.0
    assert caption.end_seconds == 2.0
    assert caption.position == "bottom"
    assert caption.style == "default"

    dumped = caption.model_dump()
    assert dumped["text"] == "Halo"
    assert dumped["start_seconds"] == 0.0
    assert dumped["end_seconds"] == 2.0


def test_caption_overlay_rejects_negative_start():
    """Negative start_seconds raises ValidationError."""
    with pytest.raises(ValidationError):
        CaptionOverlay(text="bad", start_seconds=-1.0, end_seconds=1.0)


def test_caption_overlay_rejects_end_lte_start():
    """end_seconds <= start_seconds raises ValidationError."""
    with pytest.raises(ValidationError):
        CaptionOverlay(text="bad", start_seconds=1.0, end_seconds=1.0)

    with pytest.raises(ValidationError):
        CaptionOverlay(text="bad", start_seconds=2.0, end_seconds=1.0)


# ---------------------------------------------------------------------------
# VisualOverlay
# ---------------------------------------------------------------------------


def test_visual_overlay_valid():
    """Happy path: valid VisualOverlay construction."""
    overlay = VisualOverlay(text="Breaking News")
    assert overlay.text == "Breaking News"
    assert overlay.kind == "lower_third"
    assert overlay.start_seconds == 0.0
    assert overlay.end_seconds is None


def test_visual_overlay_with_duration():
    """VisualOverlay with explicit end_seconds."""
    overlay = VisualOverlay(
        text="Breaking News", start_seconds=2.0, end_seconds=5.0
    )
    assert overlay.start_seconds == 2.0
    assert overlay.end_seconds == 5.0


def test_visual_overlay_rejects_negative_start():
    """Negative start_seconds raises ValidationError."""
    with pytest.raises(ValidationError):
        VisualOverlay(text="bad", start_seconds=-1.0)


def test_visual_overlay_rejects_end_lte_start():
    """end_seconds <= start_seconds raises ValidationError."""
    with pytest.raises(ValidationError):
        VisualOverlay(text="bad", start_seconds=2.0, end_seconds=2.0)


# ---------------------------------------------------------------------------
# RenderScene
# ---------------------------------------------------------------------------


def test_render_scene_valid():
    """Happy path: valid RenderScene construction."""
    scene = RenderScene(source_path="/tmp/scene.mp4", duration_seconds=10.0)
    assert scene.source_path == "/tmp/scene.mp4"
    assert scene.duration_seconds == 10.0
    assert scene.captions == []
    assert scene.overlays == []
    assert scene.transition == "cut"


def test_render_scene_rejects_zero_duration():
    """Zero duration_seconds raises ValidationError."""
    with pytest.raises(ValidationError):
        RenderScene(source_path="/tmp/scene.mp4", duration_seconds=0.0)


def test_render_scene_rejects_negative_duration():
    """Negative duration_seconds raises ValidationError."""
    with pytest.raises(ValidationError):
        RenderScene(source_path="/tmp/scene.mp4", duration_seconds=-5.0)


def test_render_scene_serializes_path(tmp_path):
    """RenderScene serializes source_path as a string in JSON mode."""
    scene_path = tmp_path / "scene.mp4"
    scene_path.write_text("dummy")
    scene = RenderScene(
        source_path=str(scene_path),
        duration_seconds=3.0,
        captions=[CaptionOverlay(text="Halo", start_seconds=0.0, end_seconds=1.0)],
    )
    dumped = scene.model_dump(mode="json")
    assert dumped["source_path"].endswith("scene.mp4")
    assert dumped["duration_seconds"] == 3.0
    assert len(dumped["captions"]) == 1


# ---------------------------------------------------------------------------
# ThumbnailConfig
# ---------------------------------------------------------------------------


def test_thumbnail_config_valid():
    """Happy path: valid ThumbnailConfig."""
    cfg = ThumbnailConfig(title="My Title", template_name="news_card")
    assert cfg.title == "My Title"
    assert cfg.subtitle is None
    assert cfg.template_name == "news_card"
    assert cfg.output_path is None


def test_thumbnail_config_with_optional_fields():
    """ThumbnailConfig with all fields set."""
    cfg = ThumbnailConfig(
        title="My Title",
        subtitle="A subtitle",
        template_name="news_card",
        output_path="/tmp/thumb.png",
    )
    assert cfg.subtitle == "A subtitle"
    assert cfg.output_path == "/tmp/thumb.png"


# ---------------------------------------------------------------------------
# RenderPlan
# ---------------------------------------------------------------------------


def test_render_plan_valid():
    """Happy path: valid RenderPlan with scenes."""
    scene = RenderScene(source_path="/tmp/scene.mp4", duration_seconds=5.0)
    plan = RenderPlan(template_name="news_card", scenes=[scene])
    assert plan.template_name == "news_card"
    assert len(plan.scenes) == 1
    assert plan.thumbnail is None
    assert plan.metadata == {}


def test_render_plan_with_multiple_scenes_and_thumbnail():
    """RenderPlan with multiple scenes, captions, overlays, and thumbnail."""
    scene1 = RenderScene(
        source_path="/tmp/intro.mp4",
        duration_seconds=3.0,
        captions=[
            CaptionOverlay(text="Intro", start_seconds=0.0, end_seconds=2.0),
        ],
    )
    scene2 = RenderScene(
        source_path="/tmp/main.mp4",
        duration_seconds=10.0,
        overlays=[
            VisualOverlay(text="Main Story", start_seconds=1.0, end_seconds=8.0),
        ],
    )
    thumbnail = ThumbnailConfig(
        title="News Today", template_name="news_card"
    )
    plan = RenderPlan(
        template_name="news_card",
        scenes=[scene1, scene2],
        thumbnail=thumbnail,
        metadata={"author": "clipper"},
    )
    assert len(plan.scenes) == 2
    assert plan.thumbnail.template_name == "news_card"
    assert plan.metadata == {"author": "clipper"}

    dumped = plan.model_dump(mode="json")
    assert dumped["template_name"] == "news_card"
    assert len(dumped["scenes"]) == 2
    assert dumped["thumbnail"]["title"] == "News Today"


def test_render_plan_metadata_default_is_empty_dict():
    """metadata Field default_factory=dict ensures no shared state."""
    plan1 = RenderPlan(
        template_name="test", scenes=[RenderScene(source_path="a.mp4", duration_seconds=1.0)]
    )
    plan2 = RenderPlan(
        template_name="test", scenes=[RenderScene(source_path="b.mp4", duration_seconds=1.0)]
    )
    plan1.metadata["key"] = "value"
    assert plan2.metadata == {}


# ---------------------------------------------------------------------------
# RenderResult
# ---------------------------------------------------------------------------


def test_render_result_valid():
    """Happy path: valid RenderResult."""
    result = RenderResult(
        video_path="/out/video.mp4", thumbnail_path="/out/thumb.png"
    )
    assert result.video_path == "/out/video.mp4"
    assert result.thumbnail_path == "/out/thumb.png"
    assert result.render_plan_path is None
    assert result.diagnostics_dir is None


def test_render_result_with_optional_fields():
    """RenderResult with all fields set."""
    result = RenderResult(
        video_path="/out/video.mp4",
        thumbnail_path="/out/thumb.png",
        render_plan_path="/out/plan.json",
        diagnostics_dir="/out/diag",
    )
    assert result.render_plan_path == "/out/plan.json"
    assert result.diagnostics_dir == "/out/diag"


def test_render_result_serializes_paths_as_strings(tmp_path):
    """RenderResult paths serialize as plain strings in JSON mode."""
    video = tmp_path / "video.mp4"
    thumb = tmp_path / "thumb.png"
    result = RenderResult(video_path=str(video), thumbnail_path=str(thumb))
    dumped = result.model_dump(mode="json")
    assert dumped["video_path"].endswith("video.mp4")
    assert dumped["thumbnail_path"].endswith("thumb.png")
