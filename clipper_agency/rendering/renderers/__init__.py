"""Per-template render adapters — pure plan builders, no FFmpeg I/O."""

from __future__ import annotations

from clipper_agency.rendering.renderers.rapid_update import build_rapid_update_plan

__all__ = ["build_rapid_update_plan"]
