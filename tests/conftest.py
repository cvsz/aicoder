"""tests/conftest.py — shared fixtures for structured repo layout.

The upstream repo organizes modules into subdirectories (core/, api/,
agents/, utils/) but tests use flat imports. The root conftest.py adds
all subdirectories to sys.path so flat imports resolve correctly.
"""
import pytest


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Every test gets its own config file path so tests never read/write
    a real ~/.ai-coder-config.json on the machine running the suite."""
    fake_config = tmp_path / ".ai-coder-config.json"
    import config
    monkeypatch.setattr(config, "CONFIG_PATH", str(fake_config))
    yield fake_config


@pytest.fixture(autouse=True)
def no_real_api_key(monkeypatch):
    """Prevent tests from accidentally hitting the real API because a
    developer happens to have ANTHROPIC_API_KEY set in their shell."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    yield


@pytest.fixture
def fake_logger_setup():
    from logging_config import setup_logging
    setup_logging(level="DEBUG", fmt="text")
