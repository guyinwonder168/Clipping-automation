"""Tests for clipper_agency.rendering.engine — standalone FFmpeg render engine."""

import shutil
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
from clipper_agency.rendering.templates import load_render_template

ffmpeg_available = shutil.which("ffmpeg") is not None
ffmpeg_skip = pytest.mark.skipif(not ffmpeg_available, reason="FFmpeg not installed")

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


# ---------------------------------------------------------------------------
# Fixture tests — full end-to-end render per template (requires FFmpeg)
# ---------------------------------------------------------------------------


def _make_test_source(tmp_path: Path, name: str, color: str = "blue") -> Path:
    """Generate a 1‑second 1080×1920 synthetic MP4 clip under *tmp_path*."""
    source = tmp_path / name
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={color}:s=1080x1920:d=1",
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(source),
        ],
        check=True, capture_output=True, text=True,
    )
    return source


@ffmpeg_skip
def test_standalone_renderer_news_card(tmp_path):
    """Full render: news_card adapter → engine → valid video + thumbnail."""
    source = _make_test_source(tmp_path, "src_news.mp4")

    template = load_render_template("news_card")
    from clipper_agency.rendering.renderers.news_card import build_news_card_plan

    output = tmp_path / "outputs" / "video.mp4"
    diagnostics = tmp_path / "diagnostics"
    plan = build_news_card_plan(
        template=template,
        source_paths=[source],
        caption="Breaking news hari ini dari dunia hiburan",
        title="News Card Test",
        diagnostics_dir=diagnostics,
    )

    result = render_plan(plan, output, diagnostics)
    assert result.video_path == str(output)
    assert output.is_file()
    assert output.stat().st_size > 0

    thumbnail = Path(result.thumbnail_path)
    assert thumbnail.is_file()
    assert thumbnail.stat().st_size > 0

    # Probe output
    from clipper_agency.core.media_probe import probe_video

    info = probe_video(output, output.parent)
    assert info is not None
    assert info.width == 1080
    assert info.height == 1920
    assert info.duration is not None

    # Diagnostics
    assert (diagnostics / "render_plan.json").is_file()
    assert (diagnostics / "ffmpeg_command.txt").is_file()


@ffmpeg_skip
def test_standalone_renderer_b_roll_narration(tmp_path):
    """Full render: b_roll_narration adapter → engine → valid video + thumbnail."""
    src1 = _make_test_source(tmp_path, "src_brn_clip1.mp4", "green")
    src2 = _make_test_source(tmp_path, "src_brn_clip2.mp4", "red")

    template = load_render_template("b_roll_narration")
    from clipper_agency.rendering.renderers.b_roll_narration import (
        build_b_roll_narration_plan,
    )

    output = tmp_path / "outputs" / "video.mp4"
    diagnostics = tmp_path / "diagnostics"
    plan = build_b_roll_narration_plan(
        template=template,
        source_paths=[src1, src2],
        caption="Cerita panjang untuk dua klip b roll",
        title="B-Roll Narration Test",
        diagnostics_dir=diagnostics,
    )

    result = render_plan(plan, output, diagnostics)
    assert result.video_path == str(output)
    assert output.is_file()
    assert output.stat().st_size > 0

    from clipper_agency.core.media_probe import probe_video

    info = probe_video(output, output.parent)
    assert info is not None
    assert info.width == 1080
    assert info.height == 1920


@ffmpeg_skip
def test_standalone_renderer_rapid_update(tmp_path):
    """Full render: rapid_update adapter → engine → valid video + thumbnail."""
    source = _make_test_source(tmp_path, "src_rapid.mp4", "black")

    template = load_render_template("rapid_update")
    from clipper_agency.rendering.renderers.rapid_update import build_rapid_update_plan

    output = tmp_path / "outputs" / "video.mp4"
    diagnostics = tmp_path / "diagnostics"
    plan = build_rapid_update_plan(
        template=template,
        source_paths=[source],
        caption="Gosip terbaru artis indonesia hot banget",
        title="Rapid Update Test",
        diagnostics_dir=diagnostics,
    )

    result = render_plan(plan, output, diagnostics)
    assert result.video_path == str(output)
    assert output.is_file()
    assert output.stat().st_size > 0

    from clipper_agency.core.media_probe import probe_video

    info = probe_video(output, output.parent)
    assert info is not None
    assert info.width == 1080
    assert info.height == 1920

    # Rapid Update should have drawtext captions in filter
    cmd_text = (diagnostics / "ffmpeg_command.txt").read_text()
    assert "drawtext" in cmd_text


# ---------------------------------------------------------------------------
# Regression tests for Codex review fixes
# ---------------------------------------------------------------------------


def test_drawtext_center_position():
    """Fix 3: center-position captions should use y=(h-th)/2 (not bottom)."""
    overlay = CaptionOverlay(
        text="Punchy Text",
        start_seconds=0.0,
        end_seconds=2.5,
        position="center",
    )
    result = _build_drawtext(overlay)
    assert "y=(h-th)/2" in result
    assert "y=h-th-20" not in result


def test_input_t_trimming_flag(tmp_path):
    """Fix 2: each input should be preceded by -t <duration>."""
    src1 = tmp_path / "a.mp4"
    src2 = tmp_path / "b.mp4"
    src1.write_text("dummy")
    src2.write_text("dummy")

    plan = RenderPlan(
        template_name="news_card",
        scenes=[
            RenderScene(source_path=str(src1), duration_seconds=5.0,
                        transition="fade", transition_duration_seconds=0.5),
            RenderScene(source_path=str(src2), duration_seconds=3.0,
                        transition="fade", transition_duration_seconds=0.5),
        ],
    )
    args = _build_ffmpeg_args(plan, tmp_path / "out.mp4")

    # Find the -t flags for each input
    t_flags = []
    for i, a in enumerate(args):
        if a == "-t":
            t_flags.append(float(args[i + 1]))
    assert t_flags == [5.0, 3.0], f"Expected -t 5.0 and -t 3.0, got {t_flags}"


def test_caption_offset_multi_scene(tmp_path):
    """Fix 1: multi-scene captions should be offset by prior scene durations."""
    src1 = tmp_path / "first.mp4"
    src2 = tmp_path / "second.mp4"
    src1.write_text("dummy")
    src2.write_text("dummy")

    plan = RenderPlan(
        template_name="b_roll_narration",
        scenes=[
            RenderScene(
                source_path=str(src1), duration_seconds=5.0,
                captions=[CaptionOverlay(text="Intro", start_seconds=0.0, end_seconds=5.0)],
                transition="crossfade", transition_duration_seconds=0.3,
            ),
            RenderScene(
                source_path=str(src2), duration_seconds=5.0,
                captions=[CaptionOverlay(text="Body", start_seconds=0.0, end_seconds=5.0)],
                transition="crossfade", transition_duration_seconds=0.3,
            ),
        ],
    )
    args = _build_ffmpeg_args(plan, tmp_path / "out.mp4")
    filter_part = [a for a in args if "drawtext" in a]

    # Scene 0 caption at offset 0
    assert any("between(t,0.0,5.0)" in f for f in filter_part), \
        f"Scene 0 caption should be at 0-5s, got: {filter_part}"
    # Scene 1 caption offset = d0 - xfade_dur = 5.0 - 0.3 = 4.7
    assert any("between(t,4.7,9.7)" in f for f in filter_part), \
        f"Scene 1 caption should be at 4.7-9.7s, got: {filter_part}"


def test_fade_transition_filter_chain(tmp_path):
    """Fix 4: fade transition should produce per-scene fade filters + concat."""
    src1 = tmp_path / "a.mp4"
    src2 = tmp_path / "b.mp4"
    src1.write_text("dummy")
    src2.write_text("dummy")

    plan = RenderPlan(
        template_name="news_card",
        scenes=[
            RenderScene(source_path=str(src1), duration_seconds=5.0,
                        transition="fade", transition_duration_seconds=0.5),
            RenderScene(source_path=str(src2), duration_seconds=5.0,
                        transition="fade", transition_duration_seconds=0.5),
        ],
    )
    args = _build_ffmpeg_args(plan, tmp_path / "out.mp4")
    filter_part = [a for a in args if "filter_complex" in a or "fade" in a or "concat" in a]

    # Should contain fade=t=in:st=0:d=0.5 AND fade=t=out per scene
    filter_str = ";".join(filter_part)
    assert "fade=t=in:st=0:d=0.5" in filter_str, \
        f"Missing fade-in in filter: {filter_str}"
    assert "fade=t=out:st=4.5:d=0.5" in filter_str, \
        f"Missing fade-out in filter: {filter_str}"
    # Should still have concat after fade
    assert "concat" in filter_str, \
        f"Missing concat in filter: {filter_str}"


def test_xfade_transition_filter_chain(tmp_path):
    """Fix 4: crossfade should produce xfade chain (not plain concat)."""
    src1 = tmp_path / "a.mp4"
    src2 = tmp_path / "b.mp4"
    src1.write_text("dummy")
    src2.write_text("dummy")

    plan = RenderPlan(
        template_name="b_roll_narration",
        scenes=[
            RenderScene(source_path=str(src1), duration_seconds=5.0,
                        transition="crossfade", transition_duration_seconds=0.3),
            RenderScene(source_path=str(src2), duration_seconds=5.0,
                        transition="crossfade", transition_duration_seconds=0.3),
        ],
    )
    args = _build_ffmpeg_args(plan, tmp_path / "out.mp4")
    filter_part = [a for a in args if "filter_complex" in a or "xfade" in a or "concat" in a]
    filter_str = ";".join(filter_part)

    # Must use xfade, NOT concat
    assert "xfade=" in filter_str, \
        f"Missing xfade in filter (expected xfade chain, not concat): {filter_str}"
    assert "concat" not in filter_str, \
        f"concat should NOT appear in xfade filter: {filter_str}"
    # Check xfade parameters
    assert "duration=0.3" in filter_str
    assert "offset=4.7" in filter_str  # d0 - xfade_dur = 5.0 - 0.3
    # Should have settb=AVTB normalisation
    assert "settb=AVTB" in filter_str
