from __future__ import annotations

import json
from pathlib import Path

from .fit_regression import run_fit_regression


PART_ORDER = [
    "helmet",
    "chest",
    "back",
    "waist",
    "left_shoulder",
    "right_shoulder",
    "left_upperarm",
    "right_upperarm",
    "left_forearm",
    "right_forearm",
    "left_hand",
    "right_hand",
    "left_thigh",
    "right_thigh",
    "left_shin",
    "right_shin",
    "left_boot",
    "right_boot",
]

PART_METADATA = {
    "helmet": {"wave": "Wave 3", "priority": "P2", "proxy": "head_sphere", "anchor_bone": "head"},
    "chest": {"wave": "Wave 1", "priority": "P0", "proxy": "torso_obb", "anchor_bone": "upperChest"},
    "back": {"wave": "Wave 1", "priority": "P0", "proxy": "torso_obb", "anchor_bone": "upperChest"},
    "waist": {"wave": "Wave 1", "priority": "P0", "proxy": "torso_obb", "anchor_bone": "hips"},
    "left_shoulder": {"wave": "Wave 1", "priority": "P0", "proxy": "upperarm_capsule", "anchor_bone": "leftShoulder"},
    "right_shoulder": {"wave": "Wave 1", "priority": "P0", "proxy": "upperarm_capsule", "anchor_bone": "rightShoulder"},
    "left_upperarm": {"wave": "Wave 1", "priority": "P0", "proxy": "upperarm_capsule", "anchor_bone": "leftUpperArm"},
    "right_upperarm": {"wave": "Wave 1", "priority": "P0", "proxy": "upperarm_capsule", "anchor_bone": "rightUpperArm"},
    "left_forearm": {"wave": "Wave 1", "priority": "P0", "proxy": "forearm_capsule", "anchor_bone": "leftLowerArm"},
    "right_forearm": {"wave": "Wave 1", "priority": "P0", "proxy": "forearm_capsule", "anchor_bone": "rightLowerArm"},
    "left_hand": {"wave": "Wave 3", "priority": "P2", "proxy": "forearm_capsule", "anchor_bone": "leftHand"},
    "right_hand": {"wave": "Wave 3", "priority": "P2", "proxy": "forearm_capsule", "anchor_bone": "rightHand"},
    "left_thigh": {"wave": "Wave 2", "priority": "P1", "proxy": "thigh_capsule", "anchor_bone": "leftUpperLeg"},
    "right_thigh": {"wave": "Wave 2", "priority": "P1", "proxy": "thigh_capsule", "anchor_bone": "rightUpperLeg"},
    "left_shin": {"wave": "Wave 2", "priority": "P0", "proxy": "shin_capsule", "anchor_bone": "leftLowerLeg"},
    "right_shin": {"wave": "Wave 2", "priority": "P0", "proxy": "shin_capsule", "anchor_bone": "rightLowerLeg"},
    "left_boot": {"wave": "Wave 2", "priority": "P0", "proxy": "foot_obb", "anchor_bone": "leftFoot"},
    "right_boot": {"wave": "Wave 2", "priority": "P0", "proxy": "foot_obb", "anchor_bone": "rightFoot"},
}

SEAM_FOCUS = {
    "helmet": ["helmet-chest"],
    "chest": ["helmet-chest", "chest-back", "chest-waist"],
    "back": ["chest-back"],
    "waist": ["chest-waist", "waist-thigh"],
    "left_shoulder": ["shoulder-upperarm"],
    "right_shoulder": ["shoulder-upperarm"],
    "left_upperarm": ["shoulder-upperarm", "upperarm-forearm"],
    "right_upperarm": ["shoulder-upperarm", "upperarm-forearm"],
    "left_forearm": ["upperarm-forearm", "forearm-hand"],
    "right_forearm": ["upperarm-forearm", "forearm-hand"],
    "left_hand": ["forearm-hand"],
    "right_hand": ["forearm-hand"],
    "left_thigh": ["waist-thigh", "thigh-shin"],
    "right_thigh": ["waist-thigh", "thigh-shin"],
    "left_shin": ["thigh-shin", "shin-boot"],
    "right_shin": ["thigh-shin", "shin-boot"],
    "left_boot": ["shin-boot"],
    "right_boot": ["shin-boot"],
}

SYMMETRY_GROUP_PARTS = {
    "shoulder": ["left_shoulder", "right_shoulder"],
    "upperarm": ["left_upperarm", "right_upperarm"],
    "forearm": ["left_forearm", "right_forearm"],
    "hand": ["left_hand", "right_hand"],
    "thigh": ["left_thigh", "right_thigh"],
    "shin": ["left_shin", "right_shin"],
    "boot": ["left_boot", "right_boot"],
}

PASS_GATES = {
    "rebuild": [
        "surfaceViolations == 0",
        "heroOverflow == 0",
        "critical部位なら partScore >= 58",
        "symmetryDelta ok",
    ],
    "tune": [
        "surfaceViolations == 0",
        "heroOverflow == 0",
        "symmetryDelta ok",
    ],
    "keep": [
        "VRM baselineで再回帰して summary.canSave == true",
    ],
}


def _part_decision_rank(decision: str) -> int:
    return {"keep": 0, "tune": 1, "rebuild": 2}.get(decision, 0)


def _recommend_action(decision: str) -> str:
    if decision == "rebuild":
        return "VRM基準で原型再制作"
    if decision == "tune":
        return "既存メッシュ補正 + fit再校正"
    return "現状維持"


def _part_summary_indexes(summary: dict) -> tuple[dict, dict, dict, dict]:
    weak_parts = {entry["part"]: entry for entry in summary.get("weakParts") or [] if isinstance(entry, dict) and entry.get("part")}
    surface = {}
    for entry in summary.get("surfaceViolations") or []:
        if not isinstance(entry, dict) or not entry.get("part"):
            continue
        surface.setdefault(entry["part"], []).append(entry)
    hero = {}
    for entry in summary.get("heroOverflow") or []:
        if not isinstance(entry, dict) or not entry.get("part"):
            continue
        hero.setdefault(entry["part"], []).append(entry)
    symmetry = {}
    for entry in summary.get("symmetryDelta") or []:
        if not isinstance(entry, dict) or not entry.get("group"):
            continue
        symmetry[entry["group"]] = entry
    return weak_parts, surface, hero, symmetry


def _weak_pairs_by_part(summary: dict) -> dict[str, list[dict]]:
    pairs: dict[str, list[dict]] = {}
    for entry in summary.get("weakPairs") or []:
        if not isinstance(entry, dict):
            continue
        pair_name = str(entry.get("pair") or "")
        if "-" not in pair_name:
            continue
        left, right = pair_name.split("-", 1)
        payload = {
            "pair": pair_name,
            "score": entry.get("score"),
            "gap": entry.get("gap"),
            "penetration": entry.get("penetration"),
        }
        pairs.setdefault(left, []).append(payload)
        pairs.setdefault(right, []).append(payload)
    return pairs


def _min_scale_locks_by_part(summary: dict) -> dict[str, dict]:
    locks: dict[str, dict] = {}
    for entry in summary.get("minScaleLocks") or []:
        if not isinstance(entry, dict) or not entry.get("part"):
            continue
        locks[str(entry["part"])] = entry
    return locks


def _decision_from_findings(part: str, weak: dict | None, surface: list[dict], hero: list[dict], symmetry: dict | None) -> tuple[str, list[str]]:
    reasons: list[str] = []
    decision = "keep"

    critical_surface = [entry for entry in surface if entry.get("critical")]
    if critical_surface:
        decision = "rebuild"
        reasons.append("critical surface violation")
    if weak and float(weak.get("score", 100)) < 58:
        decision = "rebuild"
        reasons.append(f"critical score {float(weak.get('score', 0)):.1f} < 58")
    elif weak and float(weak.get("score", 100)) < 82 and _part_decision_rank(decision) < _part_decision_rank("tune"):
        decision = "tune"
        reasons.append(f"part score {float(weak.get('score', 0)):.1f} < 82")
    if surface and _part_decision_rank(decision) < _part_decision_rank("tune"):
        decision = "tune"
        reasons.append("surface violation")
    if hero and _part_decision_rank(decision) < _part_decision_rank("tune"):
        decision = "tune"
        reasons.append("hero allowance overflow")
    if symmetry and not symmetry.get("ok", True):
        decision = "rebuild"
        reasons.append(f"symmetry drift {float(symmetry.get('delta', 0)):.3f}")

    if not reasons:
        reasons.append("baseline gate passed")
    return decision, reasons


def derive_part_actions(summary: dict) -> list[dict]:
    weak_parts, surface_map, hero_map, symmetry_map = _part_summary_indexes(summary)
    weak_pairs = _weak_pairs_by_part(summary)
    min_scale_locks = _min_scale_locks_by_part(summary)
    actions = []
    for part in PART_ORDER:
        meta = PART_METADATA[part]
        symmetry = None
        for group, members in SYMMETRY_GROUP_PARTS.items():
            if part in members:
                symmetry = symmetry_map.get(group)
                break
        decision, reasons = _decision_from_findings(
            part,
            weak_parts.get(part),
            surface_map.get(part, []),
            hero_map.get(part, []),
            symmetry,
        )
        actions.append(
            {
                "part": part,
                "decision": decision,
                "recommended_action": _recommend_action(decision),
                "wave": meta["wave"],
                "priority": meta["priority"],
                "anchor_bone": meta["anchor_bone"],
                "body_proxy": meta["proxy"],
                "seam_focus": SEAM_FOCUS.get(part, []),
                "part_score": weak_parts.get(part, {}).get("score"),
                "surface_violation_count": len(surface_map.get(part, [])),
                "hero_overflow_count": len(hero_map.get(part, [])),
                "symmetry_ok": None if symmetry is None else bool(symmetry.get("ok", True)),
                "weak_pairs": weak_pairs.get(part, []),
                "min_scale_lock_axes": (min_scale_locks.get(part) or {}).get("axes", []),
                "reasons": reasons,
                "pass_gates": PASS_GATES[decision],
            }
        )
    return actions


def build_authoring_audit(regression_result: dict) -> dict:
    baselines = []
    decision_totals = {"rebuild": 0, "tune": 0, "keep": 0}
    for baseline in regression_result.get("baselines") or []:
        summary = baseline.get("summary") or {}
        part_actions = derive_part_actions(summary)
        for action in part_actions:
            decision_totals[action["decision"]] += 1
        baselines.append(
            {
                "id": baseline.get("id"),
                "label": baseline.get("label"),
                "vrm_path": baseline.get("vrm_path"),
                "regression_ok": bool(baseline.get("ok")),
                "fit_score": summary.get("fitScore"),
                "can_save": bool(summary.get("canSave")),
                "summary_reasons": summary.get("reasons") or [],
                "part_actions": part_actions,
            }
        )
    return {
        "ok": bool(regression_result.get("ok")),
        "mode": regression_result.get("mode"),
        "root": regression_result.get("root"),
        "suitspec": regression_result.get("suitspec"),
        "sim": regression_result.get("sim"),
        "decision_totals": decision_totals,
        "waves": [
            {
                "name": "Wave 1",
                "goal": "胸背腰と腕系の接続をVRM基準で作り直す",
                "parts": [part for part in PART_ORDER if PART_METADATA[part]["wave"] == "Wave 1"],
            },
            {
                "name": "Wave 2",
                "goal": "下半身の接続と足首まわりをVRM基準で安定させる",
                "parts": [part for part in PART_ORDER if PART_METADATA[part]["wave"] == "Wave 2"],
            },
            {
                "name": "Wave 3",
                "goal": "頭部と末端部位を仕上げて展示品質へ寄せる",
                "parts": [part for part in PART_ORDER if PART_METADATA[part]["wave"] == "Wave 3"],
            },
        ],
        "baselines": baselines,
    }


def render_authoring_audit_markdown(audit: dict) -> str:
    lines = [
        "# VRM-First Authoring Audit",
        "",
        f"- mode: `{audit.get('mode')}`",
        f"- suitspec: `{audit.get('suitspec')}`",
        f"- sim: `{audit.get('sim')}`",
        f"- rebuild: {audit.get('decision_totals', {}).get('rebuild', 0)}",
        f"- tune: {audit.get('decision_totals', {}).get('tune', 0)}",
        f"- keep: {audit.get('decision_totals', {}).get('keep', 0)}",
        "",
    ]
    for wave in audit.get("waves") or []:
        lines.extend(
            [
                f"## {wave['name']}",
                "",
                f"- goal: {wave['goal']}",
                f"- parts: {', '.join(wave['parts'])}",
                "",
            ]
        )

    for baseline in audit.get("baselines") or []:
        lines.extend(
            [
                f"## Baseline: {baseline.get('label')}",
                "",
                f"- vrm_path: `{baseline.get('vrm_path')}`",
                f"- regression_ok: `{baseline.get('regression_ok')}`",
                f"- fit_score: `{baseline.get('fit_score')}`",
                f"- can_save: `{baseline.get('can_save')}`",
            ]
        )
        if baseline.get("summary_reasons"):
            lines.append(f"- summary_reasons: {' | '.join(baseline['summary_reasons'])}")
        lines.append("")
        for action in baseline.get("part_actions") or []:
            weak_pairs = ", ".join(f"{entry['pair']}({entry['score']})" for entry in action["weak_pairs"]) or "-"
            lines.extend(
                [
                    f"### {action['part']}",
                    "",
                    f"- decision: `{action['decision']}`",
                    f"- action: {action['recommended_action']}",
                    f"- wave / priority: {action['wave']} / {action['priority']}",
                    f"- anchor / proxy: `{action['anchor_bone']}` / `{action['body_proxy']}`",
                    f"- seam_focus: {', '.join(action['seam_focus']) or '-'}",
                    f"- weak_pairs: {weak_pairs}",
                    f"- min_scale_lock_axes: {', '.join(action['min_scale_lock_axes']) or '-'}",
                    f"- reasons: {' | '.join(action['reasons'])}",
                    f"- pass_gates: {' | '.join(action['pass_gates'])}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_authoring_audit(audit: dict, *, json_path: str | Path | None = None, markdown_path: str | Path | None = None) -> dict:
    outputs: dict[str, str] = {}
    if json_path:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        outputs["json"] = str(path)
    if markdown_path:
        path = Path(markdown_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_authoring_audit_markdown(audit), encoding="utf-8")
        outputs["markdown"] = str(path)
    return outputs


def run_authoring_audit(
    *,
    root: str | Path = ".",
    baselines_manifest: str | Path = "viewer/assets/vrm/baselines.json",
    suitspec: str | Path | None = None,
    sim: str | Path | None = None,
    baseline_ids: list[str] | None = None,
    mode: str = "auto_fit",
    timeout_seconds: int = 90,
    browser_channel: str | None = None,
) -> dict:
    regression = run_fit_regression(
        root=root,
        baselines_manifest=baselines_manifest,
        suitspec=suitspec,
        sim=sim,
        baseline_ids=baseline_ids,
        mode=mode,
        timeout_seconds=timeout_seconds,
        browser_channel=browser_channel,
    )
    return build_authoring_audit(regression)
