"""Pipeline gates (G1-G10) — validation checkpoints for job processing."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GateResult:
    """Result of a gate evaluation."""
    passed: bool
    severity: str  # "pass" | "soft_fail" | "hard_fail"
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class BaseGate:
    """Base class for pipeline gates."""

    def evaluate(self, **kwargs: Any) -> GateResult:
        raise NotImplementedError


# ════════════════════════════════════════════════════════════════════
# G1: Input Preflight — validate topic before any processing
# ════════════════════════════════════════════════════════════════════

class GateInputPreflight(BaseGate):
    """G1: Validate topic input before any processing."""

    def evaluate(self, topic: str = "", niche_config: dict | None = None,
                 source_url: str | None = None, **kwargs) -> GateResult:
        if not topic or not topic.strip():
            return GateResult(False, "hard_fail", "Topic cannot be empty")
        if niche_config is None:
            return GateResult(False, "hard_fail", "Niche config required")
        return GateResult(True, "pass", "Input valid",
                          data={"topic": topic.strip()})


# ════════════════════════════════════════════════════════════════════
# G2: Cost Estimate — lightweight credit/cost estimate
# ════════════════════════════════════════════════════════════════════

class GateCostEstimate(BaseGate):
    """G2: Lightweight cost + credit estimate."""

    BASE_COST_CENTS = 3.3  # Budget East total in cents

    def evaluate(self, cached: bool = False,
                 niche_config: dict | None = None, **kwargs) -> GateResult:
        estimated_cents = (
            self.BASE_COST_CENTS if not cached
            else self.BASE_COST_CENTS * 0.7
        )
        return GateResult(
            True, "pass",
            f"Est. cost: ${estimated_cents/100:.4f}",
            data={"estimate_cents": estimated_cents},
        )


# ════════════════════════════════════════════════════════════════════
# G3: Research Cache — check cache TTL / freshness
# ════════════════════════════════════════════════════════════════════

class GateResearchCache(BaseGate):
    """G3: Check research cache TTL."""

    def evaluate(self, cache_entry: dict | None = None, **kwargs) -> GateResult:
        if cache_entry and cache_entry.get("freshness") == "fresh":
            return GateResult(True, "pass", "Fresh cache available",
                              data=cache_entry)
        if cache_entry and cache_entry.get("freshness") == "stale":
            return GateResult(True, "soft_fail", "Stale cache - reusing",
                              data=cache_entry)
        return GateResult(False, "hard_fail", "No valid cache - research needed")


# ════════════════════════════════════════════════════════════════════
# G4: Post-Research Risk — check for dangerous content
# ════════════════════════════════════════════════════════════════════

class GatePostResearchRisk(BaseGate):
    """G4: Post-research risk check."""

    DANGER_KEYWORDS = ["ilegal", "banned", "defamation", "sara"]

    def evaluate(self, risk_flags: list[str] | None = None,
                 **kwargs) -> GateResult:
        flags = risk_flags or []
        if any(kw in " ".join(flags).lower() for kw in self.DANGER_KEYWORDS):
            return GateResult(False, "hard_fail", "High-risk content detected",
                              data={"risk_flags": flags})
        if any("unverified" in f.lower() for f in flags):
            return GateResult(
                True, "soft_fail",
                "Unverified claims - use cautious wording",
                data={"risk_flags": flags},
            )
        return GateResult(True, "pass", "No risks detected")


# ════════════════════════════════════════════════════════════════════
# G5: Source Quality — check available video sources
# ════════════════════════════════════════════════════════════════════

class GateSourceQuality(BaseGate):
    """G5: Source quality check."""

    def evaluate(self, video_sources: list | None = None, **kwargs) -> GateResult:
        sources = video_sources or []
        if len(sources) >= 2:
            return GateResult(True, "pass", f"{len(sources)} sources available")
        if len(sources) == 1:
            return GateResult(True, "soft_fail",
                              "Only 1 source - use Pexels fallback")
        return GateResult(False, "hard_fail", "No usable sources")


# ════════════════════════════════════════════════════════════════════
# G6: Creative Memory — check angle exhaustion
# ════════════════════════════════════════════════════════════════════

class GateCreativeMemory(BaseGate):
    """G6: Creative memory check."""

    def evaluate(self, used_angles: list[str] | None = None,
                 available_angles: list[str] | None = None, **kwargs) -> GateResult:
        used = set(used_angles or [])
        available = set(available_angles or [])
        remaining = available - used
        if len(remaining) >= 2:
            return GateResult(True, "pass", "Variation available",
                              data={"remaining_angles": list(remaining)})
        if len(remaining) == 1:
            return GateResult(True, "soft_fail", "Only 1 angle left")
        return GateResult(False, "hard_fail", "All angles exhausted")


# ════════════════════════════════════════════════════════════════════
# G7: Script Validation — check script + caption quality
# ════════════════════════════════════════════════════════════════════

class GateScriptValidation(BaseGate):
    """G7: Script validation."""

    def evaluate(self, script: str = "", caption: str = "", **kwargs) -> GateResult:
        if not script.strip():
            return GateResult(False, "hard_fail", "Empty script")
        if not caption.strip():
            return GateResult(False, "soft_fail", "Empty caption - auto-generate")
        if len(caption) > 150:
            return GateResult(True, "soft_fail",
                              "Caption >150 chars - trim needed")
        return GateResult(True, "pass", "Script and caption valid")


# ════════════════════════════════════════════════════════════════════
# G8: Audio Validation — check generated audio file
# ════════════════════════════════════════════════════════════════════

class GateAudioValidation(BaseGate):
    """G8: Audio validation."""

    def evaluate(self, audio_path: str | None = None, **kwargs) -> GateResult:
        if not audio_path or not Path(audio_path).exists():
            return GateResult(False, "hard_fail", "Audio file missing")
        size = Path(audio_path).stat().st_size
        if size == 0:
            return GateResult(False, "hard_fail", "Audio file is empty")
        return GateResult(True, "pass", "Audio valid")


# ════════════════════════════════════════════════════════════════════
# G9: Asset Validation — check visual assets
# ════════════════════════════════════════════════════════════════════

class GateAssetValidation(BaseGate):
    """G9: Asset validation."""

    def evaluate(self, asset_paths: list[str] | None = None,
                 **kwargs) -> GateResult:
        paths = asset_paths or []
        if not paths:
            return GateResult(False, "hard_fail", "No assets")
        valid = [p for p in paths
                 if Path(p).exists() and Path(p).stat().st_size > 0]
        if not valid:
            return GateResult(False, "hard_fail", "No valid assets")
        if len(valid) < len(paths):
            return GateResult(True, "soft_fail",
                              f"{len(valid)}/{len(paths)} assets valid")
        return GateResult(True, "pass", "All assets valid")


# ════════════════════════════════════════════════════════════════════
# G10: Video Output Validation — check final video
# ════════════════════════════════════════════════════════════════════

class GateVideoValidation(BaseGate):
    """G10: Video output validation."""

    def evaluate(self, video_path: str | None = None, **kwargs) -> GateResult:
        if not video_path or not Path(video_path).exists():
            return GateResult(False, "hard_fail", "Video file missing")
        size = Path(video_path).stat().st_size
        if size < 1024:
            return GateResult(False, "hard_fail", "Video file too small (<1KB)")
        return GateResult(True, "pass", "Video valid")
