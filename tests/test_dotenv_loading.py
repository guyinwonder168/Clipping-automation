"""Tests for dotenv loading at application startup."""

import os
from unittest.mock import patch

import pytest


class TestDotenvLoading:
    """Verify that load_dotenv() is called at import time in __main__."""

    def test_load_dotenv_called_in_main_module(self):
        """The __main__ module calls load_dotenv() at import time."""
        from dotenv import load_dotenv

        # Re-import __main__ to verify load_dotenv was called
        with patch("dotenv.load_dotenv", wraps=load_dotenv) as mock_load:
            # Force re-import by removing from sys.modules cache
            import importlib
            import clipper_agency.__main__ as main_mod

            importlib.reload(main_mod)
            mock_load.assert_called()

    def test_env_vars_available_after_load_dotenv(self):
        """After load_dotenv(), variables from .env should be in os.environ."""
        # This test verifies the mechanism works when a .env file exists
        import tempfile
        from pathlib import Path

        from dotenv import load_dotenv

        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("TEST_CLIPPER_VAR=hello_from_dotenv\n")

            # Point dotenv to our temp .env file
            with patch.dict(os.environ, {}, clear=True):
                loaded = load_dotenv(str(env_file), override=True)
                assert loaded is True
                assert os.getenv("TEST_CLIPPER_VAR") == "hello_from_dotenv"
