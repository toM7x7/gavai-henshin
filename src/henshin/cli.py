"""Command-line entrypoint for prototyping pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .archive import ensure_session_dir, save_session_bundle
from .constants import REFUSAL_CODES
from .forge import create_draft_morphotype, create_draft_suitspec, write_json
from .ids import generate_approval_id, generate_morphotype_id, generate_session_id, generate_suit_id
from .transform import ProtocolStateMachine
from .validators import validate_file


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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
