from __future__ import annotations

import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any


TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "audit_modeler_part_delivery.py"
SPEC = importlib.util.spec_from_file_location("audit_modeler_part_delivery", TOOL_PATH)
audit_tool = importlib.util.module_from_spec(SPEC)
sys.modules["audit_modeler_part_delivery"] = audit_tool
assert SPEC.loader is not None
SPEC.loader.exec_module(audit_tool)


def _write_glb(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    chunk = b"{}  "
    payload = struct.pack("<4sII", b"glTF", 2, 20 + len(chunk))
    payload += struct.pack("<II", len(chunk), 0x4E4F534A)
    payload += chunk
    path.write_bytes(payload)


def _write_asset(root: Path, module: str, asset_key: str, *, fidelity_notes: str | None = None) -> None:
    if asset_key == "canonical":
        asset_dir = root / module
        stem = module
    else:
        asset_dir = root / module / "variants" / asset_key
        stem = f"{module}__{asset_key}"
    _write_glb(asset_dir / f"{stem}.glb")
    sidecar: dict[str, Any] = {
        "variant_key": f"{module}:{asset_key}" if asset_key != "canonical" else f"{module}:canonical",
        "bbox_m": {"x": 0.2, "y": 0.3, "z": 0.1},
        "target_envelope_m": {"x": 0.24, "y": 0.34, "z": 0.14},
        "vrm_attachment": {"primary_bone": "head", "offset_m": [0, 0.08, 0.12]},
    }
    if fidelity_notes:
        sidecar["fidelity_notes"] = fidelity_notes
    (asset_dir / f"{stem}.modeler.json").write_text(
        json.dumps(sidecar, ensure_ascii=False),
        encoding="utf-8",
    )
    (asset_dir / "source").mkdir(parents=True, exist_ok=True)
    (asset_dir / "source" / f"{stem}.blend").write_bytes(b"BLENDER")
    (asset_dir / "preview").mkdir(parents=True, exist_ok=True)
    (asset_dir / "preview" / f"{stem}.mesh.json").write_text(
        json.dumps(
            {
                "format": "mesh.v1",
                "positions": [0, 0, 0, 1, 0, 0, 0, 1, 0],
                "indices": [0, 1, 2],
                "bounds": {"min": [0, 0, 0], "max": [0.2, 0.3, 0.1]},
            }
        ),
        encoding="utf-8",
    )


def test_catalog_lineage_turns_delivery_variant_into_fidelity_hold(tmp_path: Path) -> None:
    assets = tmp_path / "armor-parts"
    _write_asset(assets, "helmet", "canonical", fidelity_notes="canonical reviewed")
    _write_asset(assets, "helmet", "rescue_sleek")
    catalog = {
        "modules": {
            "helmet": {
                "part_family": "head",
                "base_motif_link": {"name": "head_crest_line", "surface_zone": "emissive"},
                "variants": [
                    {
                        "variant_key": "helmet:rescue_sleek",
                        "display_name": "Rescue Knight Sleek - helmet",
                        "line_id": "line_rescue_knight",
                        "source_concept": "c02 Rescue Knight Sleek",
                        "design_intent": "thin rescue visor",
                    }
                ],
            }
        }
    }
    catalog_path = assets / "variant_catalog.json"
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")

    result = audit_tool.audit_parts(["helmet"], assets_root=assets, catalog_path=catalog_path)
    variant = next(asset for asset in result["parts"][0]["assets"] if asset["asset_key"] == "rescue_sleek")

    assert variant["status"] == "fidelity_hold"
    assert variant["selected_line_info"]["line_id"] == "line_rescue_knight"
    assert variant["selected_line_info"]["source_concept_ids"] == ["c02 Rescue Knight Sleek"]
    assert variant["selected_line_info"]["design_intent"] == "thin rescue visor"

