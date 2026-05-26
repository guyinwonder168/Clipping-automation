"""Orchestrator — pipeline coordination, gates, and state machine."""

from clipper_agency.orchestrator.gates import (
    GateResult,
    GateInputPreflight,
    GateCostEstimate,
    GateResearchCache,
    GatePostResearchRisk,
    GateSourceQuality,
    GateCreativeMemory,
    GateScriptValidation,
    GateAudioValidation,
    GateAssetValidation,
    GateVideoValidation,
)

__all__ = [
    "GateResult",
    "GateInputPreflight",
    "GateCostEstimate",
    "GateResearchCache",
    "GatePostResearchRisk",
    "GateSourceQuality",
    "GateCreativeMemory",
    "GateScriptValidation",
    "GateAudioValidation",
    "GateAssetValidation",
    "GateVideoValidation",
]
