"""Hand-typed text -> armor, one command, three inspectable layers.

Layer 1 (instant, no Blender): text -> ArmorBlueprint JSON (the "design figure"
the rule compiler / LLM emits). Prints detected emotion axes, palette, and a
per-part feature map so you can read what the words decided.

Layer 2 (--build parts): blueprint -> GLB + sidecar + preview mesh + render.

Layer 3 (--assemble): full 18-part suit assembled on the VRM body, fit-audited,
rendered front/3q/side.

Run from the repo root (D:/personal_dev/gavai-henshin/gavai-henshin):

  # Layer 1 only — see how the words become a design figure (fast)
  python tools/forge_from_text.py --text "闘志。赤い牙、前へ踏み込む誓い。"

  # Layer 1 + build two parts and render them
  python tools/forge_from_text.py --text "メタル系。銀の装甲、青い光。守護。" --build helmet,chest

  # Layer 1 + full-body assembly render
  python tools/forge_from_text.py --text "哀傷。静かな青、長い残光。" --assemble

Same text always yields the same blueprint id (deterministic rule route), so
re-running builds the identical asset — verify with --twice.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

# Windows consoles default to cp932; force UTF-8 so JP text + bar chars print.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from henshin.armor_blueprint import (  # noqa: E402
    AXES,
    axes_from_intent,
    compile_blueprint,
    compile_blueprint_llm,
)

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
LAB_DIR = REPO_ROOT / "output" / "blueprint-armor" / "lab-text"


def find_blender() -> str:
    explicit = os.environ.get("HENSHIN_BLENDER_EXE")
    if explicit and Path(explicit).is_file():
        return explicit
    on_path = shutil.which("blender")
    if on_path:
        return on_path
    cands = sorted(glob.glob(r"C:/Program Files/Blender Foundation/Blender */blender.exe"), reverse=True)
    if cands:
        return cands[0]
    raise FileNotFoundError("Blender not found. Set HENSHIN_BLENDER_EXE.")


def bar(value: float, width: int = 20) -> str:
    filled = int(round(value * width))
    return "█" * filled + "·" * (width - filled)


def summarize(blueprint: dict) -> None:
    print("=" * 66)
    print(f"設計図ID : {blueprint['blueprint_id']}")
    print(f"意図     : {blueprint['design_intent'][:60]}")
    print("-" * 66)
    print("感情軸 (Emolgia axes):")
    axes = blueprint.get("emotion_axes", {})
    for a in AXES:
        v = axes.get(a, 0.0)
        if v > 0:
            print(f"  {a:9s} {bar(v)} {v:.2f}")
    print("-" * 66)
    pal = blueprint.get("palette", {})
    print("パレット :", "  ".join(f"{k}={v}" for k, v in pal.items()))
    print("-" * 66)
    print("部位ごとの意匠 (per-part design):")
    for part in blueprint.get("parts", []):
        sil = part.get("silhouette", {})
        surf = part.get("surface", {})
        feats = [f.get("kind") for f in part.get("features", [])]
        rings = len(surf.get("ring_grooves", []))
        merid = len(surf.get("meridian_grooves", []))
        cross = sil.get("cross_section", "-")
        line = f"  {part['module']:15s} 断面={cross:8s} 溝={rings}環/{merid}子午"
        if feats:
            line += "  意匠=" + ",".join(feats)
        print(line)
    print("=" * 66)


def build_parts(blender: str, bp_path: Path, out_dir: Path, modules: str, quality: str, render: bool) -> None:
    builder = REPO_ROOT / "tools" / "blender" / "armor_blueprint_builder.py"
    cmd = [blender, "--background", "--factory-startup", "--python", str(builder), "--",
           "--blueprint", str(bp_path), "--out-dir", str(out_dir), "--quality", quality]
    if modules:
        cmd += ["--modules", modules]
    if render:
        cmd += ["--render", "1"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (proc.stdout or "").splitlines():
        if line.startswith("ARMOR_BLUEPRINT_RESULT:"):
            result = json.loads(line.split(":", 1)[1])
            print("\n生成アセット (Layer 2):")
            for m in result["modules"]:
                dims = "x".join(f"{d:.3f}" for d in m["dims_m"])
                print(f"  {m['module']:15s} tris={m['triangles']:>6}  bbox={dims}m  -> {m['glb']}")
            return
    sys.stderr.write((proc.stdout or "")[-1500:] + "\n" + (proc.stderr or "")[-800:])


def assemble(blender: str, bp_path: Path, out_dir: Path, label: str, quality: str) -> None:
    asm = REPO_ROOT / "tools" / "blender" / "armor_fullbody_assembler.py"
    cmd = [blender, "--background", "--factory-startup", "--python", str(asm), "--",
           "--blueprint", str(bp_path), "--out-dir", str(out_dir), "--quality", quality, "--label", label]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (proc.stdout or "").splitlines():
        if line.startswith("ARMOR_FULLBODY_RESULT:"):
            r = json.loads(line.split(":", 1)[1])
            fs = r["fit_summary"]
            print("\n全身装着 + 適合審査 (Layer 3):")
            print(f"  パーツ適合 {fs['parts_pass']}/{fs['parts_total']}   関節ギャップ {fs['joints_pass']}/{fs['joints_total']}")
            for name, path in r["views"].items():
                print(f"  view {name:14s} -> {path}")
            return
    sys.stderr.write((proc.stdout or "")[-1500:] + "\n" + (proc.stderr or "")[-800:])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--text", required=True, help="hand-typed intent (思い・意匠)")
    parser.add_argument("--llm", action="store_true",
                        help="route B: interpret via Gemini (falls back to rules on any failure)")
    parser.add_argument("--build", default="", help="comma-separated modules to build+render, or 'all'")
    parser.add_argument("--assemble", action="store_true", help="assemble the full suit on the VRM body and render")
    parser.add_argument("--quality", default="preview", choices=["preview", "runtime", "hero"])
    parser.add_argument("--twice", action="store_true", help="compile twice and confirm the design figure is identical")
    args = parser.parse_args()

    if args.llm:
        blueprint, route = compile_blueprint_llm(args.text, modules=ALL_MODULES)
        print(f"経路 (route): {route}")
    else:
        blueprint = compile_blueprint(args.text, modules=ALL_MODULES)
    slug = blueprint["blueprint_id"]
    out_dir = LAB_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    bp_path = out_dir / "blueprint.json"
    bp_json = json.dumps(blueprint, ensure_ascii=False, indent=2)
    bp_path.write_text(bp_json, encoding="utf-8")

    summarize(blueprint)
    digest = hashlib.sha256(bp_json.encode("utf-8")).hexdigest()[:12]
    print(f"設計図JSON : {bp_path}")
    print(f"内容ハッシュ: {digest}  (同じ文言なら常に同じ = 決定論)")

    if args.twice:
        again = json.dumps(compile_blueprint(args.text, modules=ALL_MODULES), ensure_ascii=False, indent=2)
        d2 = hashlib.sha256(again.encode("utf-8")).hexdigest()[:12]
        print(f"再コンパイル: {d2}  ->  {'一致 (deterministic)' if d2 == digest else '不一致!'}")

    if args.build or args.assemble:
        blender = find_blender()
        if args.build:
            modules = "" if args.build == "all" else args.build
            build_parts(blender, bp_path, out_dir, modules, args.quality, render=True)
        if args.assemble:
            assemble(blender, bp_path, out_dir / "fullbody", slug, args.quality)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
