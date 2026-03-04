"""Load secrets from a YAML file into environment variables.

Lookup order:
  1. Path in LEAKPRINT_SECRETS_PATH env var
  2. secrets.yaml in the current working directory

Env vars already set take precedence (secrets file is a fallback).

Supported keys (case-insensitive in YAML, mapped to upper-case env vars):
  hass_url      -> HASS_URL
  hass_token    -> HASS_TOKEN
  nvd_api_key   -> NVD_API_KEY
"""

import os
from pathlib import Path

_KNOWN_KEYS = {
    "hass_url": "HASS_URL",
    "hass_token": "HASS_TOKEN",
    "nvd_api_key": "NVD_API_KEY",
}


def load_secrets(secrets_path: Path | str | None = None) -> dict[str, str]:
    """Load secrets YAML and populate env vars that are not already set.

    Returns a dict of env vars that were set from the file.
    """
    path = _resolve_path(secrets_path)
    if path is None:
        return {}

    try:
        import yaml
    except ImportError:
        raise RuntimeError(
            "PyYAML is required to load secrets.yaml. Install it with: pip install pyyaml"
        )

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        return {}

    applied: dict[str, str] = {}
    for yaml_key, env_key in _KNOWN_KEYS.items():
        value = data.get(yaml_key) or data.get(yaml_key.upper())
        if value is None:
            continue
        value = str(value).strip()
        if not value:
            continue
        # Env var already set → skip (env takes precedence)
        if os.environ.get(env_key):
            continue
        os.environ[env_key] = value
        applied[env_key] = value

    return applied


def _resolve_path(explicit: Path | str | None = None) -> Path | None:
    """Return the secrets file path or None if nothing found."""
    if explicit is not None:
        p = Path(explicit)
        if p.is_file():
            return p
        return None

    # LEAKPRINT_SECRETS_PATH env var
    env_path = os.environ.get("LEAKPRINT_SECRETS_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p
        return None

    # cwd fallback
    cwd_path = Path.cwd() / "secrets.yaml"
    if cwd_path.is_file():
        return cwd_path

    return None
