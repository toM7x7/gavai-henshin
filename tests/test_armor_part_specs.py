"""Pytest wrapper around tools/check_armor_part_specs.py.

These are static checks: they do not import Blender, do not read GLBs, and
they exercise the same heuristic the CLI uses so the CI signal matches a
local `python tools/check_armor_part_specs.py` run.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_TOOL_PATH = _REPO_ROOT / "tools" / "check_armor_part_specs.py"
_BUILDER_PATH = _REPO_ROOT / "tools" / "blender" / "armor_builder_core.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_armor_part_specs", _TOOL_PATH)
    assert spec and spec.loader, "could not load checker module spec"
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_armor_part_specs"] = module
    spec.loader.exec_module(module)
    return module


checker = _load_checker()


def _load_builder_core():
    sys.modules.setdefault("bmesh", types.ModuleType("bmesh"))
    sys.modules.setdefault("bpy", types.ModuleType("bpy"))
    mathutils = sys.modules.setdefault("mathutils", types.ModuleType("mathutils"))
    setattr(mathutils, "Vector", list)
    spec = importlib.util.spec_from_file_location("armor_builder_core_metadata_test", _BUILDER_PATH)
    assert spec and spec.loader, "could not load builder core module spec"
    module = importlib.util.module_from_spec(spec)
    sys.modules["armor_builder_core_metadata_test"] = module
    spec.loader.exec_module(module)
    return module


def test_no_module_fails_static_check() -> None:
    """Every PART_SPECS module passes the static envelope/material checks."""

    report = checker.run_checks()
    fails = [r for r in report["modules"] if r["status"] == "fail"]
    assert not fails, "static-check failures: " + "; ".join(
        f"{r['module']}: {'; '.join(r['issues'])}" for r in fails
    )


def test_every_blueprint_module_has_part_spec() -> None:
    """Every module in the blueprint snapshot exists in PART_SPECS."""

    part_specs = checker.load_part_specs()
    targets = checker.load_blueprint_targets()
    missing = sorted(set(targets.keys()) - set(part_specs.keys()))
    assert not missing, f"blueprint modules missing from PART_SPECS: {missing}"


def test_mirror_of_references_resolve() -> None:
    """Every mirror_of points at a real PART_SPECS entry."""

    part_specs = checker.load_part_specs()
    bad: list[str] = []
    for module, spec in part_specs.items():
        mirror_of = spec.get("mirror_of")
        if mirror_of and mirror_of not in part_specs:
            bad.append(f"{module} -> {mirror_of}")
    assert not bad, "mirror_of references that do not resolve: " + ", ".join(bad)


def test_waist_declares_closed_loop_metadata_without_claiming_glb_regen() -> None:
    """Waist carries a validator-usable loop contract, but marks GLB as pending."""

    waist = checker.load_part_specs()["waist"]
    waist_fit = waist.get("waist_fit")
    assert isinstance(waist_fit, dict), "waist_fit metadata missing"
    assert waist_fit["asset_status"] == "contract_metadata_only_glb_not_regenerated"

    inner = waist_fit.get("belt_loop_inner_diameter_m")
    outer = waist_fit.get("required_outer_diameter_m")
    target = waist.get("target_envelope_m")
    assert isinstance(inner, dict)
    assert isinstance(outer, dict)
    assert isinstance(target, dict)
    assert inner["x"] >= 0.36
    assert inner["z"] >= 0.36
    assert outer["z"] > target["z"], (
        "current waist z target cannot honestly satisfy a closed pelvis loop; "
        "metadata must keep this visible until GLB/target rebuild"
    )

    coverage = waist.get("body_wrap_coverage_contract")
    assert isinstance(coverage, dict)
    assert coverage["sample_directions"] == ["front_z", "back_z", "left_x", "right_x"]
    assert coverage["max_allowed_uncovered_arc_deg"] == 0.0
    assert "z front/back" in coverage["secondary_axis_policy"]


def test_builder_exports_waist_loop_metadata_for_future_sidecars() -> None:
    """The modeler sidecar exporter must carry waist loop metadata to validators."""

    builder_core = _load_builder_core()

    assert "body_wrap_loop" in builder_core._PRIMS
    payload = builder_core._part_spec_sidecar_metadata("waist")

    waist_fit = payload.get("waist_fit")
    assert isinstance(waist_fit, dict)
    assert "belt_loop_inner_diameter_m" in waist_fit
    assert waist_fit["asset_status"] == "contract_metadata_only_glb_not_regenerated"
    assert payload["body_wrap_loop_contract"]["authoring_primitive"] == "body_wrap_loop"
    assert payload["body_wrap_coverage_contract"]["sample_directions"] == [
        "front_z",
        "back_z",
        "left_x",
        "right_x",
    ]
