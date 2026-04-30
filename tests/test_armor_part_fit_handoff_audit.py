import importlib.util
import json
import shutil
import struct
import unittest
from pathlib import Path


TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "audit_armor_part_fit_handoff.py"
SPEC = importlib.util.spec_from_file_location("audit_armor_part_fit_handoff", TOOL_PATH)
fit_handoff = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(fit_handoff)


def _pack_glb(json_obj: dict) -> bytes:
    json_bytes = json.dumps(json_obj, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((4 - (len(json_bytes) % 4)) % 4)
    chunks = struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
    total_length = 12 + len(chunks)
    return struct.pack("<III", 0x46546C67, 2, total_length) + chunks


def _write_synthetic_glb(path: Path, bbox: dict[str, float]) -> None:
    half = [float(bbox[axis]) / 2.0 for axis in ("x", "y", "z")]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        _pack_glb(
            {
                "asset": {"version": "2.0"},
                "scene": 0,
                "scenes": [{"nodes": [0]}],
                "nodes": [{"mesh": 0, "name": "synthetic_armor_part"}],
                "meshes": [
                    {
                        "name": "synthetic_armor_mesh",
                        "primitives": [{"attributes": {"POSITION": 0}, "indices": 1}],
                    }
                ],
                "accessors": [
                    {
                        "componentType": 5126,
                        "count": 8,
                        "max": [half[0], half[1], half[2]],
                        "min": [-half[0], -half[1], -half[2]],
                        "type": "VEC3",
                    },
                    {"componentType": 5123, "count": 12, "type": "SCALAR"},
                ],
                "bufferViews": [],
                "buffers": [{"byteLength": 0}],
            }
        )
    )


def _p0_metadata(module: str) -> dict:
    slots = {
        "helmet": ["crest", "visor_trim"],
        "chest": ["chest_core", "rib_trim"],
        "back": ["spine_ridge", "rear_core"],
        "waist": ["belt_buckle", "side_clip"],
        "left_shoulder": ["shoulder_fin", "edge_trim"],
        "right_shoulder": ["shoulder_fin", "edge_trim"],
        "left_shin": ["shin_spike", "ankle_cuff_trim"],
        "right_shin": ["shin_spike", "ankle_cuff_trim"],
    }.get(module)
    if not slots:
        return {}
    return {
        "variant_key": "sleek",
        "base_motif_link": {"name": f"{module}_motif", "surface_zone": "accent"},
        "topping_slots": [
            {
                "topping_slot": slot,
                "slot_transform": {"anchor": [0, 0, 0], "rotation_deg": [0, 0, 0]},
                "max_bbox_m": {"x": 0.05, "y": 0.05, "z": 0.05},
                "conflicts_with": [],
                "parent_module": module,
            }
            for slot in slots
        ],
    }


class TestArmorPartFitHandoffAudit(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.tmp_root = Path("tests/.tmp/test_armor_part_fit_handoff_audit") / self._testMethodName
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)
        self.tmp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_current_armor_parts_aggregation_recognizes_all_18_parts(self) -> None:
        audit = fit_handoff.collect_fit_handoff_audit(self.repo_root / "viewer/assets/armor-parts")

        self.assertEqual(audit["contract_version"], "armor-part-fit-handoff-audit.v1")
        self.assertEqual(audit["part_count"], 18)
        self.assertEqual(audit["expected_part_count"], 18)
        self.assertEqual(audit["missing_modules"], [])
        self.assertNotEqual(audit["status"], "fail", audit["failed_modules"])
        self.assertEqual(audit["failed_modules"], [])
        self.assertEqual([part["module"] for part in audit["parts"]], fit_handoff.expected_runtime_modules())
        self.assertGreater(audit["total_triangles"], 0)
        self.assertIn("base_surface", audit["material_zone_counts"])

        for part in audit["parts"]:
            self.assertIn("bbox_m", part)
            self.assertIn("glb_bbox_m", part)
            self.assertIn("target_bbox_m", part)
            self.assertIn("sidecar_glb_bbox_delta_m", part)
            self.assertIn("glb_geometry", part)
            self.assertIn("triangle_count", part)
            self.assertIn("material_zones", part)
            self.assertIn("primary_bone", part)
            self.assertIn("visual_priority_wave1", part)
            self.assertIn("bbox_target_status", part)
            self.assertIn("glb_bbox_target_status", part)
            self.assertIn("p0_metadata_check", part)
            self.assertIn("modeler_requests", part)
        self.assertTrue(audit["mirror_pair_checks"])

    def test_markdown_report_contains_modeler_handoff_sections(self) -> None:
        audit = fit_handoff.collect_fit_handoff_audit(self.repo_root / "viewer/assets/armor-parts")

        markdown = fit_handoff.render_modeler_fix_requests_markdown(audit)

        self.assertIn("# 装甲パーツ フィット監査 / モデラー修正依頼", markdown)
        self.assertIn("## 現状の格納場所", markdown)
        self.assertIn("## Wave 1優先 / Webプレビュー検収観点", markdown)
        self.assertIn("modeler_glb_available", markdown)
        self.assertIn("見た目優先度/Wave 1", markdown)
        self.assertIn("| helmet | head |", markdown)
        self.assertIn("ロード済みパーツ: 18 / 18", markdown)
        self.assertIn("python tools/audit_armor_part_fit_handoff.py --format markdown --output docs/armor-part-fit-modeler-requests.md", markdown)

    def test_wave1_checklist_is_short_modeler_handoff(self) -> None:
        checklist = (self.repo_root / "docs/modeler-wave1-checklist.md").read_text(encoding="utf-8")

        self.assertIn("# Wave 1 モデラー発注チェックリスト", checklist)
        self.assertIn("## 格納場所", checklist)
        self.assertIn("## 対象パーツ", checklist)
        self.assertIn("## P0観点", checklist)
        self.assertIn("## P1観点", checklist)
        self.assertIn("## Webプレビュー検収", checklist)
        self.assertIn("## 納品チェック", checklist)
        self.assertIn("## 確認コマンド", checklist)
        self.assertIn("`chest`, `back`, `waist`, `left_shoulder`, `right_shoulder`", checklist)
        self.assertIn("python tools/validate_armor_parts_intake.py", checklist)
        self.assertIn("python tools/audit_armor_part_fit_handoff.py --format markdown --output docs/armor-part-fit-modeler-requests.md", checklist)

    def test_bbox_and_anchor_mismatches_generate_direct_modeler_requests(self) -> None:
        self._write_sidecar(
            "helmet",
            {
                "bbox_m": {"size": [0.1, 0.1, 0.1]},
                "triangle_count": 2000,
                "material_zones": ["accent"],
                "vrm_attachment": {"primary_bone": "hips"},
            },
        )

        audit = fit_handoff.collect_fit_handoff_audit(self.tmp_root)
        helmet = audit["parts"][0]

        self.assertEqual(helmet["module"], "helmet")
        self.assertIn("x", helmet["bbox_outside_tolerance_axes"])
        self.assertEqual(helmet["visual_priority_wave1"]["priority"], "P1 / Wave 1 review")
        self.assertTrue(any("bbox is outside target envelope" in item for item in helmet["modeler_requests"]))
        self.assertTrue(any("triangles" in item for item in helmet["modeler_requests"]))
        self.assertTrue(any("base_surface" in item for item in helmet["modeler_requests"]))
        self.assertTrue(any("body-fit anchor" in item for item in helmet["modeler_requests"]))
        self.assertTrue(any("見た目優先度/Wave 1" in item for item in helmet["modeler_requests"]))

    def test_glb_bounds_mismatch_and_back_thinness_generate_requests(self) -> None:
        target = fit_handoff._reference_target_dimensions("back")
        thin_glb = {**target, "z": target["z"] * 0.40}
        self._write_sidecar(
            "back",
            {
                "bbox_m": {
                    "x": target["x"],
                    "y": target["y"],
                    "z": target["z"],
                    "size": [target["x"], target["y"], target["z"]],
                },
                "vrm_attachment": {"primary_bone": "upperChest"},
            },
        )
        _write_synthetic_glb(self.tmp_root / "back" / "back.glb", thin_glb)

        audit = fit_handoff.collect_fit_handoff_audit(self.tmp_root)
        back = audit["parts"][2]

        self.assertEqual(back["module"], "back")
        self.assertEqual(back["glb_bbox_outside_tolerance_axes"], ["z"])
        self.assertEqual(back["sidecar_glb_bbox_outside_tolerance_axes"], ["z"])
        self.assertTrue(any("Sync sidecar `bbox_m`" in item for item in back["modeler_requests"]))
        self.assertTrue(any("Back GLB z-thickness is too thin" in item for item in back["modeler_requests"]))

    def test_bbox_acceptance_tiers_warn_between_10_and_15_and_fail_above_15(self) -> None:
        target = fit_handoff._reference_target_dimensions("helmet")
        warn_bbox = {axis: target[axis] * 1.12 for axis in ("x", "y", "z")}
        self._write_sidecar(
            "helmet",
            {
                **_p0_metadata("helmet"),
                "bbox_m": {"size": [warn_bbox["x"], warn_bbox["y"], warn_bbox["z"]]},
                "target_envelope_m": target,
                "vrm_attachment": {"primary_bone": "head"},
            },
        )
        _write_synthetic_glb(self.tmp_root / "helmet" / "helmet.glb", warn_bbox)

        audit = fit_handoff.collect_fit_handoff_audit(self.tmp_root)
        helmet = audit["parts"][0]

        self.assertEqual(helmet["bbox_target_status"], "warn")
        self.assertEqual(helmet["glb_bbox_target_status"], "warn")
        self.assertEqual(helmet["status"], "warn")

        fail_bbox = {axis: target[axis] * 1.20 for axis in ("x", "y", "z")}
        self._write_sidecar(
            "helmet",
            {
                **_p0_metadata("helmet"),
                "bbox_m": {"size": [fail_bbox["x"], fail_bbox["y"], fail_bbox["z"]]},
                "target_envelope_m": target,
                "vrm_attachment": {"primary_bone": "head"},
            },
        )
        _write_synthetic_glb(self.tmp_root / "helmet" / "helmet.glb", fail_bbox)

        audit = fit_handoff.collect_fit_handoff_audit(self.tmp_root)
        helmet = audit["parts"][0]

        self.assertEqual(helmet["bbox_target_status"], "fail")
        self.assertEqual(helmet["glb_bbox_target_status"], "fail")
        self.assertEqual(helmet["status"], "fail")

    def test_mirror_pair_dimension_delta_above_five_percent_fails_pair(self) -> None:
        left_target = fit_handoff._reference_target_dimensions("left_forearm")
        right_bbox = {**left_target, "x": left_target["x"] * 1.06}
        self._write_sidecar(
            "left_forearm",
            {
                "bbox_m": {"size": [left_target["x"], left_target["y"], left_target["z"]]},
                "vrm_attachment": {"primary_bone": "leftLowerArm"},
            },
        )
        self._write_sidecar(
            "right_forearm",
            {
                "bbox_m": {"size": [right_bbox["x"], right_bbox["y"], right_bbox["z"]]},
                "vrm_attachment": {"primary_bone": "rightLowerArm"},
            },
        )
        _write_synthetic_glb(self.tmp_root / "left_forearm" / "left_forearm.glb", left_target)
        _write_synthetic_glb(self.tmp_root / "right_forearm" / "right_forearm.glb", right_bbox)

        audit = fit_handoff.collect_fit_handoff_audit(self.tmp_root)
        pair = next(check for check in audit["mirror_pair_checks"] if check["pair"] == ["left_forearm", "right_forearm"])

        self.assertEqual(pair["status"], "fail")
        self.assertGreater(pair["max_delta_pct"], 5.0)

    def _write_sidecar(self, module: str, overrides: dict) -> None:
        module_dir = self.tmp_root / module
        module_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "contract_version": "modeler-part-sidecar.v1",
            "module": module,
            "part_id": f"viewer.mesh.{module}.v1",
            "bbox_m": {"size": [0.2, 0.2, 0.2]},
            "triangle_count": 10,
            "material_zones": ["base_surface"],
            "vrm_attachment": {"primary_bone": "head"},
        }
        payload.update(overrides)
        (module_dir / f"{module}.modeler.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
