"""Pytest wrapper around tools/check_armor_part_specs.py.

These are static checks: they do not import Blender, do not read GLBs, and
they exercise the same heuristic the CLI uses so the CI signal matches a
local `python tools/check_armor_part_specs.py` run.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_TOOL_PATH = _REPO_ROOT / "tools" / "check_armor_part_specs.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_armor_part_specs", _TOOL_PATH)
    assert spec and spec.loader, "could not load checker module spec"
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_armor_part_specs"] = module
    spec.loader.exec_module(module)
    return module


checker = _load_checker()


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
