import json
import shutil
import unittest
from pathlib import Path

from henshin.armor_model_quality import (
    P0_MODEL_PARTS,
    audit_mesh_payload,
    audit_viewer_mesh_assets,
    compute_position_bounds,
    ensure_mesh_payload_bounds,
)


def _valid_mesh_payload() -> dict:
    return {
        "format": "mesh.v1",
        "positions": [0, 0, 0, 1, 0, 0, 0, 1, 1],
        "normals": [0, -1, 0, 0, -1, 0, 0, -1, 0],
        "uv": [0, 0, 1, 0, 0, 1],
        "indices": [0, 1, 2],
        "bounds": {"min": [0, 0, 0], "max": [1, 1, 1]},
    }


class TestArmorModelQuality(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tests/.tmp/test_armor_model_quality") / self._testMethodName
        if self.root.exists():
            shutil.rmtree(self.root)
        self.mesh_dir = self.root / "viewer" / "assets" / "meshes"
        self.mesh_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)

    def _write_mesh(self, part: str, payload: dict | None = None) -> None:
        (self.mesh_dir / f"{part}.mesh.json").write_text(
            json.dumps(payload or _valid_mesh_payload(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _write_all_p0(self) -> None:
        for part in P0_MODEL_PARTS:
            self._write_mesh(part)

    def test_p0_viewer_mesh_assets_pass_when_contract_fields_exist(self) -> None:
        self._write_all_p0()

        audit = audit_viewer_mesh_assets(repo_root=self.root)

        self.assertEqual(audit["status"], "pass")
        self.assertEqual(audit["contract_version"], "model-quality-gate.v1")
        self.assertEqual(audit["blocking_gate"], "mesh_fit_before_texture_final")
        self.assertTrue(audit["ok"])
        self.assertTrue(audit["mesh_assets_ready"])
        self.assertTrue(audit["texture_lock_allowed"])
        self.assertEqual(audit["missing_required_parts"], [])
        self.assertEqual(audit["reasons"], ["mesh.v1 P0 quality gate passed"])
        self.assertEqual(audit["summary"]["required_pass_count"], 5)
        self.assertEqual(audit["parts"]["helmet"]["body_fit_slot_id"], "helmet")
        self.assertEqual(audit["parts"]["left_shoulder"]["body_fit_slot_id"], "shoulder_l")
        self.assertEqual(audit["parts"]["left_shoulder"]["runtime_part_id"], "left_shoulder")
        self.assertTrue(audit["parts"]["right_shoulder"]["checks"]["body_fit_slot_resolved"])
        self.assertTrue(audit["parts"]["chest"]["checks"]["normals"])
        self.assertTrue(audit["parts"]["chest"]["checks"]["uv_range"])
        self.assertTrue(audit["parts"]["chest"]["checks"]["index_range"])
        self.assertTrue(audit["parts"]["chest"]["checks"]["non_degenerate_triangles"])
        self.assertEqual(audit["parts"]["chest"]["metrics"]["triangle_count"], 1)

    def test_selected_upperarm_mesh_assets_resolve_body_fit_slots(self) -> None:
        for part in ["helmet", "chest", "back", "left_upperarm", "right_upperarm"]:
            self._write_mesh(part)

        audit = audit_viewer_mesh_assets(
            repo_root=self.root,
            required_parts=["helmet", "chest", "back", "left_upperarm", "right_upperarm"],
        )

        self.assertEqual(audit["status"], "pass")
        self.assertEqual(audit["missing_required_parts"], [])
        self.assertEqual(audit["parts"]["left_upperarm"]["body_fit_slot_id"], "upperarm_l")
        self.assertEqual(audit["parts"]["right_upperarm"]["body_fit_slot_id"], "upperarm_r")
        self.assertTrue(audit["parts"]["left_upperarm"]["checks"]["body_fit_slot_resolved"])
        self.assertTrue(audit["parts"]["right_upperarm"]["checks"]["body_fit_slot_resolved"])

    def test_missing_required_p0_part_fails_the_gate(self) -> None:
        for part in P0_MODEL_PARTS:
            if part != "back":
                self._write_mesh(part)

        audit = audit_viewer_mesh_assets(repo_root=self.root)

        self.assertEqual(audit["status"], "fail")
        self.assertFalse(audit["ok"])
        self.assertFalse(audit["mesh_assets_ready"])
        self.assertFalse(audit["texture_lock_allowed"])
        self.assertEqual(audit["missing_required_parts"], ["back"])
        self.assertIn("back: required mesh asset missing", audit["reasons"])
        self.assertEqual(audit["parts"]["back"]["status"], "fail")

    def test_mesh_payload_fails_when_required_contract_fields_are_missing_or_zero(self) -> None:
        missing_fields = _valid_mesh_payload()
        del missing_fields["uv"]
        del missing_fields["indices"]

        zero_bounds = _valid_mesh_payload()
        zero_bounds["bounds"] = {"min": [0, 0, 0], "max": [0, 1, 1]}

        missing_audit = audit_mesh_payload("helmet", missing_fields)
        zero_bounds_audit = audit_mesh_payload("chest", zero_bounds)

        self.assertEqual(missing_audit["status"], "fail")
        self.assertFalse(missing_audit["checks"]["uv"])
        self.assertFalse(missing_audit["checks"]["indices"])
        self.assertIn("helmet: uv missing or invalid", missing_audit["reasons"])
        self.assertIn("helmet: indices missing or invalid", missing_audit["reasons"])

        self.assertEqual(zero_bounds_audit["status"], "fail")
        self.assertTrue(zero_bounds_audit["checks"]["bounds"])
        self.assertTrue(zero_bounds_audit["checks"]["explicit_bounds"])
        self.assertFalse(zero_bounds_audit["checks"]["bounds_non_zero"])
        self.assertIn("chest: bounds must be non-zero on every axis", zero_bounds_audit["reasons"])

    def test_payload_reports_computed_bounds_when_explicit_bounds_are_missing(self) -> None:
        payload = _valid_mesh_payload()
        del payload["bounds"]

        audit = audit_mesh_payload("helmet", payload)

        self.assertEqual(audit["status"], "fail")
        self.assertFalse(audit["checks"]["bounds"])
        self.assertFalse(audit["checks"]["explicit_bounds"])
        self.assertEqual(audit["metrics"]["computed_bounds"]["size"], [1.0, 1.0, 1.0])
        self.assertIn("helmet: bounds missing or invalid", audit["reasons"])

    def test_sidecar_bounds_allow_p0_assets_to_pass_without_rewriting_mesh_json(self) -> None:
        for part in P0_MODEL_PARTS:
            payload = _valid_mesh_payload()
            del payload["bounds"]
            self._write_mesh(part, payload)
        (self.mesh_dir / "mesh-bounds.v1.json").write_text(
            json.dumps(
                {
                    "contract_version": "mesh-bounds.v1",
                    "parts": {
                        part: {"min": [0, 0, 0], "max": [1, 1, 1], "size": [1, 1, 1]}
                        for part in P0_MODEL_PARTS
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        audit = audit_viewer_mesh_assets(repo_root=self.root)

        self.assertEqual(audit["status"], "pass")
        self.assertEqual(audit["bounds_contract_version"], "mesh-bounds.v1")
        self.assertTrue(audit["bounds_file"].endswith("mesh-bounds.v1.json"))
        self.assertEqual(audit["parts"]["helmet"]["metrics"]["bounds_source"], "sidecar")

    def test_ensure_mesh_payload_bounds_attaches_explicit_bounds_from_positions(self) -> None:
        payload = _valid_mesh_payload()
        del payload["bounds"]

        result = ensure_mesh_payload_bounds(payload)

        self.assertIs(result, payload)
        self.assertEqual(
            payload["bounds"],
            {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0], "size": [1.0, 1.0, 1.0]},
        )
        audit = audit_mesh_payload("helmet", payload)
        self.assertEqual(audit["status"], "pass")
        self.assertTrue(audit["checks"]["explicit_bounds"])

    def test_compute_position_bounds_can_round_generated_asset_values(self) -> None:
        bounds = compute_position_bounds([0, 0, 0, 0.333333333, 0.5, 0.75, 1, 1, 1], digits=4)

        self.assertEqual(bounds, {"min": [0, 0, 0], "max": [1, 1, 1], "size": [1, 1, 1]})

    def test_non_required_extra_mesh_with_unknown_body_fit_slot_warns(self) -> None:
        self._write_all_p0()
        self._write_mesh("mystery_panel")

        audit = audit_viewer_mesh_assets(repo_root=self.root, include_extra=True)

        self.assertEqual(audit["status"], "warn")
        self.assertTrue(audit["ok"])
        self.assertEqual(audit["missing_required_parts"], [])
        self.assertEqual(audit["parts"]["mystery_panel"]["status"], "warn")
        self.assertIn("mystery_panel: cannot resolve body-fit slot", audit["reasons"])


if __name__ == "__main__":
    unittest.main()
