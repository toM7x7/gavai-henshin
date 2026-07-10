from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "validate_modeler_delivery_manifest.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_modeler_delivery_manifest", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sample_manifest() -> dict:
    return json.loads((REPO_ROOT / "examples" / "modeler_delivery_manifest.sample.json").read_text(encoding="utf-8"))


def _write_manifest(tmp_path: Path, manifest: dict) -> Path:
    path = tmp_path / "delivery.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_committed_sample_manifest_validates() -> None:
    validator = _load_validator()
    result = validator.validate_delivery_manifest(REPO_ROOT / "examples" / "modeler_delivery_manifest.sample.json")
    assert result["status"] in {"pass", "warn"}, result
    assert result["ok"], result
    assert result["asset_count"] == 1
    assert not result["reasons"]


def test_variant_key_must_match_module_and_asset_key(tmp_path: Path) -> None:
    validator = _load_validator()
    manifest = _sample_manifest()
    manifest["assets"][0]["variant_key"] = "helmet:wrong"
    path = _write_manifest(tmp_path, manifest)

    result = validator.validate_delivery_manifest(path)

    assert not result["ok"]
    assert any("variant_key: expected helmet:sleek" in reason for reason in result["reasons"])


def test_manifest_cannot_activate_runtime_directly(tmp_path: Path) -> None:
    validator = _load_validator()
    manifest = _sample_manifest()
    manifest["assets"][0]["activate_runtime"] = True
    path = _write_manifest(tmp_path, manifest)

    result = validator.validate_delivery_manifest(path)

    assert not result["ok"]
    assert any("activate_runtime" in reason for reason in result["reasons"])


def test_missing_glb_is_a_failure(tmp_path: Path) -> None:
    validator = _load_validator()
    manifest = _sample_manifest()
    asset = manifest["assets"][0]
    asset["asset_key"] = "missing"
    asset["variant_key"] = "helmet:missing"
    asset["glb_path"] = "viewer/assets/armor-parts/helmet/variants/missing/helmet__missing.glb"
    asset["sidecar_path"] = "viewer/assets/armor-parts/helmet/variants/missing/helmet__missing.modeler.json"
    asset["source_blend_path"] = "viewer/assets/armor-parts/helmet/variants/missing/source/helmet__missing.blend"
    path = _write_manifest(tmp_path, manifest)

    result = validator.validate_delivery_manifest(path)

    assert not result["ok"]
    assert any("file missing" in reason for reason in result["reasons"])


def test_absolute_paths_are_rejected(tmp_path: Path) -> None:
    validator = _load_validator()
    manifest = copy.deepcopy(_sample_manifest())
    manifest["assets"][0]["glb_path"] = str(REPO_ROOT / "viewer/assets/armor-parts/helmet/helmet.glb")
    path = _write_manifest(tmp_path, manifest)

    result = validator.validate_delivery_manifest(path)

    assert not result["ok"]
    assert any("repo-relative" in reason for reason in result["reasons"])
