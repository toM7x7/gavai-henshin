"""Armor Variation Lab — 仮説設計図を複数生成し、全身装着で比較する.

Each run: sample N hypothesis blueprints (random emotion axes or preset
intents), build all 18 parts per variant, assemble them on the default VRM
body, render front/3q/side, and stitch a contact sheet for side-by-side
review of generation variety and VRM fit.

Run from the repo root (D:/personal_dev/gavai-henshin/gavai-henshin):
  python tools/armor_variation_lab.py --count 3 --quality preview
  python tools/armor_variation_lab.py --count 4 --seed 7 --intent "守護と誓い"

Outputs under output/blueprint-armor/lab/<run>/:
  variant_XX.blueprint.json, variant_XX_{front,three_quarter,side}.png,
  contact-sheet.png
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from henshin.armor_blueprint import AXES, compile_blueprint  # noqa: E402

ASSEMBLER = REPO_ROOT / "tools" / "blender" / "armor_fullbody_assembler.py"
ALL_MODULES = (
    "helmet", "chest", "back", "waist",
    "left_shoulder", "right_shoulder",
    "left_upperarm", "right_upperarm",
    "left_forearm", "right_forearm",
    "left_hand", "right_hand",
    "left_thigh", "right_thigh",
    "left_shin", "right_shin",
    "left_boot", "right_boot",
)

PRESET_INTENTS = [
    "高揚。光を纏い、上へ伸びる王冠の誓い。",
    "闘志。牙と刃、前へ踏み込む赤の誓い。",
    "哀傷。静かな雨、長い残光を引く青の誓い。",
    "緊張。研ぎ澄まされた警戒、細い線の紫の誓い。",
    "守護。仲間を包む盾、厚い胸甲の緑の誓い。",
    "受容。すべてを受け止める曲線、紅の誓い。",
]


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
    raise FileNotFoundError("Blender not found. Set HENSHIN_BLENDER_EXE.")


def sample_axes(rng: random.Random) -> dict[str, float]:
    primary, secondary = rng.sample(list(AXES), 2)
    axes = {primary: rng.uniform(0.55, 0.95), secondary: rng.uniform(0.25, 0.6)}
    if rng.random() < 0.4:
        axes[rng.choice([a for a in AXES if a not in axes])] = rng.uniform(0.1, 0.35)
    return axes


def make_variant(rng: random.Random, index: int, base_intent: str | None) -> dict:
    if base_intent:
        intent = base_intent
        axes = None if index == 0 else sample_axes(rng)  # variant 0 = pure intent
    else:
        intent = rng.choice(PRESET_INTENTS)
        axes = sample_axes(rng)
    return compile_blueprint(intent, axes=axes, modules=ALL_MODULES)


def run_assembly(blender: str, blueprint_path: Path, out_dir: Path, label: str, quality: str) -> dict | None:
    cmd = [
        blender, "--background", "--factory-startup",
        "--python", str(ASSEMBLER), "--",
        "--blueprint", str(blueprint_path),
        "--out-dir", str(out_dir),
        "--quality", quality,
        "--label", label,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (proc.stdout or "").splitlines():
        if line.startswith("ARMOR_FULLBODY_RESULT:"):
            return json.loads(line.split(":", 1)[1])
    sys.stderr.write(f"[{label}] assembly failed (exit {proc.returncode})\n")
    sys.stderr.write((proc.stdout or "")[-1200:] + "\n")
    return None


def contact_sheet(results: list[dict], out_path: Path, view: str = "three_quarter") -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow not available; skipping contact sheet")
        return
    tiles = []
    for res in results:
        path = res["views"].get(view)
        if path and os.path.isfile(path):
            tiles.append((res, Image.open(path)))
    if not tiles:
        return
    w, h = tiles[0][1].size
    sheet = Image.new("RGB", (w * len(tiles), h), (11, 21, 32))
    draw = ImageDraw.Draw(sheet)
    for i, (res, img) in enumerate(tiles):
        sheet.paste(img, (i * w, 0))
        label = f"{res['label']}  {res.get('blueprint', '')}"
        draw.text((i * w + 18, 18), label, fill=(198, 214, 227))
        axes = res.get("emotion_axes") or {}
        if axes:
            axis_text = "  ".join(f"{k}:{v}" for k, v in axes.items())
            draw.text((i * w + 18, 40), axis_text, fill=(127, 147, 166))
    sheet.save(out_path)
    print(f"contact sheet -> {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--seed", type=int, default=None, help="omit for a fresh random run")
    parser.add_argument("--intent", default=None, help="fix the intent text; axes still vary per variant")
    parser.add_argument("--quality", default="preview", choices=["preview", "runtime", "hero"])
    parser.add_argument("--run-name", default=None)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    run_name = args.run_name or f"run-{rng.randrange(36**4):04x}"
    out_dir = REPO_ROOT / "output" / "blueprint-armor" / "lab" / run_name
    out_dir.mkdir(parents=True, exist_ok=True)
    blender = find_blender()

    results = []
    for i in range(max(1, args.count)):
        label = f"variant_{i:02d}"
        blueprint = make_variant(rng, i, args.intent)
        bp_path = out_dir / f"{label}.blueprint.json"
        bp_path.write_text(json.dumps(blueprint, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{label}] {blueprint['blueprint_id']} axes={blueprint.get('emotion_axes')}")
        res = run_assembly(blender, bp_path, out_dir, label, args.quality)
        if res:
            res["emotion_axes"] = blueprint.get("emotion_axes")
            results.append(res)

    contact_sheet(results, out_dir / "contact-sheet.png")
    summary = {"ok": bool(results), "run": run_name, "out_dir": str(out_dir),
               "variants": [{"label": r["label"], "blueprint": r.get("blueprint")} for r in results]}
    (out_dir / "lab-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
