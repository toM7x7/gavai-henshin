from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from henshin.prompt_bench import (  # noqa: E402
    DEFAULT_EMOTION_PROFILE,
    DEFAULT_OPERATOR_PROFILE,
    build_helmet_prompt_bench,
    run_live_prompt_bench,
    write_prompt_bench,
)


def _json_arg(value: str | None, fallback: dict[str, str]) -> dict[str, str]:
    if not value:
        return dict(fallback)
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def _default_output_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return REPO_ROOT / "sessions" / "_bench" / "helmet" / stamp


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a focused helmet prompt bench for Nano Banana UV generation.")
    parser.add_argument("--suitspec", default="examples/suitspec.sample.json")
    parser.add_argument("--root", default="sessions")
    parser.add_argument("--part", default="helmet")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--emotion-profile", default=None, help="JSON string or path. Defaults to a protect-oriented helmet test.")
    parser.add_argument("--operator-profile", default=None, help="JSON string or path. Defaults to a midnight stoic one-person profile.")
    parser.add_argument("--brief", default=None, help="Optional extra generation brief.")
    parser.add_argument("--variant", action="append", default=None, help="Run/write only a specific variant key. Can be repeated.")
    parser.add_argument("--live", action="store_true", help="Actually call Nano Banana for each prompt variant.")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--api-key", default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_output_dir()
    emotion_profile = _json_arg(args.emotion_profile, DEFAULT_EMOTION_PROFILE)
    operator_profile = _json_arg(args.operator_profile, DEFAULT_OPERATOR_PROFILE)

    bench = build_helmet_prompt_bench(
        suitspec=args.suitspec,
        root=args.root,
        part=args.part,
        repo_root=REPO_ROOT,
        emotion_profile=emotion_profile,
        operator_profile_override=operator_profile,
        generation_brief=args.brief,
    )
    if args.variant:
        selected = set(args.variant)
        bench["variants"] = [variant for variant in bench["variants"] if variant["key"] in selected]
        bench["comparison"] = [item for item in bench["comparison"] if item["key"] in selected]
        missing = sorted(selected - {variant["key"] for variant in bench["variants"]})
        if missing:
            raise SystemExit(f"Unknown variant key(s): {', '.join(missing)}")
    summary_path = write_prompt_bench(bench, output_dir)
    if args.live:
        run_live_prompt_bench(bench, output_dir, timeout_seconds=args.timeout, api_key=args.api_key)
        summary_path = output_dir / "summary.json"

    print(json.dumps({"ok": True, "summary_path": str(summary_path), "output_dir": str(output_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
