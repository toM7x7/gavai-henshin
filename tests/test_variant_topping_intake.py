from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "validate_variant_catalog.py"
SPEC = importlib.util.spec_from_file_location("validate_variant_catalog_topping", TOOL_PATH)
validator = importlib.util.module_from_spec(SPEC)
sys.modules["validate_variant_catalog_topping"] = validator
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


def _variant(module: str, *, recommended: list[str] | None = None) -> dict[str, Any]:
    return {
        "variant_key": f"{module}:base",
        "display_name": "Base",
        "base_motif_link": {"name": "hand_motif", "surface_zone": "emissive"},
        "detail_features": [
            "knuckle plate keeps hand silhouette readable",
            "cuff trim ties the glove back to the forearm",
        ],
        "recommended_topping_slots": recommended or ["knuckle_plate"],
    }


def _slot(
    module: str,
    name: str,
    *,
    material_zone: str | None = "accent_trim",
    conflicts_with: list[str] | None = None,
    use_slot_transform: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "topping_slot": name,
        "slot_kind": "micro",
        "allowed_count": {"min": 0, "max": 2},
        "max_bbox_m": {"x": 0.08, "y": 0.04, "z": 0.04},
        "variant_examples": ["raised knuckle", "small signal lens"],
        "conflicts_with": conflicts_with or [],
        "parent_module": module,
    }
    if material_zone is not None:
        payload["material_zone"] = material_zone
    if use_slot_transform:
        payload["slot_transform"] = {
            "anchor": [0.0, 0.02, 0.01],
            "rotation_deg": [0.0, 0.0, 0.0],
        }
    else:
        payload["anchor_hint"] = {
            "body_anchor": "left_hand",
            "parent_surface": "back_of_hand",
            "placement": "above the knuckles",
        }
    return payload


def _catalog(slot: dict[str, Any], *, recommended: list[str] | None = None) -> dict[str, Any]:
    return {
        "contract_version": validator.CATALOG_CONTRACT_VERSION,
        "canonical_parts": ["left_hand"],
        "modules": {
            "left_hand": {
                "part_family": "hand",
                "base_motif_link": {"name": "hand_motif", "surface_zone": "emissive"},
                "variants": [_variant("left_hand", recommended=recommended)],
                "topping_slots": [slot],
            }
        },
    }


def test_topping_slot_accepts_slot_transform_contract_without_anchor_hint() -> None:
    payload = _catalog(_slot("left_hand", "knuckle_plate", use_slot_transform=True))

    result = validator.validate_catalog_payload(payload, expected_modules=("left_hand",))

    assert result["status"] == "pass"
    assert result["ok"]


def test_topping_slot_conflict_must_reference_local_slot() -> None:
    payload = _catalog(_slot("left_hand", "knuckle_plate", conflicts_with=["missing_slot"]))

    result = validator.validate_catalog_payload(payload, expected_modules=("left_hand",))

    assert not result["ok"]
    assert "left_hand: topping_slot knuckle_plate conflicts_with unknown slot 'missing_slot'" in result["reasons"]


def test_topping_slot_requires_material_zone() -> None:
    payload = _catalog(_slot("left_hand", "knuckle_plate", material_zone=None))

    result = validator.validate_catalog_payload(payload, expected_modules=("left_hand",))

    assert not result["ok"]
    assert "left_hand: topping_slot knuckle_plate: material_zone missing" in result["reasons"]


def test_recommended_topping_slot_gap_is_warning_until_strict_mode() -> None:
    payload = _catalog(
        _slot("left_hand", "knuckle_plate"),
        recommended=["knuckle_plate", "future_cuff_lock"],
    )

    soft = validator.validate_catalog_payload(payload, expected_modules=("left_hand",))
    strict = validator.validate_catalog_payload(
        payload,
        expected_modules=("left_hand",),
        strict_recommended_slots=True,
    )

    assert soft["ok"]
    assert any("future_cuff_lock" in warning for warning in soft["warnings"])
    assert not strict["ok"]
    assert any("future_cuff_lock" in reason for reason in strict["reasons"])


def test_committed_wave2_variant_topping_assets_match_catalog_and_sidecars() -> None:
    result = validator.validate_delivered_asset_inventory()

    assert result["variant_count"] == 54
    assert result["topping_count"] == 32
    assert result["ok"], result["reasons"]
