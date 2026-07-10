"""Shared .env loading for provider credential/config resolution.

Environment variables always take precedence over .env values at the call
sites; this loader only backfills local development credentials. A relative
path that does not exist in the current working directory falls back to the
repository root, so starting the server from another directory does not
silently lose credentials.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: str | Path = ".env") -> dict[str, str]:
    p = Path(path)
    if not p.is_absolute() and not p.exists():
        fallback = _REPO_ROOT / p
        if fallback.exists():
            p = fallback
    if not p.exists() or not p.is_file():
        return {}

    values: dict[str, str] = {}
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values
