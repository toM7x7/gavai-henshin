"""Load/store provisional project rules."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ProvisionalRules:
    schema_version: str
    id_pattern_suit: str
    id_pattern_session: str
    id_pattern_approval: str
    id_pattern_morphotype: str
    required_modules: list[str]
    projection_modes: list[str]
    refusal_codes: list[str]

    @classmethod
    def from_dict(cls, payload: dict) -> "ProvisionalRules":
        return cls(
            schema_version=payload["schema_version"],
            id_pattern_suit=payload["id_patterns"]["suit_id"],
            id_pattern_session=payload["id_patterns"]["session_id"],
            id_pattern_approval=payload["id_patterns"]["approval_id"],
            id_pattern_morphotype=payload["id_patterns"]["morphotype_id"],
            required_modules=payload["required_modules"],
            projection_modes=payload["projection_modes"],
            refusal_codes=payload["refusal_codes"],
        )


def load_rules(path: str | Path = "config/provisional_rules.json") -> ProvisionalRules:
    p = Path(path)
    with p.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    return ProvisionalRules.from_dict(data)
