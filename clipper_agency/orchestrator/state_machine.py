"""Job state machine — validates and tracks pipeline state transitions.

The pipeline progresses through 20 defined states. Transitions are
governed by VALID_TRANSITIONS; illegal transitions raise ValueError.
COMPLETED is terminal; FAILED allows manual retry to CREATED.
PAUSED resumes to any active state (NOT COMPLETED).
"""

JOB_STATES = [
    "CREATED", "PREFLIGHT", "COST_ESTIMATED", "SAFETY_CHECKED",
    "RESEARCHING", "RESEARCH_REVIEWED", "SOURCES_VALIDATED",
    "MEMORY_CHECKED", "SCRIPTING", "SCRIPT_VALIDATED",
    "VOICING", "AUDIO_VALIDATED", "VISUALIZING",
    "ASSETS_VALIDATED", "COMPOSING", "VIDEO_VALIDATED",
    "REVIEWING", "COMPLETED", "FAILED", "PAUSED",
]

VALID_TRANSITIONS: dict[str, list[str]] = {
    "CREATED":            ["PREFLIGHT", "FAILED"],
    "PREFLIGHT":          ["COST_ESTIMATED", "FAILED", "PAUSED"],
    "COST_ESTIMATED":     ["SAFETY_CHECKED", "FAILED", "PAUSED"],
    "SAFETY_CHECKED":     ["RESEARCHING", "FAILED", "PAUSED"],
    "RESEARCHING":        ["RESEARCH_REVIEWED", "FAILED", "PAUSED"],
    "RESEARCH_REVIEWED":  ["SOURCES_VALIDATED", "FAILED", "PAUSED"],
    "SOURCES_VALIDATED":  ["MEMORY_CHECKED", "FAILED", "PAUSED"],
    "MEMORY_CHECKED":     ["SCRIPTING", "FAILED", "PAUSED"],
    "SCRIPTING":          ["SCRIPT_VALIDATED", "FAILED", "PAUSED"],
    "SCRIPT_VALIDATED":   ["VOICING", "FAILED", "PAUSED"],
    "VOICING":            ["AUDIO_VALIDATED", "FAILED", "PAUSED"],
    "AUDIO_VALIDATED":    ["VISUALIZING", "FAILED", "PAUSED"],
    "VISUALIZING":        ["ASSETS_VALIDATED", "FAILED", "PAUSED"],
    "ASSETS_VALIDATED":   ["COMPOSING", "FAILED", "PAUSED"],
    "COMPOSING":          ["VIDEO_VALIDATED", "FAILED", "PAUSED"],
    "VIDEO_VALIDATED":    ["REVIEWING", "FAILED", "PAUSED"],
    "REVIEWING":          ["COMPLETED", "FAILED", "PAUSED"],
    "COMPLETED":          [],
    "FAILED":             ["CREATED"],  # Manual retry from scratch
    "PAUSED":             [s for s in JOB_STATES if s not in ("COMPLETED", "PAUSED")],
}


class JobStateMachine:
    """Validates and tracks job state transitions."""

    def __init__(self, initial_state: str = "CREATED") -> None:
        if initial_state not in JOB_STATES:
            raise ValueError(f"Invalid initial state: {initial_state}")
        self.current_state = initial_state

    def transition_to(self, new_state: str) -> str:
        """Attempt to transition to a new state. Returns the new state.

        Raises ValueError if the transition is not allowed.
        """
        allowed = VALID_TRANSITIONS.get(self.current_state, [])
        if new_state not in allowed:
            raise ValueError(
                f"Cannot transition from {self.current_state} to "
                f"{new_state}. Allowed: {allowed}"
            )
        self.current_state = new_state
        return self.current_state

    def is_terminal(self) -> bool:
        """Return True if the current state is terminal (no further transitions)."""
        return self.current_state in ("COMPLETED", "FAILED")
