"""Export per-part model fit adjustment tasks from the Web GLB smoke report.

The smoke gate already tells us whether the packaged GLBs load. This helper
turns bbox warnings into modeler/operator-facing micro-adjustment tasks:
which axis is out, how many millimeters are needed to re-enter the pass band,
and what tri-view proof should be captured before exhibition use.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.smoke_web_glb_load import smoke_check_web_glb_load  # noqa: E402


MM = 1000.0
CONTRACT_VERSION = "modeler-fit-adjustments.v0.2"
ROUTE_LORE = "Webでスーツ成立、Questで変身試験、Replayで体験を残す"

DISPLAY_NAMES = {
    "chest": "胸部装甲",
    "waist": "ベルト",
    "left_upperarm": "左上腕",
    "right_upperarm": "右上腕",
    "left_shin": "左すね",
    "right_shin": "右すね",
}

FIDELITY_HOLD_VARIANTS = {
    "chest": ["chest:rescue_wrap", "chest:emerald_v_core", "chest:oath_core_shell"],
    "waist": ["waist:rescue_driver", "waist:guardian_buckle", "waist:oath_driver_ring"],
    "left_shin": ["left_shin:rescue_stream", "left_shin:guardian_ridge", "left_shin:oath_glow_guard"],
    "right_shin": ["right_shin:rescue_stream", "right_shin:guardian_ridge", "right_shin:oath_glow_guard"],
}

PAIR_GROUPS = {
    "left_upperarm": "upperarm_pair",
    "right_upperarm": "upperarm_pair",
    "left_shin": "shin_pair",
    "right_shin": "shin_pair",
}

PLACEMENT_NUDGES = {
    "chest": [{"axis": "z", "max_mm": 2.0, "direction": "forward", "when": "only if added depth reads sunken"}],
    "waist": [{"axis": "y", "max_mm": -1.0, "direction": "down", "when": "only if the belt floats from the body"}],
    "left_upperarm": [
        {"axis": "x", "max_mm": 2.0, "direction": "outward", "when": "only if paired widening clips the shoulder"}
    ],
    "right_upperarm": [
        {"axis": "x", "max_mm": -2.0, "direction": "outward", "when": "only if paired widening clips the shoulder"}
    ],
    "left_shin": [
        {"axis": "x", "max_mm": 2.0, "direction": "outward", "when": "only if shin/boot step becomes visible"}
    ],
    "right_shin": [
        {"axis": "x", "max_mm": -2.0, "direction": "outward", "when": "only if shin/boot step becomes visible"}
    ],
}

ROUTE_GATES = {
    "chest": {
        "web": "Suit Forge first-read: core/V shape must sell the suit identity from front and 3Q.",
        "quest": "Henshin Trial: torso depth must stay body-relative without arm/waist collision.",
        "replay": "Replay Archive: side/back evidence must show the chest and back unit as one suit, not a flat front decal.",
    },
    "waist": {
        "web": "Suit Forge first-read: belt must bridge torso and legs without a narrow unfinished waist read.",
        "quest": "Henshin Trial: belt width/height must keep hip motion and crouch clearance believable.",
        "replay": "Replay Archive: front/3Q capture must not show visible floating or asymmetry.",
    },
    "left_upperarm": {
        "web": "Suit Forge first-read: arm line must not collapse between shoulder and forearm.",
        "quest": "Henshin Trial: shoulder and elbow clearance must survive controller-scale movement.",
        "replay": "Replay Archive: paired arms must remain mirrored enough for recorded poses.",
    },
    "right_upperarm": {
        "web": "Suit Forge first-read: arm line must not collapse between shoulder and forearm.",
        "quest": "Henshin Trial: shoulder and elbow clearance must survive controller-scale movement.",
        "replay": "Replay Archive: paired arms must remain mirrored enough for recorded poses.",
    },
    "left_shin": {
        "web": "Suit Forge first-read: shin-to-boot line must ground the full-body silhouette.",
        "quest": "Henshin Trial: lower-leg width must not break knee/boot motion or foot contact.",
        "replay": "Replay Archive: front and boot-side proof must keep the stance strong in recorded evidence.",
    },
    "right_shin": {
        "web": "Suit Forge first-read: shin-to-boot line must ground the full-body silhouette.",
        "quest": "Henshin Trial: lower-leg width must not break knee/boot motion or foot contact.",
        "replay": "Replay Archive: front and boot-side proof must keep the stance strong in recorded evidence.",
    },
}

EVIDENCE_REQUIRED = {
    "chest": ["full_front", "side", "3q", "torso_closeup", "back_interference_note"],
    "waist": ["full_front", "side", "3q", "back_symmetry"],
    "left_upperarm": ["paired_front", "side_elbow_clearance", "back_shoulder_gap"],
    "right_upperarm": ["paired_front", "side_elbow_clearance", "back_shoulder_gap"],
    "left_shin": ["paired_front", "side", "boot_closeup_side", "back_symmetry"],
    "right_shin": ["paired_front", "side", "boot_closeup_side", "back_symmetry"],
}

AXIS_LABELS = {
    "x": "横幅",
    "y": "高さ",
    "z": "奥行き",
}

TRIVIEW_PROOF = {
    "chest": "正面で胸コアの幅、側面/3Qで厚み、背面で背中ユニットとの干渉なしを確認",
    "waist": "正面で腰ベルトの横幅、側面で腹/背中との浮き、背面で左右対称を確認",
    "left_upperarm": "正面で肩から上腕の連続、側面で肘可動域、背面で肩装甲との隙間を確認",
    "right_upperarm": "正面で肩から上腕の連続、側面で肘可動域、背面で肩装甲との隙間を確認",
    "left_shin": "正面でブーツからすねの連続、側面で膝下の厚み、背面で左右対称を確認",
    "right_shin": "正面でブーツからすねの連続、側面で膝下の厚み、背面で左右対称を確認",
}

POSITION_HINTS = {
    "chest": "厚みを前後へ配分。見た目が沈む場合は runtime placement の z を +2mm まで前へ寄せる。",
    "waist": "左右へ均等に広げる。中心位置は維持し、腰から浮く場合だけ y を -1mm まで下げる。",
    "left_upperarm": "左右ペア同量で横幅を増やす。肩に食い込む場合は左上腕を x +2mm まで外側へ寄せる。",
    "right_upperarm": "左右ペア同量で横幅を増やす。肩に食い込む場合は右上腕を x -2mm まで外側へ寄せる。",
    "left_shin": "左右ペア同量で横幅を増やす。ブーツと段差が出る場合は左すねを x +2mm まで外側へ寄せる。",
    "right_shin": "左右ペア同量で横幅を増やす。ブーツと段差が出る場合は右すねを x -2mm まで外側へ寄せる。",
}

DESIGN_HINTS = {
    "chest": "発光コアとVラインを太らせ、正面の主役感と側面の厚みを両立する。",
    "waist": "ベルト端の情報量を増やし、脚への接続が細く見えないようにする。",
    "left_upperarm": "肩から前腕まで線が途切れない外装リブを追加する。",
    "right_upperarm": "肩から前腕まで線が途切れない外装リブを追加する。",
    "left_shin": "膝下からブーツへ流れる縦ラインを太くし、正面で足元の強さを出す。",
    "right_shin": "膝下からブーツへ流れる縦ラインを太くし、正面で足元の強さを出す。",
}


def _round_mm(value_m: float) -> float:
    return round(value_m * MM, 1)


def _recommended_delta_m(actual_m: float, target_m: float, minimum_to_pass_m: float) -> float:
    if target_m <= actual_m:
        return 0.0
    full_gap = target_m - actual_m
    buffered = max(minimum_to_pass_m + 0.0015, minimum_to_pass_m * 1.35)
    return min(full_gap, buffered)


def fit_adjustments_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    adjustments: list[dict[str, Any]] = []
    for warning in report.get("bbox_warning_summary", []):
        module = str(warning.get("module", ""))
        actual_bbox = warning.get("actual_bbox_m") or {}
        target_bbox = warning.get("target_bbox_m") or {}
        axis_acceptance = warning.get("axis_acceptance") or {}
        axes = list(warning.get("axes") or [])
        size_tasks = []
        for axis in axes:
            acceptance = axis_acceptance.get(axis) or {}
            actual_m = float(acceptance.get("actual_m", actual_bbox.get(axis, 0.0)) or 0.0)
            target_m = float(acceptance.get("target_m", target_bbox.get(axis, 0.0)) or 0.0)
            minimum_to_pass_m = float(acceptance.get("minimum_change_to_pass_m", 0.0) or 0.0)
            recommended_delta_m = _recommended_delta_m(actual_m, target_m, minimum_to_pass_m)
            size_tasks.append(
                {
                    "axis": axis,
                    "axis_label": AXIS_LABELS.get(axis, axis),
                    "actual_mm": _round_mm(actual_m),
                    "target_mm": _round_mm(target_m),
                    "minimum_to_pass_mm": _round_mm(minimum_to_pass_m),
                    "pass_min_mm": _round_mm(float(acceptance.get("pass_min_m", 0.0) or 0.0)),
                    "pass_max_mm": _round_mm(float(acceptance.get("pass_max_m", 0.0) or 0.0)),
                    "recommended_demo_delta_mm": _round_mm(recommended_delta_m),
                    "recommended_demo_target_mm": _round_mm(actual_m + recommended_delta_m),
                    "target_delta_mm": _round_mm(max(0.0, target_m - actual_m)),
                    "axis_scale_factor": round((actual_m + recommended_delta_m) / actual_m, 4)
                    if actual_m
                    else 1.0,
                }
            )
        adjustments.append(
            {
                "module": module,
                "display_name": DISPLAY_NAMES.get(module, module),
                "priority": "P0",
                "adjustment_contract": CONTRACT_VERSION,
                "status": warning.get("status", "warn"),
                "max_abs_delta_pct": warning.get("max_abs_delta_pct"),
                "pair_group": PAIR_GROUPS.get(module),
                "affected_fidelity_hold_variants": FIDELITY_HOLD_VARIANTS.get(module, []),
                "fidelity_hold_relation": "direct_variant_scope"
                if module in FIDELITY_HOLD_VARIANTS
                else "base_fit_rule_for_missing_or_future_line_variants",
                "size_tasks": size_tasks,
                "placement_nudges": PLACEMENT_NUDGES.get(module, []),
                "position_hint": POSITION_HINTS.get(module, "中心位置を維持し、三面図で干渉が出る場合のみ1-2mm単位で調整する。"),
                "design_hint": DESIGN_HINTS.get(module, "三面図で輪郭が読めるように面とラインの密度を調整する。"),
                "triview_proof": TRIVIEW_PROOF.get(module, "正面/側面/背面/3Qのスクリーンショットで確認する。"),
                "evidence_required": EVIDENCE_REQUIRED.get(module, ["front", "side", "back", "3q"]),
                "route_gate": ROUTE_GATES.get(
                    module,
                    {
                        "web": "Suit Forge inspection must show the part as intentional armor.",
                        "quest": "Henshin Trial must keep body-relative placement and motion clearance.",
                        "replay": "Replay Archive must preserve the same identity in recorded evidence.",
                    },
                ),
                "acceptance": {
                    "bbox_warning_count_target": 0,
                    "preview_fallback_parts_target": 0,
                    "sidecar_glb_bbox_match_max_m": 0.002,
                    "mirror_pair_max_delta_pct": 3.0 if module in PAIR_GROUPS else None,
                    "runtime_visibility": "do_not_promote_fidelity_hold_variants_without_promotion_packet",
                },
            }
        )
    return adjustments


def _format_markdown(report: dict[str, Any], adjustments: list[dict[str, Any]]) -> str:
    lines = [
        "# Modeler Fit Micro-Adjustment Plan",
        "",
        "Purpose: turn current GLB smoke warnings into per-part size and placement tasks for the exhibition build.",
        "",
        f"- Preview GLB parts: `{report.get('preview_glb_parts')}`",
        f"- Preview fallback parts: `{report.get('preview_fallback_parts')}`",
        f"- BBox warning count: `{report.get('bbox_warning_count')}`",
        f"- Contract: `{CONTRACT_VERSION}`",
        f"- Route lore: {ROUTE_LORE}",
        "",
        "## Per-Part Tasks",
        "",
        "| Part | Axis | Current | Minimum pass | Demo target | Full target delta | Scale | Variant scope | Position / tri-view note |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for item in adjustments:
        variant_scope = ", ".join(item["affected_fidelity_hold_variants"]) or item["fidelity_hold_relation"]
        for task in item["size_tasks"]:
            lines.append(
                "| "
                f"{item['display_name']} (`{item['module']}`) | "
                f"{task['axis_label']} `{task['axis']}` | "
                f"{task['actual_mm']}mm -> {task['target_mm']}mm | "
                f"{task['pass_min_mm']}mm | "
                f"{task['recommended_demo_target_mm']}mm (+{task['recommended_demo_delta_mm']}mm) | "
                f"+{task['target_delta_mm']}mm | "
                f"{task['axis_scale_factor']}x | "
                f"{variant_scope} | "
                f"{item['position_hint']} {item['triview_proof']} |"
            )
    lines.extend(
        [
            "",
            "## Design Notes",
            "",
        ]
    )
    for item in adjustments:
        lines.append(f"- `{item['module']}`: {item['design_hint']}")
    lines.extend(["", "## Route Gate Notes", ""])
    for item in adjustments:
        route_gate = item["route_gate"]
        lines.append(
            f"- `{item['module']}`: Web={route_gate['web']} Quest={route_gate['quest']} Replay={route_gate['replay']}"
        )
    lines.extend(
        [
            "",
            "Acceptance:",
            "",
            "- Re-run `python tools/smoke_web_glb_load.py --report-json` from the packaged root.",
            "- `preview_fallback_parts == 0` remains true.",
            "- BBox warning count is `0`, or each remaining warning has a waiver record and tri-view proof.",
            "- For left/right pairs, apply the same size change to both sides unless an explicit asymmetry is approved.",
            "- Keep `fidelity_hold` variants out of public runtime until sidecar provenance, tri-view proof, and route proof are complete.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(_REPO_ROOT), help="repo root to scan")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)

    report = smoke_check_web_glb_load(args.repo_root)
    adjustments = fit_adjustments_from_report(report)
    if args.format == "json":
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "route_lore": ROUTE_LORE,
                    "adjustments": adjustments,
                    "source_summary": report,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(_format_markdown(report, adjustments))
    return 0 if report.get("preview_fallback_parts") == 0 and not report.get("failures") else 1


if __name__ == "__main__":
    raise SystemExit(main())
