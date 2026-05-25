"""Clipper Agency — automated short-form video content production."""

try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("clipper-agency")
except PackageNotFoundError:
    __version__ = "0.0.0"
