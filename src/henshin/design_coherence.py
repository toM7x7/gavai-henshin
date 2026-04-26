from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


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

LEFT_RIGHT_PAIRS = [
    ("left_shoulder", "right_shoulder"),
    ("left_upperarm", "right_upperarm"),
    ("left_forearm", "right_forearm"),
    ("left_hand", "right_hand"),
    ("left_thigh", "right_thigh"),
    ("left_shin", "right_shin"),
    ("left_boot", "right_boot"),
]


def run_design_coherence_audit(
    *,
    root: str | Path,
    suitspec: str | Path = "examples/suitspec.sample.json",
    canon: str | Path = "viewer/shared/armor-canon.js",
) -> dict[str, Any]:
    repo_root = Path(root).resolve()
    suitspec_path = _resolve_repo_path(repo_root, suitspec)
    canon_path = _resolve_repo_path(repo_root, canon)
    payload = json.loads(suitspec_path.read_text(encoding="utf-8"))
    canon_fit = _read_module_vis(canon_path)

    findings: list[dict[str, Any]] = []
    modules = payload.get("modules") if isinstance(payload.get("modules"), dict) else {}
    _audit_fit_contract(payload, findings)
    _audit_module_inventory(repo_root, payload, modules, findings)
    _audit_left_right_pairs(modules, findings)
    _audit_operator_identity(payload, findings)
    _audit_canon_fit_drift(modules, canon_fit, findings)

    counts = {
        "error": sum(1 for finding in findings if finding["severity"] == "error"),
        "warning": sum(1 for finding in findings if finding["severity"] == "warning"),
        "info": sum(1 for finding in findings if finding["severity"] == "info"),
    }
    return {
        "ok": counts["error"] == 0,
        "suit_id": payload.get("suit_id"),
        "suitspec": _relative_path(repo_root, suitspec_path),
        "canon": _relative_path(repo_root, canon_path),
        "module_count": len(modules),
        "expected_module_count": len(PART_ORDER),
        "counts": counts,
        "findings": findings,
    }


def write_design_coherence_markdown(audit: dict[str, Any], output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Design Coherence Audit",
        "",
        f"- Suit: `{audit.get('suit_id')}`",
        f"- SuitSpec: `{audit.get('suitspec')}`",
        f"- Canon: `{audit.get('canon')}`",
        f"- Result: `{'PASS' if audit.get('ok') else 'CHECK'}`",
        f"- Findings: {audit.get('counts', {})}",
        "",
        "| Severity | Code | Part | Message |",
        "|---|---|---|---|",
    ]
    for finding in audit.get("findings", []):
        lines.append(
            "| {severity} | `{code}` | `{part}` | {message} |".format(
                severity=finding.get("severity", ""),
                code=finding.get("code", ""),
                part=finding.get("part") or "-",
                message=str(finding.get("message", "")).replace("|", "\\|"),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _audit_fit_contract(payload: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    contract = payload.get("fit_contract") if isinstance(payload.get("fit_contract"), dict) else {}
    if not contract:
        findings.append(_finding("warning", "missing_fit_contract", None, "SuitSpec does not declare what module.fit means."))
        return
    if contract.get("module_fit_stage") not in {"authoring_baseline", "calibrated_body_fit", "runtime_override"}:
        findings.append(_finding("warning", "unknown_fit_stage", None, "fit_contract.module_fit_stage is not recognized."))
    if contract.get("module_fit_space") not in {"body_sim_segment", "vrm_anchor_local", "viewer_runtime"}:
        findings.append(_finding("warning", "unknown_fit_space", None, "fit_contract.module_fit_space is not recognized."))


def _texture_fallback_mode(payload: dict[str, Any]) -> str:
    fallback = payload.get("texture_fallback") if isinstance(payload.get("texture_fallback"), dict) else {}
    return str(fallback.get("mode") or "").strip()


def _audit_module_inventory(repo_root: Path, payload: dict[str, Any], modules: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    texture_fallback_mode = _texture_fallback_mode(payload)
    for part in PART_ORDER:
        module = modules.get(part)
        if not isinstance(module, dict):
            findings.append(_finding("error", "missing_module", part, "Required armor module is missing."))
            continue
        asset_ref = str(module.get("asset_ref") or "")
        texture_path = str(module.get("texture_path") or "")
        if not asset_ref or not _resolve_repo_path(repo_root, asset_ref).is_file():
            findings.append(_finding("error", "missing_asset_ref", part, f"Mesh asset is missing: {asset_ref or '-'}"))
        if not texture_path:
            findings.append(_finding("warning", "missing_texture_path", part, "No texture path is recorded."))
        elif _is_runtime_output(texture_path):
            if texture_fallback_mode == "palette_material":
                findings.append(
                    _finding(
                        "info",
                        "runtime_texture_path_with_fallback",
                        part,
                        f"Runtime texture path uses palette fallback when missing: {texture_path}",
                    )
                )
            else:
                findings.append(
                    _finding(
                        "warning",
                        "runtime_texture_path",
                        part,
                        f"Canonical sample points to ignored runtime output: {texture_path}",
                    )
                )
        elif not _resolve_repo_path(repo_root, texture_path).is_file():
            findings.append(_finding("warning", "missing_texture_file", part, f"Texture file is missing: {texture_path}"))

    extra = sorted(set(modules) - set(PART_ORDER))
    for part in extra:
        findings.append(_finding("info", "extra_module", part, "Module is not part of the current canonical 18-part kit."))


def _audit_left_right_pairs(modules: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    for left, right in LEFT_RIGHT_PAIRS:
        left_module = modules.get(left) if isinstance(modules.get(left), dict) else {}
        right_module = modules.get(right) if isinstance(modules.get(right), dict) else {}
        if not left_module or not right_module:
            continue
        left_fit = left_module.get("fit") if isinstance(left_module.get("fit"), dict) else {}
        right_fit = right_module.get("fit") if isinstance(right_module.get("fit"), dict) else {}
        if left_fit.get("shape") != right_fit.get("shape"):
            findings.append(_finding("error", "left_right_shape_drift", f"{left}/{right}", "Left/right shapes differ."))
        scale_delta = _max_vec_delta(left_fit.get("scale"), right_fit.get("scale"))
        offset_delta = abs(float(left_fit.get("offsetY") or 0) - float(right_fit.get("offsetY") or 0))
        z_delta = abs(float(left_fit.get("zOffset") or 0) - float(right_fit.get("zOffset") or 0))
        if max(scale_delta, offset_delta, z_delta) > 0.05:
            findings.append(
                _finding(
                    "warning",
                    "left_right_fit_drift",
                    f"{left}/{right}",
                    f"Left/right fit differs: scale={scale_delta:.3f}, offsetY={offset_delta:.3f}, zOffset={z_delta:.3f}.",
                )
            )


def _audit_operator_identity(payload: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    top_profile = payload.get("operator_profile") if isinstance(payload.get("operator_profile"), dict) else {}
    generation = payload.get("generation") if isinstance(payload.get("generation"), dict) else {}
    raw_profile = generation.get("last_operator_profile_raw") if isinstance(generation.get("last_operator_profile_raw"), dict) else {}
    resolved_profile = (
        generation.get("last_operator_profile_resolved")
        if isinstance(generation.get("last_operator_profile_resolved"), dict)
        else {}
    )
    for key in ("protect_archetype", "temperament_bias", "color_mood"):
        top = top_profile.get(key)
        generated = raw_profile.get(key) or resolved_profile.get(key)
        if top and generated and top != generated:
            findings.append(
                _finding(
                    "warning",
                    "operator_identity_drift",
                    None,
                    f"operator_profile.{key} is `{top}` but latest generation metadata uses `{generated}`.",
                )
            )


def _audit_canon_fit_drift(modules: dict[str, Any], canon_fit: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    for part in PART_ORDER:
        module = modules.get(part) if isinstance(modules.get(part), dict) else {}
        fit = module.get("fit") if isinstance(module.get("fit"), dict) else {}
        canon = canon_fit.get(part) if isinstance(canon_fit.get(part), dict) else {}
        if not fit or not canon:
            continue
        if fit.get("shape") != canon.get("shape"):
            findings.append(_finding("warning", "canon_shape_drift", part, f"Fit shape differs from canon: {fit.get('shape')} vs {canon.get('shape')}."))
        scale_delta = _max_vec_delta(fit.get("scale"), canon.get("scale"))
        offset_delta = abs(float(fit.get("offsetY") or 0) - float(canon.get("offsetY") or 0))
        z_delta = abs(float(fit.get("zOffset") or 0) - float(canon.get("zOffset") or 0))
        if scale_delta > 0.25 or offset_delta > 0.2 or z_delta > 0.08:
            findings.append(
                _finding(
                    "info",
                    "canon_fit_drift",
                    part,
                    f"Fit differs from armor canon: scale={scale_delta:.3f}, offsetY={offset_delta:.3f}, zOffset={z_delta:.3f}.",
                )
            )


def _read_module_vis(path: Path) -> dict[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    start_token = "export const MODULE_VIS = Object.freeze({"
    start = text.find(start_token)
    if start < 0:
        return {}
    cursor = start + len("export const MODULE_VIS = Object.freeze(")
    block = _extract_braced_block(text, cursor)
    result: dict[str, dict[str, Any]] = {}
    for part in PART_ORDER:
        match = re.search(rf"\b{re.escape(part)}\s*:\s*{{", block)
        if not match:
            continue
        part_block = _extract_braced_block(block, match.end() - 1)
        result[part] = {
            "shape": _match_string(part_block, "shape"),
            "source": _match_string(part_block, "source"),
            "attach": _match_string(part_block, "attach"),
            "offsetY": _match_number(part_block, "offsetY", 0),
            "zOffset": _match_number(part_block, "zOffset", 0),
            "scale": _match_number_array(part_block, "scale"),
        }
    return result


def _extract_braced_block(text: str, open_brace_index: int) -> str:
    depth = 0
    for index in range(open_brace_index, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace_index : index + 1]
    return ""


def _match_string(block: str, key: str) -> str | None:
    match = re.search(rf"\b{re.escape(key)}\s*:\s*\"([^\"]*)\"", block)
    return match.group(1) if match else None


def _match_number(block: str, key: str, fallback: float) -> float:
    match = re.search(rf"\b{re.escape(key)}\s*:\s*(-?\d+(?:\.\d+)?)", block)
    return float(match.group(1)) if match else fallback


def _match_number_array(block: str, key: str) -> list[float]:
    match = re.search(rf"\b{re.escape(key)}\s*:\s*\[([^\]]+)\]", block)
    if not match:
        return []
    return [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", match.group(1))]


def _max_vec_delta(left: Any, right: Any) -> float:
    if not isinstance(left, list) or not isinstance(right, list) or not left or not right:
        return 0.0
    pairs = zip(left[:3], right[:3], strict=False)
    return max((abs(float(a) - float(b)) for a, b in pairs), default=0.0)


def _is_runtime_output(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized.startswith("sessions/")


def _resolve_repo_path(repo_root: Path, raw: str | Path) -> Path:
    path = Path(raw)
    candidate = path if path.is_absolute() else repo_root / path
    resolved = candidate.resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"Path is outside repository root: {raw}") from exc
    return resolved


def _relative_path(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _finding(severity: str, code: str, part: str | None, message: str) -> dict[str, Any]:
    return {"severity": severity, "code": code, "part": part, "message": message}
