"""Tests for the job state machine."""

import pytest

from clipper_agency.orchestrator.state_machine import (
    JobStateMachine,
    JOB_STATES,
    VALID_TRANSITIONS,
)


def test_initial_state():
    sm = JobStateMachine()
    assert sm.current_state == "CREATED"


def test_initial_state_default():
    sm = JobStateMachine()
    assert sm.current_state == "CREATED"
    assert not sm.is_terminal()


def test_valid_transition():
    sm = JobStateMachine()
    sm.transition_to("PREFLIGHT")
    assert sm.current_state == "PREFLIGHT"


def test_invalid_transition():
    sm = JobStateMachine()
    with pytest.raises(ValueError, match="Cannot transition"):
        sm.transition_to("COMPLETED")  # Can't jump from CREATED to COMPLETED


def test_full_pipeline():
    states = [
        "CREATED", "PREFLIGHT", "COST_ESTIMATED", "SAFETY_CHECKED",
        "RESEARCHING", "RESEARCH_REVIEWED", "SOURCES_VALIDATED",
        "MEMORY_CHECKED", "SCRIPTING", "SCRIPT_VALIDATED",
        "VOICING", "AUDIO_VALIDATED", "VISUALIZING",
        "ASSETS_VALIDATED", "COMPOSING", "VIDEO_VALIDATED",
        "REVIEWING", "COMPLETED",
    ]
    sm = JobStateMachine()
    for i, state in enumerate(states[1:], 1):
        sm.transition_to(state)
        assert sm.current_state == state
    assert sm.is_terminal()


def test_failure_state():
    sm = JobStateMachine()
    sm.transition_to("FAILED")
    assert sm.is_terminal()


def test_paused_state_can_resume():
    sm = JobStateMachine()
    sm.transition_to("PREFLIGHT")
    sm.transition_to("PAUSED")
    # From PAUSED we can go to any state — choose RESEARCHING
    sm.transition_to("RESEARCHING")
    assert sm.current_state == "RESEARCHING"


def test_invalid_initial_state():
    with pytest.raises(ValueError, match="Invalid initial state"):
        JobStateMachine(initial_state="NONEXISTENT")


def test_job_states_are_strings():
    for state in JOB_STATES:
        assert isinstance(state, str)


def test_all_valid_transitions_have_known_targets():
    """Every target state in VALID_TRANSITIONS must be in JOB_STATES."""
    state_set = set(JOB_STATES)
    for source, targets in VALID_TRANSITIONS.items():
        for target in targets:
            assert target in state_set, (
                f"Target '{target}' (from '{source}') not in JOB_STATES"
            )
