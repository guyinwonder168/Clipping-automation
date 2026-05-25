"""Smoke tests — verify basic project structure works."""

import clipper_agency  # noqa: F401


def test_import():
    """Package can be imported without errors."""
    assert clipper_agency.__version__ is not None
