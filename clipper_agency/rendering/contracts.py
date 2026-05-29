"""Render contract models — Pydantic schemas for rendering pipeline input/output."""

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class CaptionOverlay(BaseModel):
    """A text caption rendered onto a scene at a specific time range.

    Args:
        text: Caption content (plain text).
        start_seconds: Time offset (inclusive) when the caption appears.
        end_seconds: Time offset (exclusive) when the caption disappears.
        position: Screen placement (e.g. ``"bottom"``, ``"top"``).
        style: Named style key for rendering (e.g. ``"default"``).
    """

    text: str
    start_seconds: float = Field(ge=0)
    end_seconds: float
    position: str = "bottom"
    style: str = "default"

    @model_validator(mode="after")
    def _end_after_start(self) -> "CaptionOverlay":
        if self.end_seconds <= self.start_seconds:
            raise ValueError(
                f"end_seconds ({self.end_seconds}) must be > "
                f"start_seconds ({self.start_seconds})"
            )
        return self


class VisualOverlay(BaseModel):
    """A visual overlay (lower-third, banner, etc.) rendered onto a scene.

    Args:
        text: Overlay text content.
        kind: Overlay type — ``"lower_third"``, ``"banner"``, etc.
        start_seconds: Time offset when the overlay appears (default 0.0).
        end_seconds: Time offset when the overlay disappears (None = scene end).
    """

    text: str
    kind: str = "lower_third"
    start_seconds: float = Field(default=0.0, ge=0)
    end_seconds: Optional[float] = None

    @model_validator(mode="after")
    def _end_after_start(self) -> "VisualOverlay":
        if self.end_seconds is not None and self.end_seconds <= self.start_seconds:
            raise ValueError(
                f"end_seconds ({self.end_seconds}) must be > "
                f"start_seconds ({self.start_seconds})"
            )
        return self


class RenderScene(BaseModel):
    """A single scene within a render plan.

    Args:
        source_path: Path to the source media file for this scene.
        duration_seconds: How long this scene plays (must be > 0).
        captions: List of caption overlays (default empty).
        overlays: List of visual overlays (default empty).
        transition: Named transition into the next scene (default ``"cut"``).
    """

    source_path: str
    duration_seconds: float = Field(gt=0)
    captions: list[CaptionOverlay] = Field(default_factory=list)
    overlays: list[VisualOverlay] = Field(default_factory=list)
    transition: str = "cut"


class ThumbnailConfig(BaseModel):
    """Configuration for a generated thumbnail image.

    Args:
        title: Primary text on the thumbnail.
        subtitle: Secondary text (optional).
        template_name: Which thumbnail template to render.
        output_path: Custom output path for the thumbnail file (optional).
    """

    title: str
    subtitle: Optional[str] = None
    template_name: str
    output_path: Optional[str] = None


class RenderPlan(BaseModel):
    """Complete render plan consumed by the rendering engine.

    Args:
        template_name: Name of the rendering template to apply.
        scenes: Ordered list of scenes to compose.
        thumbnail: Optional thumbnail configuration.
        metadata: Arbitrary key-value metadata attached to the render job.
    """

    template_name: str
    scenes: list[RenderScene]
    thumbnail: Optional[ThumbnailConfig] = None
    metadata: dict = Field(default_factory=dict)


class RenderResult(BaseModel):
    """Output of a completed render job.

    Args:
        video_path: Path to the rendered video file.
        thumbnail_path: Path to the generated thumbnail image.
        render_plan_path: Path to the serialized render plan used (optional).
        diagnostics_dir: Path to diagnostics/output folder (optional).
    """

    video_path: str
    thumbnail_path: str
    render_plan_path: Optional[str] = None
    diagnostics_dir: Optional[str] = None
