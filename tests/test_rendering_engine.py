"""Tests for clipper_agency.rendering.engine — standalone FFmpeg render engine."""

import subprocess
from pathlib import Path

import pytest

from clipper_agency.rendering.contracts import (
    CaptionOverlay,
    RenderPlan,
    RenderResult,
    RenderScene,
    ThumbnailConfig,
)
from clipper_agency.rendering.engine import (
    TemplateRenderError,
    _build_drawtext,
    _build_ffmpeg_args,
    render_plan,
)

# ---------------------------------------------------------------------------
# _build_drawtext
# ---------------------------------------------------------------------------


def test_build_drawtext_centers_bottom_by_default():
    """Verify drawtext output contains centered x and bottom y positioning."""
    overlay = CaptionOverlay(
        text="Hello World",
        start_seconds=0.0,
        end_seconds=5.0,
        position="bottom",
    )
    result = _build_drawtext(overlay)

    assert "x=(w-text_w)/2" in result
    assert "y=h-th-20" in result
    assert "fontsize=32" in result
    assert "fontcolor=white" in result
    assert "enable='between(t,0.0,5.0)'" in result
    assert "Hello World" in result


def test_build_drawtext_escapes_colon():
    """Verify colon in caption text is escaped via escape_drawtext."""
    overlay = CaptionOverlay(
        text="Time: 3:00 PM",
        start_seconds=0.0,
        end_seconds=3.0,
    )
    result = _build_drawtext(overlay)

    assert r"\:" in result
    assert "Time" in result
    # Original colon should be escaped, not raw
    assert "Time: 3" not in result or ":" not in result.replace(r"\:", "")


def test_build_drawtext_top_position():
    """Verify top position uses y=20."""
    overlay = CaptionOverlay(
        text="Top text",
        start_seconds=0.0,
        end_seconds=1.0,
        position="top",
    )
    result = _build_drawtext(overlay)

    assert "y=20" in result


# ---------------------------------------------------------------------------
# _build_ffmpeg_args
# ---------------------------------------------------------------------------


def test_build_ffmpeg_args_single_scene_no_captions(tmp_path):
    """Single scene with no captions should produce concat + anullsrc + encoding."""
    source = tmp_path / "scene.mp4"
    source.write_text("dummy")

    plan = RenderPlan(
        template_name="news_card",
        scenes=[
            RenderScene(
                source_path=str(source),
                duration_seconds=5.0,
                captions=[],
            ),
        ],
    )
    output = tmp_path / "output.mp4"
    args = _build_ffmpeg_args(plan, output)

    assert args[0] == "ffmpeg"
    assert "-y" in args
    assert str(source) in args

    # concat filter should be present (1 scene = still needs concat)
    filter_strs = [a for a in args if "concat" in a]
    assert len(filter_strs) >= 1

    # anullsrc
    assert any("anullsrc" in a for a in args)

    # encoding
    assert any("libx264" in a for a in args)
    assert any("aac" in a for a in args)
    assert str(output) in args

    # No drawtext since no captions
    assert not any("drawtext" in a for a in args)


def test_build_ffmpeg_args_single_scene_with_caption(tmp_path):
    """Single scene with a caption should include drawtext chain."""
    source = tmp_path / "scene.mp4"
    source.write_text("dummy")

    plan = RenderPlan(
        template_name="news_card",
        scenes=[
            RenderScene(
                source_path=str(source),
                duration_seconds=5.0,
                captions=[
                    CaptionOverlay(
                        text="Breaking News",
                        start_seconds=0.0,
                        end_seconds=5.0,
                    ),
                ],
            ),
        ],
    )
    output = tmp_path / "output.mp4"
    args = _build_ffmpeg_args(plan, output)

    assert any("drawtext" in a for a in args)


def test_build_ffmpeg_args_multi_scene_no_captions(tmp_path):
    """Two scenes with no captions: verify concat for 2 sources, no drawtext."""
    src1 = tmp_path / "scene1.mp4"
    src1.write_text("dummy")
    src2 = tmp_path / "scene2.mp4"
    src2.write_text("dummy")

    plan = RenderPlan(
        template_name="rapid_update",
        scenes=[
            RenderScene(source_path=str(src1), duration_seconds=3.0),
            RenderScene(source_path=str(src2), duration_seconds=4.0),
        ],
    )
    output = tmp_path / "output.mp4"
    args = _build_ffmpeg_args(plan, output)

    # concat for 2 videos
    filter_strs = [a for a in args if "concat" in a]
    assert len(filter_strs) >= 1
    # n=2
    assert any("n=2" in a for a in filter_strs)

    # no drawtext
    assert not any("drawtext" in a for a in args)

    # anullsrc
    assert any("anullsrc" in a for a in args)


# ---------------------------------------------------------------------------
# render_plan
# ---------------------------------------------------------------------------


def test_render_plan_persists_diagnostics_and_runs_ffmpeg(tmp_path, monkeypatch):
    """Mock FFmpeg + probe, verify diagnostics written and RenderResult correct."""
    # Create a fake source file
    source = tmp_path / "scene.mp4"
    source.write_text("fake video content")

    output_path = tmp_path / "render" / "output.mp4"
    diagnostics_dir = tmp_path / "render" / "diagnostics"

    plan = RenderPlan(
        template_name="news_card",
        scenes=[
            RenderScene(
                source_path=str(source),
                duration_seconds=5.0,
                captions=[
                    CaptionOverlay(
                        text="Hello",
                        start_seconds=0.0,
                        end_seconds=5.0,
                    ),
                ],
            ),
        ],
        thumbnail=ThumbnailConfig(
            title="Test Thumb",
            template_name="news_card",
            output_path=str(tmp_path / "thumb.png"),
        ),
    )

    # --- Mock subprocess.run ---
    run_calls = []

    def fake_run(cmd, check=False, capture_output=False, text=False, **kwargs):
        run_calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    # --- Mock probe_video ---
    from clipper_agency.rendering import engine as eng_mod

    probe_calls = []

    def fake_probe(path, allowed_base_dir):
        probe_calls.append((str(path), str(allowed_base_dir)))
        from clipper_agency.core.media_probe import VideoInfo

        return VideoInfo(
            path=str(path),
            width=1080,
            height=1920,
            codec="h264",
            pix_fmt="yuv420p",
            duration=5.0,
            has_audio=True,
            file_size=1024,
        )

    monkeypatch.setattr(eng_mod, "probe_video", fake_probe)

    # --- Mock generate_template_thumbnail ---
    thumb_calls = []

    def fake_thumb(config):
        thumb_calls.append(config)
        return Path(str(tmp_path / "thumb.png"))

    monkeypatch.setattr(eng_mod, "generate_template_thumbnail", fake_thumb)

    # --- Execute ---
    result = render_plan(plan, output_path, diagnostics_dir)

    # --- Assertions ---
    assert isinstance(result, RenderResult)
    assert result.video_path == str(output_path)
    assert result.thumbnail_path == str(tmp_path / "thumb.png")
    assert result.render_plan_path == str(diagnostics_dir / "render_plan.json")
    assert result.diagnostics_dir == str(diagnostics_dir)

    # Diagnostics files written
    assert (diagnostics_dir / "render_plan.json").exists()
    assert (diagnostics_dir / "ffmpeg_command.txt").exists()

    # FFmpeg was called
    assert len(run_calls) == 1
    ffmpeg_cmd = run_calls[0]
    assert ffmpeg_cmd[0] == "ffmpeg"

    # probe_video was called
    assert len(probe_calls) == 1

    # thumbnail was generated
    assert len(thumb_calls) == 1


def test_render_plan_raises_on_ffmpeg_failure(tmp_path, monkeypatch):
    """FFmpeg CalledProcessError → TemplateRenderError raised + stderr logged."""
    source = tmp_path / "scene.mp4"
    source.write_text("fake")

    output_path = tmp_path / "render" / "output.mp4"
    diagnostics_dir = tmp_path / "render" / "diagnostics"

    plan = RenderPlan(
        template_name="news_card",
        scenes=[
            RenderScene(
                source_path=str(source),
                duration_seconds=5.0,
            ),
        ],
    )

    def fake_run(cmd, check=False, capture_output=False, text=False, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            stderr="FFmpeg error: invalid argument",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(TemplateRenderError):
        render_plan(plan, output_path, diagnostics_dir)

    # ffmpeg_stderr.log should be written
    stderr_log = diagnostics_dir / "ffmpeg_stderr.log"
    assert stderr_log.exists()
    content = stderr_log.read_text()
    assert "FFmpeg error" in content
