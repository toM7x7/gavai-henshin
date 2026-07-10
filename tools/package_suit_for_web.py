# -*- coding: utf-8 -*-
"""スーツをWeb体験(Vercel/Supabase)向けに束ねる — 動線M1の橋.

Usage:
  python tools/package_suit_for_web.py --suit-dir output/blueprint-armor/thunder \
      --label thunder --code GAVAI-0001 [--upload]

- アセンブラ出力ディレクトリから assembly/lod1/lod2/vrm(+リポ内の henshin.vrma)を集め、
  suit-package.json マニフェストと共に webdrop/<code>/ へ集約する(ドライラン既定)。
- --upload 時は Supabase Storage/PostgREST へ直接アップロード。
  env: SUPABASE_URL, SUPABASE_SERVICE_KEY(service_role。公開readはバケット設定で)
  依存ゼロ(stdlib urllib)。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import struct
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VRMA_DEFAULT = REPO / "output" / "blueprint-armor" / "henshin.vrma"


def glb_triangles(path: Path) -> int:
    try:
        data = path.read_bytes()
        ln = struct.unpack("<I", data[12:16])[0]
        doc = json.loads(data[20:20 + ln])
        return sum(doc["accessors"][pr["indices"]]["count"] // 3
                   for m in doc.get("meshes", []) for pr in m.get("primitives", []))
    except Exception:  # noqa: BLE001
        return 0


def collect(suit_dir: Path, label: str) -> dict[str, Path]:
    cand = {
        "assembly": suit_dir / f"{label}.assembly.glb",
        "lod1": suit_dir / f"{label}.lod1.glb",
        "lod2": suit_dir / f"{label}.lod2.glb",
        "vrm": suit_dir / f"{label}.vrm",
    }
    files = {k: p for k, p in cand.items() if p.exists()}
    if VRMA_DEFAULT.exists():
        files["vrma"] = VRMA_DEFAULT
    return files


def upload_supabase(bucket_path: str, data: bytes, content_type: str) -> None:
    base = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_KEY"]
    req = urllib.request.Request(
        f"{base}/storage/v1/object/suits/{bucket_path}",
        data=data, method="POST",
        headers={"Authorization": f"Bearer {key}", "apikey": key,
                 "Content-Type": content_type, "x-upsert": "true"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        resp.read()


def register_code(manifest: dict) -> None:
    base = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_KEY"]
    row = {"recall_code": manifest["recall_code"],
           "blueprint_id": manifest["blueprint_id"],
           "manifest_path": f"{manifest['recall_code']}/suit-package.json",
           "status": "ACTIVE"}
    req = urllib.request.Request(
        f"{base}/rest/v1/recall_codes",
        data=json.dumps(row).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "apikey": key,
                 "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        resp.read()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suit-dir", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--code", required=True)
    ap.add_argument("--upload", action="store_true")
    args = ap.parse_args()

    suit_dir = Path(args.suit_dir).resolve()
    files = collect(suit_dir, args.label)
    if "assembly" not in files:
        raise SystemExit(f"assembly.glb not found in {suit_dir}")

    assembly_json = suit_dir / f"{args.label}.assembly.json"
    meta = json.loads(assembly_json.read_text(encoding="utf-8")) if assembly_json.exists() else {}
    bp_path = None
    for cand in (suit_dir / "blueprint.json", suit_dir.parent / "blueprint.json"):
        if cand.exists():
            bp_path = cand
            break
    bp = json.loads(bp_path.read_text(encoding="utf-8")) if bp_path else {}

    manifest = {
        "package_version": "suit-package.v1",
        "recall_code": args.code,
        "blueprint_id": meta.get("blueprint") or bp.get("blueprint_id", ""),
        "design_intent": bp.get("design_intent", ""),
        "palette": bp.get("palette", {}),
        "files": {k: f"{k}{p.suffix}" for k, p in files.items()},
        "triangles": {k: glb_triangles(p) for k, p in files.items() if p.suffix == ".glb"},
        "fit_summary": meta.get("fit_summary", {}),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    drop = REPO / "webdrop" / args.code
    drop.mkdir(parents=True, exist_ok=True)
    for k, p in files.items():
        shutil.copy2(p, drop / f"{k}{p.suffix}")
    (drop / "suit-package.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PACKAGED: {drop}")
    for k, p in files.items():
        print(f"  {k}: {p.name} ({round(p.stat().st_size / 1048576, 1)}MB)")

    if args.upload:
        # リポ直下の .env を自動読込(既にある環境変数が優先)
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
            from henshin._env import load_dotenv
            for k, v in load_dotenv().items():
                os.environ.setdefault(k, v)
        except Exception:
            pass
        if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY")):
            raise SystemExit("--upload needs SUPABASE_URL and SUPABASE_SERVICE_KEY (env or .env)")
        for k, p in files.items():
            ct = "model/gltf-binary" if p.suffix in (".glb", ".vrm", ".vrma") else "application/octet-stream"
            upload_supabase(f"{args.code}/{k}{p.suffix}", p.read_bytes(), ct)
            print(f"UPLOADED: suits/{args.code}/{k}{p.suffix}")
        upload_supabase(f"{args.code}/suit-package.json",
                        json.dumps(manifest, ensure_ascii=False).encode("utf-8"),
                        "application/json")
        register_code(manifest)
        print(f"RECALL_CODE_ACTIVE: {args.code}")


if __name__ == "__main__":
    main()
