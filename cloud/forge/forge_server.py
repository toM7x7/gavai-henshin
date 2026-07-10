"""蒸着執行録 鍛造工場 API — Cloud Run 用ジョブサーバ。

言葉 → 設計図(ルートA) → Blenderヘッドレス鍛造 → Supabase格納 → 呼出符発行。
Vercel の /api/forge がここへプロキシする(ブラウザ直叩きはさせない)。

  POST /forge   {"text": "..."}  + X-Forge-Token   → {"job_id": "..."}
  GET  /job?id=<job_id>                            → {"status", "phase", "code", ...}
  GET  /healthz                                    → ok

Blenderは重いのでビルドは直列(_BUILD_LOCK)。Cloud Run は
--max-instances 1 --no-cpu-throttling で運用する(応答後もスレッドが走る)。
env: SUPABASE_URL / SUPABASE_SERVICE_KEY / FORGE_TOKEN / HENSHIN_BLENDER_EXE
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import urllib.request

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from henshin.armor_blueprint import compile_blueprint, compile_blueprint_llm  # noqa: E402
from package_suit_for_web import glb_triangles, register_code, upload_supabase  # noqa: E402

ASSEMBLER = REPO / "tools" / "blender" / "armor_fullbody_assembler.py"
VRMA_ASSET = HERE / "assets" / "henshin.vrma"
WORK = Path(os.environ.get("FORGE_WORK_DIR", "/tmp/forge"))
TOKEN = os.environ.get("FORGE_TOKEN", "")
MAX_TEXT = 400

_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()
_BUILD_LOCK = threading.Lock()


def _set(job_id: str, **fields) -> None:
    with _JOBS_LOCK:
        _JOBS.setdefault(job_id, {}).update(fields)


def find_blender() -> str:
    exe = os.environ.get("HENSHIN_BLENDER_EXE")
    if exe and Path(exe).exists():
        return exe
    on_path = shutil.which("blender")
    if on_path:
        return on_path
    cands = sorted(glob.glob(r"C:/Program Files/Blender Foundation/Blender */blender.exe"), reverse=True)
    if cands:
        return cands[0]
    raise FileNotFoundError("Blender not found. Set HENSHIN_BLENDER_EXE.")


def _next_code() -> str:
    """呼出符の採番: 台帳の最大値+1(GAVAI-0001形式は9999まで辞書順=数値順)。"""
    base = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_KEY"]
    req = urllib.request.Request(
        f"{base}/rest/v1/recall_codes?select=recall_code&order=recall_code.desc&limit=1",
        headers={"apikey": key, "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        rows = json.load(resp)
    last = 0
    if rows:
        tail = str(rows[0].get("recall_code", "")).rsplit("-", 1)[-1]
        if tail.isdigit():
            last = int(tail)
    return f"GAVAI-{last + 1:04d}"


def _forge_job(job_id: str, text: str, llm: bool = False) -> None:
    with _BUILD_LOCK:
        workdir = WORK / job_id
        try:
            _set(job_id, status="forging", phase="設計図を紡いでいます")
            # ルートB(Gemini解釈)はオプション: llm指定 + GEMINI_API_KEY がある時だけ。
            # compile_blueprint_llm は失敗時ルートAへ自動フォールバックする
            route = "rule"
            if llm and os.environ.get("GEMINI_API_KEY"):
                bp, route = compile_blueprint_llm(text)
            else:
                bp = compile_blueprint(text)
            _set(job_id, route=route)
            workdir.mkdir(parents=True, exist_ok=True)
            bp_path = workdir / "blueprint.json"
            bp_path.write_text(json.dumps(bp, ensure_ascii=False, indent=2), encoding="utf-8")

            _set(job_id, status="forging", phase="鍛造中(装甲を成形し適合審査しています)",
                 blueprint_id=bp["blueprint_id"])
            fb_dir = workdir / "fullbody"
            cmd = [find_blender(), "--background", "--python", str(ASSEMBLER), "--",
                   "--blueprint", str(bp_path), "--out-dir", str(fb_dir),
                   "--quality", "preview", "--label", bp["blueprint_id"],
                   "--export-glb", "1", "--export-vrm", "1",
                   "--render-views", "soft"]
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=1500)
            result = None
            for line in (proc.stdout or "").splitlines():
                if line.startswith("ARMOR_FULLBODY_RESULT:"):
                    result = json.loads(line.split(":", 1)[1])
                    break
            if result is None or not result.get("ok"):
                tail = (proc.stdout or "")[-600:] + (proc.stderr or "")[-300:]
                raise RuntimeError(f"assembler failed: {tail}")

            _set(job_id, status="uploading", phase="保管庫へ格納しています")
            files: dict[str, Path] = {}
            glb = result.get("glb") or ""
            if glb and Path(glb).exists():
                files["assembly"] = Path(glb)
            vrm = result.get("vrm") or ""
            if vrm and Path(vrm).exists():
                files["vrm"] = Path(vrm)
            if VRMA_ASSET.exists():
                files["vrma"] = VRMA_ASSET
            if "assembly" not in files:
                raise RuntimeError("no assembly.glb produced")

            code = _next_code()
            for k, p in files.items():
                ct = "model/gltf-binary" if p.suffix in (".glb", ".vrm", ".vrma") \
                    else "application/octet-stream"
                upload_supabase(f"{code}/{k}{p.suffix}", p.read_bytes(), ct)
            manifest = {
                "package_version": "suit-package.v1",
                "recall_code": code,
                "blueprint_id": bp["blueprint_id"],
                "design_intent": text,
                "palette": bp.get("palette", {}),
                "files": {k: f"{k}{p.suffix}" for k, p in files.items()},
                "triangles": {k: glb_triangles(p) for k, p in files.items()
                              if p.suffix == ".glb"},
                "fit_summary": result.get("fit_summary", {}),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            upload_supabase(f"{code}/suit-package.json",
                            json.dumps(manifest, ensure_ascii=False).encode("utf-8"),
                            "application/json")
            register_code(manifest)
            fs = result.get("fit_summary", {})
            _set(job_id, status="done", code=code, phase="蒸着準備完了",
                 fit=f"{fs.get('parts_pass', '?')}/{fs.get('parts_total', '?')}")
        except Exception as exc:  # noqa: BLE001
            _set(job_id, status="error", error=str(exc)[-500:])
        finally:
            shutil.rmtree(workdir, ignore_errors=True)


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # Cloud Run のログを1行に
        print(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._json({"ok": True})
            return
        if parsed.path == "/job":
            job_id = (parse_qs(parsed.query).get("id") or [""])[0]
            with _JOBS_LOCK:
                job = dict(_JOBS.get(job_id, {"status": "unknown"}))
            self._json(job)
            return
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/forge":
            self.send_error(404)
            return
        if TOKEN and self.headers.get("X-Forge-Token", "") != TOKEN:
            self._json({"ok": False, "error": "forbidden"}, 403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json({"ok": False, "error": "bad json"}, 400)
            return
        text = str(payload.get("text", "")).strip()[:MAX_TEXT]
        if not text:
            self._json({"ok": False, "error": "言葉を入力してください"}, 400)
            return
        llm = bool(payload.get("llm"))
        job_id = uuid.uuid4().hex[:12]
        _set(job_id, status="queued", phase="鍛造炉の順番待ち", text=text[:80])
        threading.Thread(target=_forge_job, args=(job_id, text, llm), daemon=True).start()
        self._json({"ok": True, "job_id": job_id})


def main() -> None:
    # ローカル実行時はリポ直下 .env を自動読込(既存の環境変数優先)
    try:
        from henshin._env import load_dotenv
        for k, v in load_dotenv().items():
            os.environ.setdefault(k, v)
    except Exception:  # noqa: BLE001
        pass
    for req_key in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        if not os.environ.get(req_key):
            raise SystemExit(f"env {req_key} is required")
    port = int(os.environ.get("PORT", "8080"))
    print(f"FORGE_READY: port={port} blender={find_blender()}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
