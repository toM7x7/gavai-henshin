from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "validate_variant_catalog.py"
SPEC = importlib.util.spec_from_file_location("validate_variant_catalog", TOOL_PATH)
validator = importlib.util.module_from_spec(SPEC)
sys.modules["validate_variant_catalog"] = validator
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


def _slot(module: str, name: str, *, conflicts_with: list[str] | None = None) -> dict[str, Any]:
    return {
        "topping_slot": name,
        "slot_kind": "detail",
        "allowed_count": {"min": 0, "max": 1},
        "anchor_hint": {
            "body_anchor": module,
            "parent_surface": "front_center",
            "placement": f"{name} placement",
        },
        "max_bbox_m": {"x": 0.1, "y": 0.1, "z": 0.05},
        "material_zone": "accent_trim",
        "variant_examples": [f"{name} example"],
        "conflicts_with": conflicts_with or [],
        "parent_module": module,
    }


def _variant(module: str, name: str = "base", *, mirror_of: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "variant_key": f"{module}:{name}",
        "display_name": f"{module} {name}",
        "base_motif_link": {"name": f"{module}_motif", "surface_zone": "emissive"},
        "detail_features": [
            "separate armor panels preserve the body read",
            "small trim breaks up flat proxy surfaces",
        ],
        "recommended_topping_slots": ["primary", "secondary"],
    }
    if mirror_of:
        payload["mirror_of"] = mirror_of
    return payload


def _module(module: str, *, mirror_of: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "part_family": "test_family",
        "base_motif_link": {"name": f"{module}_motif", "surface_zone": "emissive"},
        "variants": [_variant(module, "base"), _variant(module, "sleek")],
        "topping_slots": [_slot(module, "primary"), _slot(module, "secondary")],
    }
    if mirror_of:
        payload["mirror_of"] = mirror_of
    return payload


def _catalog(*, modules: dict[str, Any] | None = None, expected: tuple[str, ...] = ("left_hand", "right_hand")) -> dict[str, Any]:
    catalog_modules = modules or {
        "left_hand": _module("left_hand"),
        "right_hand": _module("right_hand", mirror_of="left_hand"),
    }
    return {
        "contract_version": validator.CATALOG_CONTRACT_VERSION,
        "schema_version": validator.CATALOG_CONTRACT_VERSION,
        "canonical_parts": list(expected),
        "modules": catalog_modules,
    }


def test_synthetic_catalog_passes_with_variants_slots_mirror_and_materials() -> None:
    payload = _catalog()

    result = validator.validate_catalog_payload(
        payload,
        expected_modules=("left_hand", "right_hand"),
    )

    assert result["status"] == "pass"
    assert result["ok"]
    assert result["module_count"] == 2
    assert result["modules"]["right_hand"]["topping_slots"] == ["primary", "secondary"]
    assert "accent_trim" in result["modules"]["right_hand"]["material_zones"]
    assert "emissive" in result["modules"]["right_hand"]["material_zones"]


def test_committed_wave2_catalog_validates_without_hard_failures() -> None:
    result = validator.validate_variant_catalog(
        strict_mirror_of=True,
        strict_recommended_slots=True,
    )

    assert len(validator.EXPECTED_MODULES) == 18
    assert result["ok"], result["reasons"]
    assert result["status"] == "pass"
    assert result["module_count"] == 18
    assert sorted(result["modules"]) == sorted(validator.EXPECTED_MODULES)
    assert all(report["variant_count"] >= 1 for report in result["modules"].values())
    assert all(report["topping_slot_count"] >= 1 for report in result["modules"].values())


def test_missing_required_p0_topping_slot_fails() -> None:
    payload = _catalog(
        expected=("left_shin", "right_shin"),
        modules={
            "left_shin": _module("left_shin"),
            "right_shin": _module("right_shin", mirror_of="left_shin"),
        },
    )
    payload["modules"]["left_shin"]["topping_slots"] = [_slot("left_shin", "shin_spike")]

    result = validator.validate_catalog_payload(
        payload,
        expected_modules=("left_shin", "right_shin"),
    )

    assert not result["ok"]
    assert result["status"] == "fail"
    assert any("left_shin: missing required topping slots" in reason for reason in result["reasons"])


def test_duplicate_variant_key_fails() -> None:
    payload = _catalog()
    payload["modules"]["left_hand"]["variants"] = [
        _variant("left_hand", "base"),
        _variant("left_hand", "base"),
    ]

    result = validator.validate_catalog_payload(
        payload,
        expected_modules=("left_hand", "right_hand"),
    )

    assert not result["ok"]
    assert "left_hand:base: duplicate variant_key" in result["reasons"]


def test_cli_json_report_returns_success_for_strict_current_catalog(capsys) -> None:
    rc = validator.main(["--report-json", "--strict-mirror-of", "--strict-recommended-slots"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert payload["ok"]
    assert payload["status"] == "pass"
    assert payload["module_count"] == 18


def test_strict_mirror_of_turns_migration_warning_into_failure() -> None:
    payload = _catalog()
    del payload["modules"]["right_hand"]["mirror_of"]

    soft = validator.validate_catalog_payload(
        payload,
        expected_modules=("left_hand", "right_hand"),
    )
    strict = validator.validate_catalog_payload(
        payload,
        expected_modules=("left_hand", "right_hand"),
        strict_mirror_of=True,
    )

    assert soft["ok"]
    assert any("right_hand: mirror_of should point at left_hand" in warning for warning in soft["warnings"])
    assert not strict["ok"]
    assert "right_hand: mirror_of should point at left_hand" in strict["reasons"]


def test_payload_validation_does_not_mutate_input() -> None:
    payload = _catalog()
    before = copy.deepcopy(payload)

    validator.validate_catalog_payload(payload, expected_modules=("left_hand", "right_hand"))

    assert payload == before
