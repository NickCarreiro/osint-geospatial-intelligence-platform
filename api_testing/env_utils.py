#!/usr/bin/env python3
"""Helpers for loading and safely displaying API-testing credentials."""

import os
from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> None:
    """Load the project .env file for local API-testing scripts."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)


def require_env(name: str) -> str:
    """Return a required environment variable or fail with a clear message."""
    value = os.getenv(name)
    if value:
        return value

    raise RuntimeError(
        f"Missing required environment variable: {name}. "
        "Set it in the project .env before running this script."
    )


def redact_secret(value: str, visible_prefix: int = 4, visible_suffix: int = 4) -> str:
    """Redact a secret for debug output."""
    if not value:
        return "<missing>"

    if len(value) <= visible_prefix + visible_suffix:
        return "<redacted>"

    return f"{value[:visible_prefix]}...{value[-visible_suffix:]}"
