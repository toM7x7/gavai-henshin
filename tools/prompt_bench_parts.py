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

from henshin.part_prompts import list_enabled_parts  # noqa: E402
from henshin.prompt_bench import (  # noqa: E402
    DEFAULT_EMOTION_PROFILE,
    DEFAULT_OPERATOR_PROFILE,
    build_part_prompt_bench,
    run_live_prompt_bench,
    write_prompt_bench,
)
from henshin.validators import load_json  # noqa: E402


def _json_arg(value: str | None, fallback: dict[str, str]) -> dict[str, str]:
    if not value:
        return dict(fallback)
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def _default_output_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return REPO_ROOT / "sessions" / "_bench" / "all-parts" / stamp


def _resolve_parts(value: str | None, suitspec_path: str) -> list[str]:
    spec_path = Path(suitspec_path)
    if not spec_path.is_absolute():
        spec_path = REPO_ROOT / spec_path
    enabled = list_enabled_parts(load_json(spec_path))
    if not value or value == "all":
        return enabled
    requested = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(requested) - set(enabled))
    if unknown:
        raise SystemExit(f"Unknown or disabled part(s): {', '.join(unknown)}")
    return requested


def _filter_variants(bench: dict, variants: list[str] | None) -> None:
    if not variants:
        return
    selected = set(variants)
    bench["variants"] = [variant for variant in bench["variants"] if variant["key"] in selected]
    bench["comparison"] = [item for item in bench["comparison"] if item["key"] in selected]
    missing = sorted(selected - {variant["key"] for variant in bench["variants"]})
    if missing:
        raise SystemExit(f"Unknown variant key(s): {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or run UV prompt bench variants for multiple armor parts.")
    parser.add_argument("--suitspec", default="examples/suitspec.sample.json")
    parser.add_argument("--root", default="sessions")
    parser.add_argument("--parts", default="all", help="Comma-separated part list, or all enabled parts.")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--emotion-profile", default=None, help="JSON string or path.")
    parser.add_argument("--operator-profile", default=None, help="JSON string or path.")
    parser.add_argument("--brief", default=None, help="Optional extra generation brief.")
    parser.add_argument(
        "--variant",
        action="append",
        default=None,
        help="Variant key to run/write. Defaults to c_normal_fold_first. Can be repeated.",
    )
    parser.add_argument("--all-variants", action="store_true", help="Write/run every bench variant.")
    parser.add_argument("--live", action="store_true", help="Actually call Nano Banana for each selected variant.")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--fail-fast", action="store_true", help="Stop at the first failed part.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    emotion_profile = _json_arg(args.emotion_profile, DEFAULT_EMOTION_PROFILE)
    operator_profile = _json_arg(args.operator_profile, DEFAULT_OPERATOR_PROFILE)
    selected_variants = None if args.all_variants else (args.variant or ["c_normal_fold_first"])
    parts = _resolve_parts(args.parts, args.suitspec)

    aggregate = {
        "ok": True,
        "bench_batch_version": "armor-part-prompt-bench-batch-v1",
        "suitspec": args.suitspec,
        "parts": parts,
        "selected_variants": selected_variants or "all",
        "live": bool(args.live),
        "output_dir": str(output_dir),
        "results": {},
        "errors": {},
    }

    for index, part in enumerate(parts, start=1):
        part_dir = output_dir / part
        try:
            bench = build_part_prompt_bench(
                suitspec=args.suitspec,
                root=args.root,
                part=part,
                repo_root=REPO_ROOT,
                emotion_profile=emotion_profile,
                operator_profile_override=operator_profile,
                generation_brief=args.brief,
            )
            _filter_variants(bench, selected_variants)
            summary_path = write_prompt_bench(bench, part_dir)
            if args.live:
                run_live_prompt_bench(bench, part_dir, timeout_seconds=args.timeout, api_key=args.api_key)
                summary_path = part_dir / "summary.json"
                bench = json.loads(summary_path.read_text(encoding="utf-8"))
            aggregate["results"][part] = {
                "index": index,
                "summary_path": str(summary_path),
                "variants": [variant["key"] for variant in bench["variants"]],
                "live_outputs": bench.get("live_outputs", {}),
            }
        except Exception as exc:  # noqa: BLE001
            aggregate["ok"] = False
            aggregate["errors"][part] = str(exc)
            if args.fail_fast:
                break
        finally:
            (output_dir / "summary.json").write_text(json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": aggregate["ok"], "summary_path": str(output_dir / "summary.json"), "output_dir": str(output_dir)}, ensure_ascii=False))
    return 0 if aggregate["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
