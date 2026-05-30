"""Tests for centralized logging configuration."""

import logging

from clipper_agency.core.logging import get_logger, setup_logging


def _reset_root_logger() -> None:
    """Remove all handlers from the root logger to isolate tests."""
    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    for handler in root.handlers[:]:
        root.removeHandler(handler)


def test_setup_logging_configures_root_logger():
    _reset_root_logger()
    setup_logging("DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    _reset_root_logger()


def test_setup_logging_default_is_info():
    _reset_root_logger()
    setup_logging()
    root = logging.getLogger()
    assert root.level == logging.INFO
    _reset_root_logger()


def test_setup_logging_is_noop_when_handlers_exist():
    root = logging.getLogger()
    _reset_root_logger()
    root.setLevel(logging.WARNING)
    handler = logging.StreamHandler()
    root.addHandler(handler)
    try:
        setup_logging("DEBUG")
        assert root.level != logging.DEBUG
    finally:
        root.removeHandler(handler)
        _reset_root_logger()


def test_get_logger_returns_named_logger():
    logger = get_logger("test.module")
    assert logger.name == "test.module"
