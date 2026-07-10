from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "validate_exhibition_release_package.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_exhibition_release_package", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_exhibition_release_package"] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def _write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _minimal_catalog() -> dict:
    return {
        "contract_version": "armor-part-variant-catalog.v1",
        "modules": {
            "helmet": {
                "variants": [
                    {
                        "variant_key": "helmet:demo",
                        "asset_ref": "viewer/assets/armor-parts/helmet/variants/demo/helmet__demo.glb",
                    }
                ]
            }
        },
    }


def _p1_order_manifest(*, runtime_activation_allowed: bool = False) -> dict:
    modules = [
        "left_upperarm",
        "right_upperarm",
        "left_forearm",
        "right_forearm",
        "left_hand",
        "right_hand",
        "left_thigh",
        "right_thigh",
    ]
    lines = [
        ("line_rescue_knight", "rescue"),
        ("line_royal_insect", "guardian"),
        ("line_final_oath", "oath"),
    ]
    family_by_module = {
        module: module.removeprefix("left_").removeprefix("right_")
        for module in modules
    }
    variants = []
    for line_id, prefix in lines:
        for module in modules:
            family = family_by_module[module]
            asset_key = f"{prefix}_{family}"
            stem = f"{module}__{asset_key}"
            base = f"viewer/assets/armor-parts/{module}/variants/{asset_key}"
            entry = {
                "asset_kind": "variant_order",
                "module": module,
                "line_id": line_id,
                "asset_key": asset_key,
                "variant_key": f"{module}:{asset_key}",
                "expected_glb_path": f"{base}/{stem}.glb",
                "expected_sidecar_path": f"{base}/{stem}.modeler.json",
                "expected_source_blend_path": f"{base}/source/{stem}.blend",
                "expected_preview_mesh_path": f"{base}/preview/{stem}.mesh.json",
                "design_intent": f"{line_id} {module} P1 acceptance fixture.",
            }
            if module.startswith("right_"):
                entry["mirror_of"] = f"left_{family}:{asset_key}"
            variants.append(entry)
    return {
        "contract_version": "modeler-variant-order-manifest.v1",
        "order_id": "p1-limb-three-line-variants-2026-05-03",
        "assets_root": "viewer/assets/armor-parts",
        "source_concept_catalog": None,
        "target_modules": modules,
        "required_lines": [
            {"line_id": line_id, "source_concept_ids": ["c02"], "line_label": label, "read": label}
            for line_id, label in lines
        ],
        "acceptance_policy": {
            "required_variants_per_module": 3,
            "runtime_activation_allowed": runtime_activation_allowed,
        },
        "variants": variants,
    }


def _sidecar(
    module: str,
    *,
    bbox: dict[str, float] | None = None,
    target: dict[str, float] | None = None,
    waist_loop_status: str | None = "glb_loop_exported",
) -> str:
    bbox = bbox or {"x": 0.1, "y": 0.1, "z": 0.1}
    target = target or bbox
    payload = {
        "module": module,
        "bbox_m": bbox,
        "target_envelope_m": target,
        "vrm_attachment": {"offset_m": [0.0, 0.0, 0.02]},
        "attachment_offset_target_m": 0.05,
    }
    if module == "waist":
        payload["category"] = "waist"
        if waist_loop_status is not None:
            payload["body_wrap_loop_contract"] = {
                "body_wrap_loop_export_status": waist_loop_status,
            }
    return json.dumps(payload)


def _required_file_content(rel_path: str) -> str:
    if rel_path == "package.json":
        return json.dumps(
            {
                "scripts": {
                    "dev": "python tools/run_henshin.py serve-dashboard --port 8010 --root .",
                    "dev:quest:adb": "powershell -File tools/start_quest_adb_reverse.ps1",
                }
            }
        )
    if rel_path == "viewer/quest-iw-demo/quest-demo.js":
        return "展示用UI 変身スーツ Quest 呼び出し 蒸着粒子 蒸着光跡 THREE.Points THREE.LineSegments THREE.AdditiveBlending updateDepositionEffects"
    if rel_path.startswith("viewer/armor-forge/") or rel_path.startswith("viewer/quest-iw-demo/"):
        return "展示用UI 変身スーツ Quest 呼び出し"
    if rel_path == "docs/modeler-exhibition-readiness-risks-2026-05-04.md":
        return "fidelity_hold front side back 3Q waiver"
    if rel_path == "docs/modeler-triview-30variant-audit-table-2026-05-03.md":
        return "fidelity_hold front side back 3Q"
    if rel_path == "docs/quest-deposition-visual-direction-2026-05-04.md":
        return "Quest deposition particles light trails shine Japanese UI"
    if rel_path == "docs/exhibition-ui-redesign-backlog-2026-05-04.md":
        return "Webでスーツ成立 Questで変身試験 Replayで体験を残す deposition Japanese UI"
    if rel_path == "docs/exhibition-service-mocopi-roadmap-2026-05-04.md":
        return (
            "Required local preflight Optional enhancement preflight "
            "local-pass is prerequisite for visitor operation local-pass cannot be overridden "
            "External PC local baseline Core demo must run without live GCP, internet, provider secrets, or mocopi. "
            "Cloud-only exhibition path before local fallback passes. "
            "PlayCanvas as variant, placement, code, or Replay authority. "
            "service endpoint must pass the same forge, recall, replay, and no-local-path checks "
            "PlayCanvas must consume an exported runtime package snapshot "
            "mocopi cannot promote the visitor path unless the packaged-PC local baseline remains pass "
            "mocopi-GO/DEMO-ONLY/NO-GO/not-included service-pass/fail/not-included "
            "playcanvas-pass/fail/not-included local-pass/fail "
            "fallback confirmed `8010` `5173` USB ADB reverse Replay portability"
        )
    if rel_path == "docs/web-service-phase0-task-breakdown-2026-05-02.md":
        return (
            "Required local preflight Optional enhancement preflight "
            "local-pass is prerequisite for visitor operation local-pass cannot be overridden "
            "External PC local baseline Core demo must run without live GCP, internet, provider secrets, or mocopi. "
            "Cloud-only exhibition path before local fallback passes. "
            "PlayCanvas as variant, placement, code, or Replay authority. "
            "service endpoint must pass the same forge, recall, replay, and no-local-path checks "
            "PlayCanvas must consume an exported runtime package snapshot "
            "playcanvas-pass/fail/not-included service-pass/fail/not-included local-pass/fail "
            "`8010` `5173` Replay portability"
        )
    if rel_path == "docs/quest-mocopi-exhibition-spike-2026-05-04.md":
        return (
            "Required local preflight Optional enhancement preflight "
            "local-pass is prerequisite for visitor operation local-pass cannot be overridden "
            "mocopi cannot promote the visitor path unless the packaged-PC local baseline remains pass "
            "mocopi-GO/DEMO-ONLY/NO-GO/not-included fallback confirmed USB ADB reverse "
            "`8010` `5173` Replay portability"
        )
    if rel_path == "docs/p1-limb-variant-order-acceptance-2026-05-03.md":
        return (
            "24 upperarm forearm hand thigh line_rescue_knight line_royal_insect "
            "line_final_oath runtime_activation_allowed warn_now_block_p1 pass_p1"
        )
    if rel_path == "tools/validate_modeler_variant_order_manifest.py":
        return (REPO_ROOT / rel_path).read_text(encoding="utf-8")
    if rel_path == "docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json":
        return json.dumps(_p1_order_manifest())
    return "x"


def _create_minimal_package(root: Path) -> None:
    for _category, rel_path in validator.REQUIRED_FILES:
        if rel_path == "viewer/assets/armor-parts/variant_catalog.json":
            _write(root / rel_path, json.dumps(_minimal_catalog()))
        else:
            _write(root / rel_path, _required_file_content(rel_path))

    for module in validator.EXPECTED_MODULES:
        base = root / "viewer" / "assets" / "armor-parts" / module
        _write(base / f"{module}.glb")
        _write(base / f"{module}.modeler.json", _sidecar(module))
        _write(base / "preview" / f"{module}.mesh.json", "{}")

    variant_base = root / "viewer" / "assets" / "armor-parts" / "helmet" / "variants" / "demo"
    _write(variant_base / "helmet__demo.glb")
    _write(variant_base / "helmet__demo.modeler.json", _sidecar("helmet"))
    _write(variant_base / "preview" / "helmet__demo.mesh.json", "{}")

    topping_base = (
        root
        / "viewer"
        / "assets"
        / "armor-parts"
        / "helmet"
        / "toppings"
        / "crest"
        / "demo_crest"
    )
    _write(topping_base / "helmet__crest__demo_crest.glb")
    _write(topping_base / "helmet__crest__demo_crest.modeler.json", _sidecar("helmet"))
    _write(topping_base / "preview" / "helmet__crest__demo_crest.mesh.json", "{}")


def test_minimal_package_passes_existence_gate_without_git(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=False,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    assert result["ok"], result["reasons"]
    assert result["status"] == "warn"
    assert result["missing_count"] == 0
    assert result["pattern_gap_count"] == 0
    assert result["untracked_count"] == 0
    assert result["model_quality"]["status"] == "pass"
    assert result["model_quality"]["runtime_release_allowed"] is True
    assert result["model_quality"]["model_delivery_acceptance_status"] == "pass"
    assert result["model_quality"]["fidelity_acceptance_blockers"] == []
    assert result["model_quality"]["micro_dimension_warnings"] == []
    assert result["experience_gates"]["status"] == "pass"
    assert result["p1_acceptance"]["package_gate_status"] == "warn_now_block_p1"
    assert result["p1_acceptance"]["acceptance_complete"] is False
    assert result["p1_acceptance"]["runtime_activation_allowed"] is False


def test_missing_package_paths_and_patterns_are_reported_exactly(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)
    (tmp_path / "viewer" / "assets" / "armor-parts" / "variant_catalog.json").unlink()
    (tmp_path / "viewer" / "assets" / "armor-parts" / "helmet" / "variants" / "demo" / "helmet__demo.glb").unlink()

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=False,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    assert not result["ok"]
    assert {
        "category": "armor",
        "path": "viewer/assets/armor-parts/variant_catalog.json",
        "reason": "required file missing",
    } in result["missing"]
    assert any(
        gap["pattern"] == "viewer/assets/armor-parts/*/variants/*/*.glb"
        and gap["actual_count"] == 0
        and gap["missing_count"] == 1
        for gap in result["pattern_gaps"]
    )


def test_git_tracking_gate_reports_untracked_critical_files(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)
    subprocess.run(["git", "-C", str(tmp_path), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "--all"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "rm", "--cached", "viewer/assets/armor-parts/variant_catalog.json"],
        check=True,
        capture_output=True,
    )

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=True,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    assert not result["ok"]
    assert result["git_tracking"]["checked"] is True
    assert any(
        entry["path"] == "viewer/assets/armor-parts/variant_catalog.json"
        and "armor" in entry["categories"]
        for entry in result["untracked"]
    )


def test_catalog_asset_refs_report_missing_companion_paths(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)
    (tmp_path / "viewer" / "assets" / "armor-parts" / "helmet" / "variants" / "demo" / "preview" / "helmet__demo.mesh.json").unlink()

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=False,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    assert not result["ok"]
    assert any(
        entry["category"] == "armor_catalog_ref"
        and entry["path"] == "viewer/assets/armor-parts/helmet/variants/demo/preview/helmet__demo.mesh.json"
        for entry in result["missing"]
    )


def test_model_quality_outputs_concrete_per_part_micro_adjustments(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)
    chest = tmp_path / "viewer" / "assets" / "armor-parts" / "chest" / "chest.modeler.json"
    chest.write_text(
        _sidecar(
            "chest",
            bbox={"x": 0.62, "y": 0.50, "z": 0.142398},
            target={"x": 0.6392, "y": 0.4992, "z": 0.1632},
        ),
        encoding="utf-8",
    )

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=False,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    assert result["ok"]
    assert result["status"] == "warn"
    assert result["model_quality_warning_count"] == 1
    assert result["model_quality"]["runtime_release_allowed"] is True
    assert result["model_quality"]["model_delivery_acceptance_status"] == "blocked"
    assert result["model_quality"]["micro_dimension_warning_count"] == 1
    assert result["model_quality"]["fidelity_acceptance_blockers"] == []
    chest_report = next(part for part in result["model_quality"]["parts"] if part["module"] == "chest")
    assert chest_report["status"] == "warn"
    assert chest_report["runtime_release_allowed"] is True
    assert chest_report["model_delivery_acceptance_status"] == "blocked"
    assert chest_report["model_quality_warning_type"] == "micro_dimension"
    assert chest_report["size_adjustments"][0]["axis"] == "z"
    assert chest_report["size_adjustments"][0]["minimum_change_to_pass_m"] == 0.004482
    assert "side and 3Q volume" in chest_report["position_adjustment"]["summary"]
    assert "V core" in chest_report["design_directive"]


def test_model_quality_separates_runtime_allowed_warnings_from_fidelity_blockers(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)
    warned_parts = {
        "chest": (
            {"x": 0.62, "y": 0.50, "z": 0.142398},
            {"x": 0.6392, "y": 0.4992, "z": 0.1632},
        ),
        "waist": (
            {"x": 0.440351, "y": 0.156788, "z": 0.1900},
            {"x": 0.4896, "y": 0.1716, "z": 0.1904},
        ),
        "left_upperarm": (
            {"x": 0.0963, "y": 0.22, "z": 0.096},
            {"x": 0.1088, "y": 0.22, "z": 0.096},
        ),
        "right_upperarm": (
            {"x": 0.0963, "y": 0.22, "z": 0.096},
            {"x": 0.1088, "y": 0.22, "z": 0.096},
        ),
        "left_shin": (
            {"x": 0.1017, "y": 0.4105, "z": 0.114},
            {"x": 0.1156, "y": 0.3956, "z": 0.1156},
        ),
        "right_shin": (
            {"x": 0.1017, "y": 0.4105, "z": 0.114},
            {"x": 0.1156, "y": 0.3956, "z": 0.1156},
        ),
    }
    for module, (bbox, target) in warned_parts.items():
        sidecar = tmp_path / "viewer" / "assets" / "armor-parts" / module / f"{module}.modeler.json"
        sidecar.write_text(
            _sidecar(module, bbox=bbox, target=target, waist_loop_status=None),
            encoding="utf-8",
        )

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=False,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    assert result["ok"], result["reasons"]
    model_quality = result["model_quality"]
    assert model_quality["status"] == "warn"
    assert model_quality["runtime_release_allowed"] is True
    assert model_quality["model_delivery_acceptance_status"] == "blocked"
    assert result["model_quality_warning_count"] == 6
    assert model_quality["micro_dimension_warning_count"] == 6
    assert {warning["module"] for warning in model_quality["micro_dimension_warnings"]} == set(warned_parts)
    waist_micro_warning = next(
        warning for warning in model_quality["micro_dimension_warnings"] if warning["module"] == "waist"
    )
    assert waist_micro_warning["warning_type"] == "micro_dimension"
    assert waist_micro_warning["runtime_release_allowed"] is True
    assert waist_micro_warning["package_gate_status"] == "warn_runtime_allowed_block_model_delivery"
    assert model_quality["fidelity_acceptance_blocker_count"] == 1
    blocker = model_quality["fidelity_acceptance_blockers"][0]
    assert blocker["module"] == "waist"
    assert blocker["warning_type"] == "fidelity_acceptance_blocker"
    assert blocker["phase"] == "P1"
    assert blocker["runtime_release_allowed"] is True
    assert blocker["package_gate_status"] == "warn_now_block_p1"
    assert blocker["body_wrap_loop_export_status"] == "export_status_not_declared"
    assert "closed wearable-loop proof" in blocker["distinction"]
    assert not any("waist_body_wrap_loop_not_exported" in reason for reason in result["reasons"])


def test_experience_gates_warn_without_japanese_ui_or_fidelity_docs(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)
    _write(tmp_path / "viewer" / "armor-forge" / "index.html", "English demo UI")
    _write(tmp_path / "viewer" / "armor-forge" / "forge.js", "console.log('forge')")
    _write(tmp_path / "viewer" / "quest-iw-demo" / "index.html", "Quest UI")
    _write(tmp_path / "viewer" / "quest-iw-demo" / "quest-demo.js", "console.log('quest')")
    _write(tmp_path / "docs" / "modeler-exhibition-readiness-risks-2026-05-04.md", "held assets")
    _write(tmp_path / "docs" / "modeler-triview-30variant-audit-table-2026-05-03.md", "held assets")

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=False,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    assert result["ok"]
    assert result["status"] == "warn"
    gate_by_name = {gate["gate"]: gate for gate in result["experience_gates"]["gates"]}
    assert gate_by_name["japanese_ui"]["status"] == "warn"
    assert gate_by_name["quest_deposition_visuals"]["status"] == "warn"
    assert gate_by_name["tri_view_fidelity_hold_documentation"]["status"] == "warn"
    assert any("Japanese UI gate" in warning for warning in result["warnings"])
    assert any("Quest deposition visual gate" in warning for warning in result["warnings"])
    assert any("Tri-view/fidelity_hold doc gate" in warning for warning in result["warnings"])


def test_p1_limb_baseline_is_a_required_package_file(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)
    (tmp_path / "docs" / "modeler-deliveries" / "p1-limb-three-line-variants-2026-05-03.order-manifest.json").unlink()

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=False,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    assert not result["ok"]
    assert any(
        entry["path"] == "docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json"
        and entry["category"] == "operator_docs"
        for entry in result["missing"]
    )


def test_demo_env_example_is_a_required_package_file(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)
    (tmp_path / ".env.demo.example").unlink()

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=False,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    assert not result["ok"]
    assert any(
        entry["path"] == ".env.demo.example" and entry["category"] == "runtime"
        for entry in result["missing"]
    )


def test_p1_limb_acceptance_incomplete_warns_without_failing_package(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=False,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    assert result["ok"], result["reasons"]
    assert result["status"] == "warn"
    assert result["p1_acceptance"]["validator_ok"] is True
    assert result["p1_acceptance"]["package_gate_status"] == "warn_now_block_p1"
    assert result["p1_acceptance"]["runtime_activation_allowed"] is False
    assert result["p1_acceptance"]["runtime_activation_label"] == (
        "runtime_activation_blocked_by_order_manifest"
    )
    assert any("P1 limb acceptance incomplete" in warning for warning in result["warnings"])


def test_p1_limb_manifest_runtime_activation_violation_fails_release(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)
    _write(
        tmp_path / "docs" / "modeler-deliveries" / "p1-limb-three-line-variants-2026-05-03.order-manifest.json",
        json.dumps(_p1_order_manifest(runtime_activation_allowed=True)),
    )

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=False,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    assert not result["ok"]
    assert result["p1_acceptance"]["runtime_activation_allowed"] is False
    assert any("runtime_activation_allowed" in reason for reason in result["reasons"])


def test_p1_limb_manifest_unreadable_fails_release_with_reason(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)
    _write(
        tmp_path / "docs" / "modeler-deliveries" / "p1-limb-three-line-variants-2026-05-03.order-manifest.json",
        "{not-json",
    )

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=False,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    assert not result["ok"]
    assert result["p1_acceptance"]["package_gate_status"] == "warn_now_block_p1"
    assert any("manifest: invalid JSON" in reason for reason in result["reasons"])


def test_local_optional_lane_separation_gate_warns_when_roadmap_terms_are_missing(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)
    for rel_path in (
        "docs/exhibition-service-mocopi-roadmap-2026-05-04.md",
        "docs/exhibition-pc-release-package-manifest-2026-05-04.md",
        "docs/exhibition-pc-runbook-2026-05-04.md",
        "docs/exhibition-day-one-page-checklist-2026-05-04.md",
        "docs/web-service-phase0-task-breakdown-2026-05-02.md",
        "docs/quest-mocopi-exhibition-spike-2026-05-04.md",
    ):
        _write(tmp_path / rel_path, "cloud demo first")

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=False,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    assert result["ok"]
    gate_by_name = {gate["gate"]: gate for gate in result["experience_gates"]["gates"]}
    gate = gate_by_name["local_required_optional_enhancement_separation"]
    assert gate["status"] == "warn"
    assert "external-PC local baseline schedule" in gate["missing_evidence_terms"]
    assert any("Local/optional lane separation gate" in warning for warning in result["warnings"])


def test_local_optional_lane_separation_gate_reports_required_and_optional_labels(tmp_path: Path) -> None:
    _create_minimal_package(tmp_path)

    result = validator.validate_release_package(
        tmp_path,
        check_git_tracking=False,
        expected_variant_glbs=1,
        expected_topping_glbs=1,
    )

    gate_by_name = {gate["gate"]: gate for gate in result["experience_gates"]["gates"]}
    gate = gate_by_name["local_required_optional_enhancement_separation"]
    assert gate["required_lane"] == "external_pc_local"
    assert gate["required_operator_labels"] == ["local-pass", "local-fail"]
    assert gate["optional_operator_labels"]["gcp_service"] == [
        "service-pass",
        "service-fail",
        "not-included",
    ]
    assert gate["optional_operator_labels"]["playcanvas"] == [
        "playcanvas-pass",
        "playcanvas-fail",
        "not-included",
    ]
    assert gate["optional_operator_labels"]["mocopi"] == [
        "mocopi-GO",
        "DEMO-ONLY",
        "NO-GO",
        "not-included",
    ]


def test_cli_json_report_uses_expected_counts(tmp_path: Path, capsys) -> None:
    _create_minimal_package(tmp_path)

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--skip-git-tracking",
            "--expected-variant-glbs",
            "1",
            "--expected-topping-glbs",
            "1",
            "--report-json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert payload["ok"]
    assert payload["tracked_candidate_count"] > 0
