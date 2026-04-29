"""Aggregate GLB armor sidecars into a modeler-facing fit handoff report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from henshin.armor_fit_contract import ARMOR_SLOT_SPECS, MAJOR_ARMOR_SLOTS, normalize_slot_id  # noqa: E402
from henshin import modeler_blueprints as blueprints  # noqa: E402


DEFAULT_ARMOR_PARTS_DIR = Path("viewer/assets/armor-parts")
AUDIT_CONTRACT_VERSION = "armor-part-fit-handoff-audit.v1"
DEFAULT_BBOX_TOLERANCE = 0.15
AXES = ("x", "y", "z")


def collect_fit_handoff_audit(
    root: str | Path = DEFAULT_ARMOR_PARTS_DIR,
    *,
    bbox_tolerance: float = DEFAULT_BBOX_TOLERANCE,
) -> dict[str, Any]:
    """Read modeler sidecars and compare them with blueprint/body-fit contracts."""

    armor_root = Path(root)
    expected_modules = expected_runtime_modules()
    parts = [
        _audit_part(armor_root, module, bbox_tolerance=bbox_tolerance)
        for module in expected_modules
    ]
    material_zone_counts: dict[str, int] = {}
    for part in parts:
        for zone in part.get("material_zones", []):
            material_zone_counts[zone] = material_zone_counts.get(zone, 0) + 1

    missing_modules = [part["module"] for part in parts if part["status"] == "missing"]
    request_parts = [part for part in parts if part.get("modeler_requests")]
    status = "fail" if missing_modules else "warn" if request_parts else "pass"
    return {
        "contract_version": AUDIT_CONTRACT_VERSION,
        "source_contracts": {
            "blueprint": blueprints.BLUEPRINT_CONTRACT_VERSION,
            "body_fit": "armor-body-fit.v1",
            "sidecar": "modeler-part-sidecar.v1",
        },
        "root": str(armor_root),
        "bbox_tolerance_pct": round(bbox_tolerance * 100, 3),
        "status": status,
        "ok": not missing_modules,
        "part_count": len([part for part in parts if part["status"] != "missing"]),
        "expected_part_count": len(expected_modules),
        "missing_modules": missing_modules,
        "total_triangles": sum(part.get("triangle_count") or 0 for part in parts),
        "material_zone_counts": dict(sorted(material_zone_counts.items())),
        "parts": parts,
    }


def expected_runtime_modules() -> list[str]:
    return [ARMOR_SLOT_SPECS[slot].runtime_part_id for slot in MAJOR_ARMOR_SLOTS]


def render_modeler_fix_requests_markdown(audit: dict[str, Any]) -> str:
    """Render a compact table that can be sent back to modelers."""

    lines = [
        "# 装甲パーツ フィット監査・モデラー修正依頼",
        "",
        "入力: `viewer/assets/armor-parts/*/*.modeler.json`",
        "",
        "参照した契約:",
        "",
        "- `henshin.modeler_blueprints`: 目標bboxとtriangle予算",
        "- `henshin.armor_fit_contract`: body anchorと装着スロット順",
        "- `viewer/assets/armor-parts/<module>/<module>.modeler.json`: 納品済みメトリクス",
        "",
        "要約:",
        "",
        f"- 判定: `{audit['status']}`",
        f"- 認識パーツ: {audit['part_count']} / {audit['expected_part_count']}",
        f"- 総三角形数: {audit['total_triangles']}",
        f"- material_zones集計: {_zone_counts_label(audit.get('material_zone_counts', {}))}",
        "- 見方: `修正依頼` 欄だけを順に潰せば、次の受け入れチェックに進めます。",
        "",
        "| module | anchor | bbox 実測 -> 目標 m | 差分 | triangles | material_zones | 修正依頼 |",
        "|---|---|---|---|---:|---|---|",
    ]

    for part in audit["parts"]:
        request = "<br>".join(part.get("modeler_requests") or ["OK: 現状維持。レビュー画像と干渉確認の根拠だけ添えてください。"])
        lines.append(
            "| {module} | {anchor} | {bbox} -> {target} | {delta} | {triangles} | {zones} | {request} |".format(
                module=part["module"],
                anchor=_escape_md(part.get("primary_bone") or "missing"),
                bbox=_vector_label(part.get("bbox_m")),
                target=_vector_label(part.get("target_bbox_m")),
                delta=_escape_md(_delta_label(part.get("bbox_delta_pct"))),
                triangles=part.get("triangle_count") or 0,
                zones=_escape_md(", ".join(part.get("material_zones") or ["missing"])),
                request=_escape_md(request),
            )
        )

    lines.extend(
        [
            "",
            "再生成コマンド:",
            "",
            "```bash",
            "python tools/audit_armor_part_fit_handoff.py --format markdown --output docs/armor-part-fit-modeler-requests.md",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _audit_part(root: Path, module: str, *, bbox_tolerance: float) -> dict[str, Any]:
    sidecar_path = root / module / f"{module}.modeler.json"
    body_fit_slot_id = normalize_slot_id(module)
    body_fit_spec = ARMOR_SLOT_SPECS[body_fit_slot_id]
    category = getattr(blueprints, "_CATEGORY_BY_MODULE").get(module, "armor")
    target_bbox = _reference_target_dimensions(module)
    triangle_budget = getattr(blueprints, "_TRIANGLE_BUDGET_BY_CATEGORY").get(category, 1200)
    base = {
        "module": module,
        "body_fit_slot_id": body_fit_slot_id,
        "body_anchor_expected": body_fit_spec.body_anchor,
        "category": category,
        "triangle_budget": triangle_budget,
        "target_bbox_m": target_bbox,
        "sidecar_path": sidecar_path.as_posix(),
    }
    if not sidecar_path.exists():
        return {
            **base,
            "status": "missing",
            "modeler_requests": [f"sidecarを納品してください: {sidecar_path.as_posix()}"],
        }

    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    bbox = _bbox_size(payload.get("bbox_m"))
    sidecar_target = _target_bbox(payload.get("target_envelope_m"))
    if sidecar_target is not None:
        target_bbox = sidecar_target
    triangle_count = payload.get("triangle_count", payload.get("triangles"))
    material_zones = payload.get("material_zones") if isinstance(payload.get("material_zones"), list) else []
    attachment = payload.get("vrm_attachment") if isinstance(payload.get("vrm_attachment"), dict) else {}
    primary_bone = attachment.get("primary_bone")
    bbox_delta = _bbox_delta_pct(bbox, target_bbox)
    bbox_axes = [
        axis
        for axis, delta in (bbox_delta or {}).items()
        if abs(delta) > bbox_tolerance * 100
    ]
    qa_warnings = _qa_flags(payload.get("qa_self_report"), flag="warn")
    qa_failures = _qa_flags(payload.get("qa_self_report"), flag="fail")

    requests = _modeler_requests(
        module=module,
        bbox=bbox,
        target_bbox=target_bbox,
        bbox_delta=bbox_delta,
        bbox_axes=bbox_axes,
        triangle_count=triangle_count,
        triangle_budget=triangle_budget,
        material_zones=material_zones,
        primary_bone=primary_bone,
        expected_bone=body_fit_spec.body_anchor,
        qa_warnings=qa_warnings,
        qa_failures=qa_failures,
    )
    has_blocking_metadata_gap = (
        bbox is None
        or not isinstance(triangle_count, int)
        or triangle_count <= 0
        or not material_zones
        or primary_bone != body_fit_spec.body_anchor
    )
    status = "fail" if qa_failures or has_blocking_metadata_gap else "warn" if requests else "pass"
    return {
        **base,
        "status": status,
        "part_id": payload.get("part_id"),
        "primary_bone": primary_bone,
        "anchor_matches_body_fit": primary_bone == body_fit_spec.body_anchor,
        "bbox_m": bbox,
        "target_bbox_m": target_bbox,
        "bbox_delta_pct": bbox_delta,
        "bbox_outside_tolerance_axes": bbox_axes,
        "triangle_count": triangle_count,
        "triangle_budget": triangle_budget,
        "material_zones": material_zones,
        "qa_warnings": qa_warnings,
        "qa_failures": qa_failures,
        "modeler_requests": requests,
    }


def _modeler_requests(
    *,
    module: str,
    bbox: dict[str, float] | None,
    target_bbox: dict[str, float],
    bbox_delta: dict[str, float] | None,
    bbox_axes: list[str],
    triangle_count: Any,
    triangle_budget: int,
    material_zones: list[Any],
    primary_bone: Any,
    expected_bone: str,
    qa_warnings: list[str],
    qa_failures: list[str],
) -> list[str]:
    requests: list[str] = []
    if bbox is None:
        requests.append("`bbox_m` に正の x/y/z メートル値を入れてください。")
    elif bbox_delta and bbox_axes:
        requests.append(
            "`authoring_target_m` に近づくようbboxを調整してください: "
            + "; ".join(
                f"{axis} {_signed_pct(bbox_delta[axis])} ({bbox[axis]:.4f} -> {target_bbox[axis]:.4f}m)"
                for axis in bbox_axes
            )
            + "."
        )

    if not isinstance(triangle_count, int) or triangle_count <= 0:
        requests.append("`triangle_count` を正の整数で記入してください。")
    elif triangle_count > triangle_budget:
        requests.append(f"trianglesを {triangle_budget} 以下に減らしてください: {module} は現在 {triangle_count} です。")

    if not material_zones:
        requests.append("`material_zones` を宣言し、少なくとも `base_surface` を入れてください。")
    elif "base_surface" not in material_zones:
        requests.append("`material_zones` に `base_surface` を追加してください。")

    if primary_bone != expected_bone:
        requests.append(f"`vrm_attachment.primary_bone` を body-fit anchor `{expected_bone}` に合わせてください。")

    if qa_failures:
        requests.append("sidecar QAのfailを直してください: " + ", ".join(qa_failures) + ".")
    elif qa_warnings:
        requests.append("QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: " + ", ".join(qa_warnings) + ".")
    return requests


def _reference_target_dimensions(module: str) -> dict[str, float]:
    target = getattr(blueprints, "_reference_target_dimensions")(module)
    return {axis: float(target[axis]) for axis in AXES}


def _bbox_size(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    size = value.get("size") or value.get("dimensions")
    if _number_list(size, expected_len=3):
        return {axis: float(size[index]) for index, axis in enumerate(AXES)}
    xyz = [value.get(axis) for axis in AXES]
    if _number_list(xyz, expected_len=3):
        return {axis: float(xyz[index]) for index, axis in enumerate(AXES)}
    return None


def _target_bbox(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    xyz = [value.get(axis) for axis in AXES]
    if _number_list(xyz, expected_len=3):
        return {axis: float(xyz[index]) for index, axis in enumerate(AXES)}
    return None


def _bbox_delta_pct(bbox: dict[str, float] | None, target: dict[str, float]) -> dict[str, float] | None:
    if bbox is None:
        return None
    result = {}
    for axis in AXES:
        target_value = target[axis]
        result[axis] = round(((bbox[axis] - target_value) / target_value) * 100, 1) if target_value else 0.0
    return result


def _qa_flags(value: Any, *, flag: str) -> list[str]:
    if not isinstance(value, dict):
        return []
    return [str(key) for key, status in value.items() if status == flag]


def _number_list(value: Any, *, expected_len: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == expected_len
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    )


def _zone_counts_label(value: dict[str, int]) -> str:
    if not value:
        return "none"
    return ", ".join(f"{zone}={count}" for zone, count in sorted(value.items()))


def _vector_label(value: dict[str, float] | None) -> str:
    if value is None:
        return "missing"
    return "/".join(f"{value[axis]:.4f}" for axis in AXES)


def _delta_label(value: dict[str, float] | None) -> str:
    if value is None:
        return "missing"
    return ", ".join(f"{axis} {_signed_pct(value[axis])}" for axis in AXES)


def _signed_pct(value: float) -> str:
    return f"{value:+.1f}%"


def _escape_md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def write_output(text: str, output: str | Path | None) -> None:
    if output is None:
        print(text)
        return
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ARMOR_PARTS_DIR), help="armor-parts directory")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", help="optional output path")
    parser.add_argument(
        "--bbox-tolerance",
        type=float,
        default=DEFAULT_BBOX_TOLERANCE,
        help="allowed absolute bbox delta ratio before a resize request is emitted",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    audit = collect_fit_handoff_audit(args.root, bbox_tolerance=args.bbox_tolerance)
    if args.format == "json":
        text = json.dumps(audit, ensure_ascii=False, indent=2) + "\n"
    else:
        text = render_modeler_fix_requests_markdown(audit)
    write_output(text, args.output)
    return 0 if audit["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
