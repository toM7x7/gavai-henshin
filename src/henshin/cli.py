"""Command-line entrypoint for prototyping pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .archive import ensure_session_dir, save_session_bundle
from .bodyfit import BodyFrame, CoverScale as BodyCoverScale, SegmentSpec, Vec2 as BodyVec2, run_body_sequence
from .constants import REFUSAL_CODES
from .forge import create_draft_morphotype, create_draft_suitspec, write_json
from .gemini_image import (
    GeminiImageError,
    extension_for_mime,
    generate_image,
    resolve_api_key,
    save_image,
    write_generation_meta,
)
from .ids import generate_approval_id, generate_morphotype_id, generate_session_id, generate_suit_id
from .part_prompts import list_enabled_parts, resolve_part_prompts
from .rightarm import CoverScale, RightArmFrame, Vec2, run_rightarm_sequence
from .transform import ProtocolStateMachine
from .validators import load_json, validate_file


def _cmd_new_session(args: argparse.Namespace) -> int:
    session_id = args.session_id or generate_session_id()
    path = ensure_session_dir(session_id, root=args.root)
    print(json.dumps({"session_id": session_id, "path": str(path)}, ensure_ascii=False))
    return 0


def _cmd_draft(args: argparse.Namespace) -> int:
    session_id = args.session_id or generate_session_id()
    session_dir = ensure_session_dir(session_id, root=args.root)

    suit_id = args.suit_id or generate_suit_id(
        series=args.series,
        role=args.role,
        rev=args.rev,
        seq=args.seq,
    )
    morphotype_id = args.morphotype_id or generate_morphotype_id()
    approval_id = args.approval_id or generate_approval_id()

    suit = create_draft_suitspec(
        suit_id=suit_id,
        style_tags=args.style_tags or ["metal", "visor", "audit"],
        oath=args.oath,
        model_id=args.model_id,
    )
    suit["approval_id"] = approval_id
    suit["morphotype_id"] = morphotype_id

    morph = create_draft_morphotype(morphotype_id=morphotype_id, source=args.source)
    morph["session_id"] = session_id

    suit_path = write_json(session_dir / "suitspec.json", suit)
    morph_path = write_json(session_dir / "morphotype.json", morph)

    print(
        json.dumps(
            {
                "session_id": session_id,
                "suitspec": str(suit_path),
                "morphotype": str(morph_path),
                "approval_id": approval_id,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _run_machine(mode: str, refusal_code: str) -> ProtocolStateMachine:
    machine = ProtocolStateMachine()
    if mode == "happy":
        machine.run_happy_path()
        return machine

    for state in [
        "POSTED",
        "FIT_AUDIT",
        "MORPHOTYPE_LOCKED",
        "DESIGN_ISSUED",
        "DRY_FIT_SIM",
        "TRY_ON",
        "APPROVAL_PENDING",
    ]:
        machine.transition(state)
    machine.refuse(refusal_code, note="Provisional refusal during demo")
    return machine


def _cmd_demo(args: argparse.Namespace) -> int:
    session_id = args.session_id or generate_session_id()
    session_dir = ensure_session_dir(session_id, root=args.root)

    suit = create_draft_suitspec()
    morph = create_draft_morphotype(source=args.source)
    suit["approval_id"] = generate_approval_id()
    suit["morphotype_id"] = morph["morphotype_id"]
    morph["session_id"] = session_id

    machine = _run_machine(mode=args.mode, refusal_code=args.refusal_code)
    outputs = save_session_bundle(
        session_id=session_id,
        suit_spec=suit,
        morphotype=morph,
        machine=machine,
        root=args.root,
    )

    print(
        json.dumps(
            {
                "session_id": session_id,
                "session_dir": str(session_dir),
                "final_state": machine.state,
                "outputs": {k: str(v) for k, v in outputs.items()},
            },
            ensure_ascii=False,
        )
    )
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    validate_file(args.path, kind=args.kind)
    print(json.dumps({"path": args.path, "kind": args.kind, "valid": True}, ensure_ascii=False))
    return 0


def _resolve_prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        return args.prompt
    if args.suitspec:
        spec = load_json(args.suitspec)
        generation = spec.get("generation", {})
        prompt = generation.get("prompt")
        if prompt:
            return prompt
    raise ValueError("Prompt is required. Set --prompt or provide --suitspec with generation.prompt.")


def _cmd_generate_image(args: argparse.Namespace) -> int:
    try:
        prompt = _resolve_prompt(args)
        api_key = resolve_api_key(args.api_key)
    except (GeminiImageError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    session_id = args.session_id or generate_session_id()
    session_dir = ensure_session_dir(session_id, root=args.root)
    artifacts_dir = session_dir / "artifacts"

    try:
        result = generate_image(
            prompt=prompt,
            model_id=args.model_id,
            api_key=api_key,
            timeout_seconds=args.timeout,
        )
    except GeminiImageError as exc:
        print(json.dumps({"ok": False, "error": str(exc), "session_id": session_id}, ensure_ascii=False))
        return 1

    if args.output:
        output_path = Path(args.output)
    else:
        suffix = extension_for_mime(result.mime_type)
        filename = "Blueprint.generated" if args.kind == "blueprint" else "Emblem.generated"
        output_path = artifacts_dir / f"{filename}{suffix}"

    image_path = save_image(result, output_path=output_path)
    meta_path = write_generation_meta(
        artifacts_dir / f"{args.kind}.generation.json",
        result=result,
        kind=args.kind,
    )

    print(
        json.dumps(
            {
                "ok": True,
                "session_id": session_id,
                "kind": args.kind,
                "model_id": args.model_id,
                "image_path": str(image_path),
                "meta_path": str(meta_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _cmd_generate_parts(args: argparse.Namespace) -> int:
    spec = load_json(args.suitspec)
    requested = args.parts or list_enabled_parts(spec)
    if not requested:
        print(json.dumps({"ok": False, "error": "No enabled parts found in suitspec."}, ensure_ascii=False))
        return 2

    prompts = resolve_part_prompts(spec, requested)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "ok": True,
                    "dry_run": True,
                    "parts": requested,
                    "prompts": prompts,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    try:
        api_key = resolve_api_key(args.api_key)
    except GeminiImageError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    model_id = args.model_id or spec.get("generation", {}).get("model_id", "gemini-3-pro-image-preview")
    session_id = args.session_id or generate_session_id()
    session_dir = ensure_session_dir(session_id, root=args.root)
    parts_dir = session_dir / "artifacts" / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)

    generated: dict[str, dict[str, str]] = {}
    errors: dict[str, str] = {}
    for part in requested:
        try:
            result = generate_image(
                prompt=prompts[part],
                model_id=model_id,
                api_key=api_key,
                timeout_seconds=args.timeout,
            )
            ext = extension_for_mime(result.mime_type)
            image_path = save_image(result, output_path=parts_dir / f"{part}.generated{ext}")
            meta_path = write_generation_meta(parts_dir / f"{part}.generation.json", result=result, kind=f"part:{part}")
            generated[part] = {"image_path": str(image_path), "meta_path": str(meta_path)}
        except GeminiImageError as exc:
            errors[part] = str(exc)

    if args.update_suitspec:
        modules = spec.setdefault("modules", {})
        generation = spec.setdefault("generation", {})
        part_prompts = generation.setdefault("part_prompts", {})
        for part, prompt in prompts.items():
            part_prompts[part] = prompt
        for part, info in generated.items():
            module = modules.setdefault(part, {"enabled": True, "asset_ref": f"modules/{part}/base.prefab"})
            module["texture_path"] = info["image_path"]
        write_json(args.suitspec, spec)

    summary_path = parts_dir / "parts.generation.summary.json"
    summary = {
        "session_id": session_id,
        "model_id": model_id,
        "requested_parts": requested,
        "generated": generated,
        "errors": errors,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = len(errors) == 0
    print(
        json.dumps(
            {
                "ok": ok,
                "session_id": session_id,
                "generated_count": len(generated),
                "error_count": len(errors),
                "summary_path": str(summary_path),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


def _cmd_simulate_rightarm(args: argparse.Namespace) -> int:
    payload = load_json(args.input)
    raw_frames = payload.get("frames", [])
    frames: list[RightArmFrame] = []
    for item in raw_frames:
        frames.append(
            RightArmFrame(
                dt_sec=float(item["dt_sec"]),
                right_elbow_xy01=(float(item["right_elbow_xy01"][0]), float(item["right_elbow_xy01"][1])),
                right_wrist_xy01=(float(item["right_wrist_xy01"][0]), float(item["right_wrist_xy01"][1])),
            )
        )

    cover = payload.get("cover_scale", {"x": 1.0, "y": 1.0})
    dock = payload.get("dock", {"center": [0.55, -0.25], "radius": 0.18, "hold_to_equip_sec": 0.7})

    result = run_rightarm_sequence(
        frames=frames,
        mirror=bool(payload.get("mirror", True)),
        cover_scale=CoverScale(float(cover["x"]), float(cover["y"])),
        dock_center=Vec2(float(dock["center"][0]), float(dock["center"][1])),
        dock_radius=float(dock["radius"]),
        hold_to_equip_sec=float(dock.get("hold_to_equip_sec", 0.7)),
    )

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(out), "equip_frame": result["equip_frame"]}, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))

    return 0


def _cmd_simulate_body(args: argparse.Namespace) -> int:
    payload = load_json(args.input)
    raw_frames = payload.get("frames", [])

    frames: list[BodyFrame] = []
    for item in raw_frames:
        joints: dict[str, tuple[float, float]] = {}
        for joint_name, xy in item.get("joints", {}).items():
            joints[joint_name] = (float(xy[0]), float(xy[1]))
        frames.append(BodyFrame(dt_sec=float(item["dt_sec"]), joints_xy01=joints))

    raw_specs = payload.get("segments", [])
    segment_specs: list[SegmentSpec] | None = None
    if raw_specs:
        segment_specs = []
        for row in raw_specs:
            segment_specs.append(
                SegmentSpec(
                    name=str(row["name"]),
                    start_joint=str(row["start_joint"]),
                    end_joint=str(row["end_joint"]),
                    radius_factor=float(row.get("radius_factor", 0.22)),
                    radius_min=float(row.get("radius_min", 0.05)),
                    radius_max=float(row.get("radius_max", 0.22)),
                    z=float(row.get("z", 0.22)),
                    smooth_gain=float(row.get("smooth_gain", 18.0)),
                    dock_offset_x=float(row.get("dock_offset_x", 0.0)),
                    dock_offset_y=float(row.get("dock_offset_y", 0.0)),
                )
            )

    cover = payload.get("cover_scale", {"x": 1.0, "y": 1.0})
    dock = payload.get("dock", {"center": [0.55, -0.25], "radius": 0.18, "hold_to_equip_sec": 0.7})

    result = run_body_sequence(
        frames=frames,
        mirror=bool(payload.get("mirror", True)),
        cover_scale=BodyCoverScale(float(cover["x"]), float(cover["y"])),
        dock_center=BodyVec2(float(dock["center"][0]), float(dock["center"][1])),
        dock_radius=float(dock.get("radius", 0.18)),
        hold_to_equip_sec=float(dock.get("hold_to_equip_sec", 0.7)),
        trigger_joint=str(dock.get("trigger_joint", "right_wrist")),
        segment_specs=segment_specs,
    )

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "ok": True,
                    "output": str(out),
                    "equip_frame": result["equip_frame"],
                    "segments": len(result["segments"]),
                },
                ensure_ascii=False,
            )
        )
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="henshin", description="SIM-first henshin prototyping CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    new_session = sub.add_parser("new-session", help="Create a new session workspace")
    new_session.add_argument("--root", default="sessions")
    new_session.add_argument("--session-id")
    new_session.set_defaults(func=_cmd_new_session)

    draft = sub.add_parser("draft", help="Create draft SuitSpec + Morphotype files")
    draft.add_argument("--root", default="sessions")
    draft.add_argument("--session-id")
    draft.add_argument("--suit-id")
    draft.add_argument("--series", default="AXIS")
    draft.add_argument("--role", default="OP")
    draft.add_argument("--rev", type=int, default=0)
    draft.add_argument("--seq", type=int, default=1)
    draft.add_argument("--approval-id")
    draft.add_argument("--morphotype-id")
    draft.add_argument("--oath", default="INTEGRITY_FIRST")
    draft.add_argument("--model-id", default="gemini-3-pro-image-preview")
    draft.add_argument("--source", choices=["manual", "mocopi", "webcam"], default="manual")
    draft.add_argument("--style-tags", nargs="*")
    draft.set_defaults(func=_cmd_draft)

    demo = sub.add_parser("demo", help="Run end-to-end demo bundle generation")
    demo.add_argument("--root", default="sessions")
    demo.add_argument("--session-id")
    demo.add_argument("--source", choices=["manual", "mocopi", "webcam"], default="manual")
    demo.add_argument("--mode", choices=["happy", "refused"], default="happy")
    demo.add_argument(
        "--refusal-code",
        choices=REFUSAL_CODES,
        default="INCOMPLETE_PROCEDURE",
    )
    demo.set_defaults(func=_cmd_demo)

    validate = sub.add_parser("validate", help="Validate a JSON file")
    validate.add_argument("--kind", choices=["suitspec", "morphotype"], required=True)
    validate.add_argument("--path", required=True)
    validate.set_defaults(func=_cmd_validate)

    generate_image_cmd = sub.add_parser("generate-image", help="Generate blueprint/emblem image via Gemini API")
    generate_image_cmd.add_argument("--root", default="sessions")
    generate_image_cmd.add_argument("--session-id")
    generate_image_cmd.add_argument("--kind", choices=["blueprint", "emblem"], default="blueprint")
    generate_image_cmd.add_argument("--suitspec", help="Path to SuitSpec JSON (uses generation.prompt)")
    generate_image_cmd.add_argument("--prompt", help="Direct prompt override")
    generate_image_cmd.add_argument("--model-id", default="gemini-3-pro-image-preview")
    generate_image_cmd.add_argument("--api-key", help="Gemini API key (optional if env is set)")
    generate_image_cmd.add_argument("--timeout", type=int, default=90)
    generate_image_cmd.add_argument("--output", help="Output image path")
    generate_image_cmd.set_defaults(func=_cmd_generate_image)

    generate_parts = sub.add_parser(
        "generate-parts",
        help="Generate per-part images from suitspec module list via Gemini API",
    )
    generate_parts.add_argument("--root", default="sessions")
    generate_parts.add_argument("--session-id")
    generate_parts.add_argument("--suitspec", required=True)
    generate_parts.add_argument("--parts", nargs="*", help="Optional subset of parts")
    generate_parts.add_argument("--model-id", help="Overrides suitspec generation.model_id")
    generate_parts.add_argument("--api-key", help="Gemini API key (optional if env is set)")
    generate_parts.add_argument("--timeout", type=int, default=90)
    generate_parts.add_argument("--update-suitspec", action="store_true")
    generate_parts.add_argument("--dry-run", action="store_true")
    generate_parts.set_defaults(func=_cmd_generate_parts)

    simulate_rightarm = sub.add_parser(
        "simulate-rightarm",
        help="Run right-arm docking/equip/follow simulation from frame sequence JSON",
    )
    simulate_rightarm.add_argument("--input", required=True, help="Input JSON sequence file")
    simulate_rightarm.add_argument("--output", help="Optional output JSON path")
    simulate_rightarm.set_defaults(func=_cmd_simulate_rightarm)

    simulate_body = sub.add_parser(
        "simulate-body",
        help="Run full-body segment docking/equip/follow simulation from frame sequence JSON",
    )
    simulate_body.add_argument("--input", required=True, help="Input JSON sequence file")
    simulate_body.add_argument("--output", help="Optional output JSON path")
    simulate_body.set_defaults(func=_cmd_simulate_body)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
