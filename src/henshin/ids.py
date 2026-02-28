"""ID generation rules (provisional v0.1)."""

from __future__ import annotations

import random
import string
from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _token(length: int, rng: random.Random | None = None) -> str:
    r = rng or random.Random()
    alphabet = string.ascii_uppercase + string.digits
    return "".join(r.choice(alphabet) for _ in range(length))


def _digits(length: int, rng: random.Random | None = None) -> str:
    r = rng or random.Random()
    return "".join(str(r.randint(0, 9)) for _ in range(length))


def _sanitize(value: str) -> str:
    cleaned = "".join(ch for ch in value.upper() if ch.isalnum())
    if not cleaned:
        raise ValueError("ID token must contain at least one alphanumeric character.")
    return cleaned


def generate_session_id(now: datetime | None = None, rng: random.Random | None = None) -> str:
    t = now or _utcnow()
    return f"S-{t:%Y%m%d}-{_token(4, rng=rng)}"


def generate_suit_id(series: str = "AXIS", role: str = "OP", rev: int = 0, seq: int = 1) -> str:
    if rev < 0 or rev > 99:
        raise ValueError("rev must be in range 0..99")
    if seq < 0 or seq > 9999:
        raise ValueError("seq must be in range 0..9999")
    return f"VDA-{_sanitize(series)}-{_sanitize(role)}-{rev:02d}-{seq:04d}"


def generate_approval_id(rng: random.Random | None = None) -> str:
    return f"APV-{_digits(8, rng=rng)}"


def generate_morphotype_id(rng: random.Random | None = None) -> str:
    return f"MTP-{_digits(8, rng=rng)}"
