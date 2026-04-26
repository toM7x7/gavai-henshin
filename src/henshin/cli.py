"""Command-line entrypoint for prototyping pipeline."""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import socketserver
from pathlib import Path

from .archive import ensure_session_dir, save_session_bundle
from .bodyfit import BodyFrame, CoverScale as BodyCoverScale, SegmentSpec, Vec2 as BodyVec2, run_body_sequence
from .constants import REFUSAL_CODES
from .dashboard_server import serve_dashboard
from .design_coherence import run_design_coherence_audit, write_design_coherence_markdown
from .fit_regression import DEFAULT_BASELINE_MANIFEST, run_fit_regression, write_fit_regression_output
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
from .iw_henshin import (
    DEFAULT_EXPLANATION,
    DEFAULT_TRIGGER_PHRASE,
    IWSDKHenshinConfig,
    IWSDKHenshinRequest,
    run_iwsdk_henshin,
)
from .part_generation import (
    DEFAULT_GEMINI_FALLBACK_MODEL,
    DEFAULT_PROVIDER_PROFILE,
    GenerationRequest,
    _resolve_fallback_image,
    _use_fallback_asset,
    run_generate_parts,
)
from .image_providers import ImageProviderError
from .manifest import project_suitspec_to_manifest
from .rightarm import CoverScale, RightArmFrame, Vec2, run_rightarm_sequence
from .sakura_ai_engine import resolve_sakura_config
from .transform import ProtocolStateMachine
from .validators import load_json, validate_file
from .vrm_authoring_audit import run_authoring_audit, write_authoring_audit


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


def _cmd_project_manifest(args: argparse.Namespace) -> int:
    try:
        suitspec = load_json(args.suitspec)
        part_catalog = None
        if args.partcatalog:
            part_catalog = load_json(args.partcatalog)
        manifest = project_suitspec_to_manifest(
            suitspec,
            part_catalog=part_catalog,
            manifest_id=args.manifest_id,
            status=args.status,
            projection_version=args.projection_version,
        )
        if args.validate:
            from .validators import validate_against_schema

            validate_against_schema(manifest, "suitmanifest")
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    output_path = None
    if args.output:
        output_path = write_json(args.output, manifest)
    print(
        json.dumps(
            {
                "ok": True,
                "manifest_id": manifest["manifest_id"],
                "suit_id": manifest["suit_id"],
                "parts": len(manifest["parts"]),
                "output": str(output_path) if output_path else None,
            },
            ensure_ascii=False,
        )
    )
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
    req = GenerationRequest(
        suitspec=args.suitspec,
        root=args.root,
        session_id=args.session_id,
        parts=args.parts,
        model_id=args.model_id,
        api_key=args.api_key,
        generation_brief=args.generation_brief,
        operator_profile_override=None,
        timeout=args.timeout,
        texture_mode=args.texture_mode,
        uv_refine=bool(args.uv_refine),
        fallback_dir=args.fallback_dir,
        prefer_fallback=bool(args.prefer_fallback),
        update_suitspec=bool(args.update_suitspec),
        dry_run=bool(args.dry_run),
        provider_profile=args.provider_profile,
        priority_mode=args.priority_mode,
        use_cache=bool(args.use_cache),
        hero_render=bool(args.hero_render),
        tracking_source=args.tracking_source,
        max_parallel=int(args.max_parallel),
        retry_count=int(args.retry_count),
    )
    try:
        result = run_generate_parts(req)
    except (ValueError, ImageProviderError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


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


def _cmd_serve_viewer(args: argparse.Namespace) -> int:
    port = int(args.port)
    directory = Path(args.root).resolve()
    if not directory.exists():
        print(json.dumps({"ok": False, "error": f"Directory not found: {directory}"}, ensure_ascii=False))
        return 2

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(
            json.dumps(
                {
                    "ok": True,
                    "message": "Serving viewer root",
                    "root": str(directory),
                    "url": f"http://localhost:{port}/viewer/body-fit/",
                },
                ensure_ascii=False,
            )
        )
        httpd.serve_forever()
    return 0


def _cmd_serve_dashboard(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if not root.exists():
        print(json.dumps({"ok": False, "error": f"Directory not found: {root}"}, ensure_ascii=False))
        return 2
    serve_dashboard(root=root, port=int(args.port))
    return 0


def _cmd_fit_regression(args: argparse.Namespace) -> int:
    try:
        result = run_fit_regression(
            root=args.root,
            baselines_manifest=args.baselines,
            suitspec=args.suitspec,
            sim=args.sim,
            baseline_ids=args.baseline_id,
            mode=args.mode,
            force_tpose=bool(args.force_tpose),
            timeout_seconds=int(args.timeout),
            browser_channel=args.browser_channel,
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    if args.output:
        output_path = write_fit_regression_output(result, args.output)
        result = {**result, "output": str(output_path)}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


def _cmd_authoring_audit(args: argparse.Namespace) -> int:
    try:
        audit = run_authoring_audit(
            root=args.root,
            baselines_manifest=args.baselines,
            suitspec=args.suitspec,
            sim=args.sim,
            baseline_ids=args.baseline_id,
            mode=args.mode,
            timeout_seconds=int(args.timeout),
            browser_channel=args.browser_channel,
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    outputs = write_authoring_audit(
        audit,
        json_path=args.output_json,
        markdown_path=args.output_md,
    )
    payload = {**audit}
    if outputs:
        payload["outputs"] = outputs
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _cmd_design_coherence(args: argparse.Namespace) -> int:
    try:
        audit = run_design_coherence_audit(root=args.root, suitspec=args.suitspec, canon=args.canon)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    if args.output_md:
        audit["output_md"] = str(write_design_coherence_markdown(audit, args.output_md))
    print(json.dumps(audit, ensure_ascii=False))
    return 0 if audit.get("ok") else 1


def _cmd_iw_henshin(args: argparse.Namespace) -> int:
    try:
        mocopi_payload = load_json(args.mocopi) if args.mocopi else None
        config = IWSDKHenshinConfig(
            trigger_phrase=args.trigger_phrase or os.getenv("VOICE_TRIGGER_PHRASE") or DEFAULT_TRIGGER_PHRASE,
            explanation_text=args.explanation or DEFAULT_EXPLANATION,
            tts_enabled=not bool(args.no_tts),
        )
        sakura_config = resolve_sakura_config(
            token=args.sakura_token,
            base_url=args.sakura_base_url,
            whisper_model=args.whisper_model,
            tts_model=args.tts_model,
            tts_voice=args.tts_voice,
            tts_format=args.tts_format,
            timeout_seconds=args.timeout,
        )
        result = run_iwsdk_henshin(
            IWSDKHenshinRequest(
                transcript=args.transcript,
                audio_path=args.audio,
                mocopi_payload=mocopi_payload,
                session_id=args.session_id,
                root=args.root,
                dry_run=bool(args.dry_run),
                config=config,
                sakura_config=sakura_config,
            )
        )
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps(result, ensure_ascii=False))
    if result.get("ok"):
        return 0
    return 2 if result.get("error") else 1


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
    draft.add_argument("--model-id", default=DEFAULT_GEMINI_FALLBACK_MODEL)
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
    validate.add_argument(
        "--kind",
        choices=["suitspec", "morphotype", "suitmanifest", "partcatalog", "transform-session", "replay-script"],
        required=True,
    )
    validate.add_argument("--path", required=True)
    validate.set_defaults(func=_cmd_validate)

    project_manifest = sub.add_parser(
        "project-manifest",
        help="Project a SuitSpec authoring document into a SuitManifest runtime contract",
    )
    project_manifest.add_argument("--suitspec", required=True)
    project_manifest.add_argument("--partcatalog", default="examples/partcatalog.seed.json")
    project_manifest.add_argument("--manifest-id")
    project_manifest.add_argument("--status", choices=["DRAFT", "READY", "ACTIVE", "RETIRED"], default="DRAFT")
    project_manifest.add_argument("--projection-version", default="0.1")
    project_manifest.add_argument("--output")
    project_manifest.add_argument("--validate", action=argparse.BooleanOptionalAction, default=True)
    project_manifest.set_defaults(func=_cmd_project_manifest)

    generate_image_cmd = sub.add_parser("generate-image", help="Generate blueprint/emblem image via Gemini API")
    generate_image_cmd.add_argument("--root", default="sessions")
    generate_image_cmd.add_argument("--session-id")
    generate_image_cmd.add_argument("--kind", choices=["blueprint", "emblem"], default="blueprint")
    generate_image_cmd.add_argument("--suitspec", help="Path to SuitSpec JSON (uses generation.prompt)")
    generate_image_cmd.add_argument("--prompt", help="Direct prompt override")
    generate_image_cmd.add_argument("--model-id", default=DEFAULT_GEMINI_FALLBACK_MODEL)
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
    generate_parts.add_argument(
        "--texture-mode",
        choices=["concept", "mesh_uv"],
        default="mesh_uv",
        help="Prompt mode: concept image or UV-ready mesh texture",
    )
    generate_parts.add_argument(
        "--uv-refine",
        action="store_true",
        help="Two-pass generation: concept image -> UV texture refinement using reference image",
    )
    generate_parts.add_argument(
        "--fallback-dir",
        help="Directory of existing part images used when generation is unavailable or fails",
    )
    generate_parts.add_argument(
        "--prefer-fallback",
        action="store_true",
        help="Use fallback images first when both API and fallback are available",
    )
    generate_parts.add_argument("--update-suitspec", action="store_true")
    generate_parts.add_argument("--dry-run", action="store_true")
    generate_parts.add_argument("--provider-profile", default=DEFAULT_PROVIDER_PROFILE)
    generate_parts.add_argument("--priority-mode", default="exhibition")
    generate_parts.add_argument("--generation-brief", help="Optional concise creative direction for the current run")
    generate_parts.add_argument("--use-cache", action=argparse.BooleanOptionalAction, default=True)
    generate_parts.add_argument("--hero-render", action="store_true")
    generate_parts.add_argument("--tracking-source", choices=["manual", "mocopi", "webcam"], default="webcam")
    generate_parts.add_argument("--max-parallel", type=int, default=4)
    generate_parts.add_argument("--retry-count", type=int, default=1)
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

    serve_viewer = sub.add_parser(
        "serve-viewer",
        help="Serve repository root for browser-based body-fit viewer",
    )
    serve_viewer.add_argument("--root", default=".")
    serve_viewer.add_argument("--port", type=int, default=8000)
    serve_viewer.set_defaults(func=_cmd_serve_viewer)

    serve_dashboard_cmd = sub.add_parser(
        "serve-dashboard",
        help="Serve suit dashboard (part preview + local generate API)",
    )
    serve_dashboard_cmd.add_argument("--root", default=".")
    serve_dashboard_cmd.add_argument("--port", type=int, default=8010)
    serve_dashboard_cmd.set_defaults(func=_cmd_serve_dashboard)

    fit_regression = sub.add_parser(
        "fit-regression",
        help="Run VRM-first fit regression through the browser fit engine",
    )
    fit_regression.add_argument("--root", default=".")
    fit_regression.add_argument("--suitspec", help="Optional SuitSpec override")
    fit_regression.add_argument("--sim", help="Optional body-sim override")
    fit_regression.add_argument("--baselines", default=str(DEFAULT_BASELINE_MANIFEST))
    fit_regression.add_argument("--baseline-id", nargs="*", help="Optional subset of baseline ids")
    fit_regression.add_argument("--mode", choices=["auto_fit", "current"], default="auto_fit")
    fit_regression.add_argument("--force-tpose", action=argparse.BooleanOptionalAction, default=True)
    fit_regression.add_argument("--timeout", type=int, default=90)
    fit_regression.add_argument("--browser-channel", help="Optional browser channel override, e.g. msedge")
    fit_regression.add_argument("--output", help="Optional output JSON path")
    fit_regression.set_defaults(func=_cmd_fit_regression)

    authoring_audit = sub.add_parser(
        "authoring-audit",
        help="Generate a VRM-first armor re-authoring backlog from fit regression results",
    )
    authoring_audit.add_argument("--root", default=".")
    authoring_audit.add_argument("--suitspec", help="Optional SuitSpec override")
    authoring_audit.add_argument("--sim", help="Optional body-sim override")
    authoring_audit.add_argument("--baselines", default=str(DEFAULT_BASELINE_MANIFEST))
    authoring_audit.add_argument("--baseline-id", nargs="*", help="Optional subset of baseline ids")
    authoring_audit.add_argument("--mode", choices=["auto_fit", "current"], default="auto_fit")
    authoring_audit.add_argument("--timeout", type=int, default=90)
    authoring_audit.add_argument("--browser-channel", help="Optional browser channel override, e.g. msedge")
    authoring_audit.add_argument("--output-json", help="Optional JSON output path")
    authoring_audit.add_argument("--output-md", help="Optional Markdown output path")
    authoring_audit.set_defaults(func=_cmd_authoring_audit)

    design_coherence = sub.add_parser(
        "design-coherence-audit",
        help="Audit canonical suit identity, part assets, fit drift, and design portability",
    )
    design_coherence.add_argument("--root", default=".")
    design_coherence.add_argument("--suitspec", default="examples/suitspec.sample.json")
    design_coherence.add_argument("--canon", default="viewer/shared/armor-canon.js")
    design_coherence.add_argument("--output-md", help="Optional Markdown output path")
    design_coherence.set_defaults(func=_cmd_design_coherence)

    iw_henshin = sub.add_parser(
        "iw-henshin",
        help="Run IWSDK-ready voice triggered full-body armor deposition",
    )
    iw_henshin.add_argument("--root", default="sessions")
    iw_henshin.add_argument("--session-id")
    iw_henshin.add_argument("--transcript", help="Use a transcript directly instead of calling Whisper")
    iw_henshin.add_argument("--audio", help="Audio file sent to Sakura Whisper when --transcript is omitted")
    iw_henshin.add_argument("--mocopi", help="mocopi/IWSDK tracking JSON; defaults to an internal demo pose")
    iw_henshin.add_argument("--dry-run", action="store_true", help="Skip remote STT/TTS calls")
    iw_henshin.add_argument("--trigger-phrase", help="Voice trigger phrase; defaults to VOICE_TRIGGER_PHRASE or 生成")
    iw_henshin.add_argument("--explanation", help="TTS explanation text played after trigger detection")
    iw_henshin.add_argument("--no-tts", action="store_true", help="Disable Sakura TTS even when a token is configured")
    iw_henshin.add_argument("--sakura-token", help="Sakura AI Engine account token")
    iw_henshin.add_argument("--sakura-base-url", help="Sakura AI Engine API base URL")
    iw_henshin.add_argument("--whisper-model", help="Sakura Whisper model")
    iw_henshin.add_argument("--tts-model", help="Sakura TTS model")
    iw_henshin.add_argument("--tts-voice", help="Sakura TTS voice")
    iw_henshin.add_argument("--tts-format", help="Sakura TTS response format")
    iw_henshin.add_argument("--timeout", type=int, default=90)
    iw_henshin.set_defaults(func=_cmd_iw_henshin)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
