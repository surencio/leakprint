"""Tests for secrets loader."""

import os
import textwrap
from pathlib import Path

import pytest

from leakprint.secrets import load_secrets, _resolve_path


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure env vars are clean before each test."""
    for key in ("HASS_URL", "HASS_TOKEN", "NVD_API_KEY", "LEAKPRINT_SECRETS_PATH"):
        monkeypatch.delenv(key, raising=False)


def _write_secrets(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "secrets.yaml"
    p.write_text(textwrap.dedent(content))
    return p


def test_load_sets_env_vars(tmp_path):
    path = _write_secrets(tmp_path, """\
        hass_url: http://ha.local:8123
        hass_token: tok123
        nvd_api_key: nvdkey
    """)
    applied = load_secrets(path)
    assert applied == {
        "HASS_URL": "http://ha.local:8123",
        "HASS_TOKEN": "tok123",
        "NVD_API_KEY": "nvdkey",
    }
    assert os.environ["HASS_URL"] == "http://ha.local:8123"
    assert os.environ["HASS_TOKEN"] == "tok123"
    assert os.environ["NVD_API_KEY"] == "nvdkey"


def test_env_var_takes_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("HASS_URL", "http://already-set:8123")
    path = _write_secrets(tmp_path, """\
        hass_url: http://from-file:8123
        hass_token: tok123
    """)
    applied = load_secrets(path)
    assert "HASS_URL" not in applied
    assert os.environ["HASS_URL"] == "http://already-set:8123"
    assert applied["HASS_TOKEN"] == "tok123"


def test_missing_file_returns_empty():
    applied = load_secrets("/nonexistent/secrets.yaml")
    assert applied == {}


def test_empty_yaml_returns_empty(tmp_path):
    path = _write_secrets(tmp_path, "")
    applied = load_secrets(path)
    assert applied == {}


def test_partial_keys(tmp_path):
    path = _write_secrets(tmp_path, """\
        hass_url: http://ha.local:8123
    """)
    applied = load_secrets(path)
    assert applied == {"HASS_URL": "http://ha.local:8123"}
    assert "HASS_TOKEN" not in os.environ


def test_resolve_via_env_var(tmp_path, monkeypatch):
    path = _write_secrets(tmp_path, "hass_url: test")
    monkeypatch.setenv("LEAKPRINT_SECRETS_PATH", str(path))
    resolved = _resolve_path()
    assert resolved == path


def test_resolve_cwd_fallback(tmp_path, monkeypatch):
    path = tmp_path / "secrets.yaml"
    path.write_text("hass_url: test")
    monkeypatch.chdir(tmp_path)
    resolved = _resolve_path()
    assert resolved == path


def test_no_secrets_file_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resolved = _resolve_path()
    assert resolved is None


def test_upper_case_keys_in_yaml(tmp_path):
    path = _write_secrets(tmp_path, """\
        HASS_URL: http://ha.local:8123
        HASS_TOKEN: tok123
    """)
    applied = load_secrets(path)
    assert applied["HASS_URL"] == "http://ha.local:8123"
    assert applied["HASS_TOKEN"] == "tok123"
