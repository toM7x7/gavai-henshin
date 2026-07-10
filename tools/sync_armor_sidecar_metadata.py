"""Synchronize Wave 2 metadata from PART_SPECS into committed modeler sidecars.

This intentionally does not rebuild GLB/Blend assets. It only updates JSON
metadata that the Web Forge and modeler handoff read at runtime.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PART_SPECS_PATH = REPO_ROOT / "tools" / "blender" / "armor_part_specs.py"
ARMOR_PARTS_DIR = REPO_ROOT / "viewer" / "assets" / "armor-parts"

SYNC_KEYS = (
    "part_family",
    "variant_key",
    "base_motif_link",
    "topping_slots",
    "conflicts_with",
    "texture_zone_notes",
    "attachment_offset_target_m",
)


def load_part_specs(path: Path = PART_SPECS_PATH) -> dict[str, dict[str, Any]]:
    spec = importlib.util.spec_from_file_location("armor_part_specs_sync", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load armor_part_specs from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["armor_part_specs_sync"] = module
    spec.loader.exec_module(module)
    part_specs = getattr(module, "PART_SPECS", None)
    if not isinstance(part_specs, dict):
        raise RuntimeError("armor_part_specs.py must expose PART_SPECS")
    return part_specs


def _normalized_sidecar_value(value: Any) -> Any:
    return deepcopy(value)


def sync_sidecar_metadata(
    *,
    armor_parts_dir: Path = ARMOR_PARTS_DIR,
    part_specs: dict[str, dict[str, Any]] | None = None,
    check: bool = False,
) -> dict[str, Any]:
    specs = part_specs or load_part_specs()
    changed: list[str] = []
    missing: list[str] = []

    for module, part_spec in sorted(specs.items()):
        path = armor_parts_dir / module / f"{module}.modeler.json"
        if not path.exists():
            missing.append(str(path.relative_to(REPO_ROOT)).replace("\\", "/"))
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        original = deepcopy(payload)
        for key in SYNC_KEYS:
            if key in part_spec:
                payload[key] = _normalized_sidecar_value(part_spec[key])
        if payload != original:
            changed.append(str(path.relative_to(REPO_ROOT)).replace("\\", "/"))
            if not check:
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": not missing and (not check or not changed),
        "changed_count": len(changed),
        "changed": changed,
        "missing": missing,
        "checked_modules": len(specs),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift without writing files")
    parser.add_argument("--report-json", action="store_true", help="print a machine-readable report")
    args = parser.parse_args(argv)

    report = sync_sidecar_metadata(check=args.check)
    if args.report_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["changed_count"]:
        action = "would update" if args.check else "updated"
        print(f"{action} {report['changed_count']} modeler sidecar(s)")
        for path in report["changed"]:
            print(path)
    else:
        print("modeler sidecar metadata is in sync")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
