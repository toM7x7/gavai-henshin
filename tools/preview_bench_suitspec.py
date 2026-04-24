from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from henshin.bench_preview import write_batch_preview_suitspec, write_preview_suitspec  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a dashboard/body-fit preview SuitSpec from a generated bench texture."
    )
    parser.add_argument("--base", default="examples/suitspec.sample.json", help="Base SuitSpec JSON.")
    parser.add_argument("--output", default="sessions/S-BENCH-HELMET/suitspec.json", help="Preview SuitSpec output.")
    parser.add_argument("--part", default="helmet", help="Module to receive the generated texture.")
    parser.add_argument("--image", default=None, help="Generated texture image. Overrides --bench-summary.")
    parser.add_argument("--bench-summary", default=None, help="Prompt bench summary.json with live_outputs.")
    parser.add_argument("--batch-summary", default=None, help="Multi-part prompt bench summary.json.")
    parser.add_argument("--variant", default=None, help="live_outputs variant key to use.")
    parser.add_argument("--fit-summary", default=None, help="Optional Body Fit capture summary.json to apply fit/anchor.")
    parser.add_argument("--all-parts", action="store_true", help="Keep all SuitSpec modules enabled.")
    parser.add_argument("--label", default=None, help="Optional preview label stored in generation.preview_source.")
    args = parser.parse_args()

    if args.batch_summary:
        result = write_batch_preview_suitspec(
            base_suitspec_path=args.base,
            output_path=args.output,
            repo_root=REPO_ROOT,
            batch_summary_path=args.batch_summary,
            variant_key=args.variant,
            only_parts=not args.all_parts,
            fit_summary_path=args.fit_summary,
            preview_label=args.label,
        )
    else:
        result = write_preview_suitspec(
            base_suitspec_path=args.base,
            output_path=args.output,
            repo_root=REPO_ROOT,
            part=args.part,
            image_path=args.image,
            bench_summary_path=args.bench_summary,
            variant_key=args.variant,
            only_part=not args.all_parts,
            fit_summary_path=args.fit_summary,
            preview_label=args.label,
        )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
