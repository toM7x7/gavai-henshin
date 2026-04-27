"""ID generation rules (provisional v0.1)."""

from __future__ import annotations

import random
import re
import string
from datetime import datetime, timezone

_SUIT_ID_PARTS_RE = re.compile(r"^VDA-([A-Z0-9]+)-([A-Z0-9]+)-([0-9]{2})-([0-9]{4})$")
_RECALL_CODE_RE = re.compile(r"^[A-Z0-9]{4}$")


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


def parse_suit_id(suit_id: str) -> dict[str, int | str]:
    match = _SUIT_ID_PARTS_RE.fullmatch(str(suit_id or ""))
    if not match:
        raise ValueError("suit_id format is invalid")
    series, role, rev, seq = match.groups()
    return {"series": series, "role": role, "rev": int(rev), "seq": int(seq)}


def next_suit_id(
    existing_ids: list[str] | tuple[str, ...],
    *,
    series: str = "AXIS",
    role: str = "OP",
    rev: int = 0,
) -> str:
    normalized_series = _sanitize(series)
    normalized_role = _sanitize(role)
    max_seq = 0
    for suit_id in existing_ids:
        try:
            parsed = parse_suit_id(suit_id)
        except ValueError:
            continue
        if (
            parsed["series"] == normalized_series
            and parsed["role"] == normalized_role
            and parsed["rev"] == rev
        ):
            max_seq = max(max_seq, int(parsed["seq"]))
    return generate_suit_id(series=normalized_series, role=normalized_role, rev=rev, seq=max_seq + 1)


def normalize_recall_code(value: str) -> str:
    code = "".join(ch for ch in str(value or "").upper() if ch.isalnum())
    if not _RECALL_CODE_RE.fullmatch(code):
        raise ValueError("recall_code must be exactly 4 alphanumeric characters")
    return code


def generate_recall_code(rng: random.Random | None = None) -> str:
    return _token(4, rng=rng)


def next_recall_code(existing_codes: list[str] | tuple[str, ...], rng: random.Random | None = None) -> str:
    used = set()
    for code in existing_codes:
        try:
            used.add(normalize_recall_code(code))
        except ValueError:
            continue
    for _ in range(128):
        code = generate_recall_code(rng=rng)
        if code not in used:
            return code
    raise ValueError("Unable to allocate a unique recall_code")


def generate_approval_id(rng: random.Random | None = None) -> str:
    return f"APV-{_digits(8, rng=rng)}"


def generate_morphotype_id(rng: random.Random | None = None) -> str:
    return f"MTP-{_digits(8, rng=rng)}"
