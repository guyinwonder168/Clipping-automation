"""Smoke tests — verify basic project structure works."""

import clipper_agency  # noqa: F401


def test_import():
    """Package can be imported without errors."""
    assert hasattr(clipper_agency, "__version__")
    parts = clipper_agency.__version__.split(".")
    assert len(parts) == 3, f"Expected semver, got {clipper_agency.__version__}"
    for part in parts:
        assert part.isdigit(), f"Version component not numeric: {part}"
