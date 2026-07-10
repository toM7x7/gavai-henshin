"""Generate armor GLBs from an ArmorBlueprint v1 JSON via headless Blender.

Usage:
  python tools/generate_armor_from_blueprint.py \
      --blueprint examples/armor-blueprint.sample.json \
      --out-dir output/blueprint-armor \
      --modules helmet,chest --quality runtime --render

Blender discovery order: HENSHIN_BLENDER_EXE env var, `blender` on PATH,
then the newest install under C:/Program Files/Blender Foundation.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER = REPO_ROOT / "tools" / "blender" / "armor_blueprint_builder.py"
RESULT_PREFIX = "ARMOR_BLUEPRINT_RESULT:"


def find_blender() -> str:
    explicit = os.environ.get("HENSHIN_BLENDER_EXE")
    if explicit and Path(explicit).is_file():
        return explicit
    on_path = shutil.which("blender")
    if on_path:
        return on_path
    candidates = sorted(
        glob.glob(r"C:/Program Files/Blender Foundation/Blender */blender.exe"),
        reverse=True,
    )
    if candidates:
        return candidates[0]
    raise FileNotFoundError(
        "Blender not found. Set HENSHIN_BLENDER_EXE or install Blender."
    )


def run(blueprint: str, out_dir: str, modules: str, quality: str, render: bool) -> dict:
    cmd = [
        find_blender(), "--background", "--factory-startup",
        "--python", str(BUILDER), "--",
        "--blueprint", str(Path(blueprint).resolve()),
        "--out-dir", str(Path(out_dir).resolve()),
        "--quality", quality,
    ]
    if modules:
        cmd += ["--modules", modules]
    if render:
        cmd += ["--render", "1"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    result = None
    for line in (proc.stdout or "").splitlines():
        if line.startswith(RESULT_PREFIX):
            result = json.loads(line[len(RESULT_PREFIX):])
    if result is None:
        raise RuntimeError(
            f"Blender build failed (exit {proc.returncode}).\n"
            f"stdout tail:\n{(proc.stdout or '')[-2000:]}\n"
            f"stderr tail:\n{(proc.stderr or '')[-2000:]}"
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueprint", required=True)
    parser.add_argument("--out-dir", default="output/blueprint-armor")
    parser.add_argument("--modules", default="", help="comma-separated; default = all parts in the blueprint")
    parser.add_argument("--quality", default="runtime", choices=["preview", "runtime", "hero"])
    parser.add_argument("--render", action="store_true", help="also render a 3/4 preview PNG per module")
    args = parser.parse_args()
    result = run(args.blueprint, args.out_dir, args.modules, args.quality, args.render)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
