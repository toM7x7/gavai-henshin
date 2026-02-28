"""Project-wide constants derived from Lore + Blueprint."""

from __future__ import annotations

PROTOCOL_STATES = [
    "IDLE",
    "POSTED",
    "FIT_AUDIT",
    "MORPHOTYPE_LOCKED",
    "DESIGN_ISSUED",
    "DRY_FIT_SIM",
    "TRY_ON",
    "APPROVAL_PENDING",
    "APPROVED",
    "DEPOSITION",
    "SEALING",
    "ACTIVE",
    "ARCHIVED",
    "REFUSED",
]

HAPPY_PATH = [
    "IDLE",
    "POSTED",
    "FIT_AUDIT",
    "MORPHOTYPE_LOCKED",
    "DESIGN_ISSUED",
    "DRY_FIT_SIM",
    "TRY_ON",
    "APPROVAL_PENDING",
    "APPROVED",
    "DEPOSITION",
    "SEALING",
    "ACTIVE",
    "ARCHIVED",
]

REFUSAL_CODES = [
    "INCOMPLETE_PROCEDURE",
    "AUDIT_MISMATCH",
    "RESONANCE_UNSTABLE",
    "NC_CONTAMINATION_SUSPECT",
]

OATHS = [
    "NO_OMISSION",
    "NO_FABRICATION",
    "SEAL_INTACT",
    "AUDIT_READY",
    "REFUSAL_ACCEPTED",
    "NC_OBSERVED",
    "POSTED_OBEYED",
    "CLEARANCE_RESPECT",
    "PROTOCOL_COMPLETE",
    "INTEGRITY_FIRST",
]

REQUIRED_SUITSPEC_FIELDS = [
    "schema_version",
    "suit_id",
    "style_tags",
    "modules",
    "palette",
    "blueprint",
    "emblem",
    "effects",
    "text",
    "generation",
]

REQUIRED_MORPHOTYPE_FIELDS = [
    "schema_version",
    "morphotype_id",
    "height_cm",
    "shoulder_width_cm",
    "hip_width_cm",
    "arm_length_cm",
    "leg_length_cm",
    "torso_length_cm",
    "scale",
    "source",
    "confidence",
]

LEXICON = [
    "公示",
    "任命",
    "認可",
    "承認",
    "拒否",
    "監査",
    "照合",
    "記録院",
    "封印",
    "適合",
    "規格",
    "逸脱",
    "汚染",
    "腐食",
    "確定",
    "暫定",
    "正規",
    "非正規",
]
