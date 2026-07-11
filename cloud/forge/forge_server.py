"""蒸着執行録 鍛造工場 API — Cloud Run 用ジョブサーバ。

言葉 → 設計図(ルートA) → Blenderヘッドレス鍛造 → Supabase格納 → 呼出符発行。
Vercel の /api/forge がここへプロキシする(ブラウザ直叩きはさせない)。

  POST /forge   {"text": "..."}  + X-Forge-Token   → {"job_id": "..."}
  GET  /job?id=<job_id>                            → {"status", "phase", "code", ...}
  GET  /health                                     → ok
  (※/healthz は不可 — Googleフロントエンドが run.app 上で予約していて
    コンテナに届く前に404を返す。2026-07-11実測)

Blenderは重いのでビルドは直列(_BUILD_LOCK)。Cloud Run は
--max-instances 1 --no-cpu-throttling で運用する(応答後もスレッドが走る)。
env: SUPABASE_URL / SUPABASE_SERVICE_KEY / FORGE_TOKEN / HENSHIN_BLENDER_EXE
"""
from __future__ import annotations

import glob
import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
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


# 紛らわしい 0/O/1/I を除いた32文字。5桁で約3,350万通り —
# 連番(GAVAI-0001)はURL推測で他人の鎧に届いてしまう(2026-07-11指摘)
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _code_taken(code: str) -> bool:
    base = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_KEY"]
    req = urllib.request.Request(
        f"{base}/rest/v1/recall_codes?select=recall_code&recall_code=eq.{code}",
        headers={"apikey": key, "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return bool(json.load(resp))


def _next_code() -> str:
    """呼出符の発行: 推測不能なランダム5桁英数字(衝突は台帳照会で回避)。"""
    for _ in range(8):
        code = "GAVAI-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(5))
        if not _code_taken(code):
            return code
    raise RuntimeError("recall code allocation failed (collisions)")


def _update_gallery(manifest: dict) -> None:
    """鍛造記録 — 直近の鎧をトップページの一覧に載せる(公開gallery.json)。
    失敗しても鍛造自体は成立させる(呼び出し側でtry/except)。"""
    base = os.environ["SUPABASE_URL"].rstrip("/")
    entry = {
        "code": manifest["recall_code"],
        "blueprint_id": manifest["blueprint_id"],
        "intent": str(manifest.get("design_intent", ""))[:40],
        "palette": manifest.get("palette", {}),
        "created_at": manifest["created_at"],
    }
    items: list = []
    try:
        with urllib.request.urlopen(
                f"{base}/storage/v1/object/public/suits/gallery.json", timeout=15) as r:
            items = json.load(r)
    except Exception:  # noqa: BLE001 — 初回は無いのが正常
        items = []
    items = [entry] + [i for i in items if i.get("code") != entry["code"]]
    upload_supabase("gallery.json",
                    json.dumps(items[:24], ensure_ascii=False).encode("utf-8"),
                    "application/json")


def _forge_job(job_id: str, text: str) -> None:
    with _BUILD_LOCK:
        workdir = WORK / job_id
        timings: dict[str, float] = {}
        t0 = time.time()
        try:
            _set(job_id, status="forging", stage=1,
                 phase="設計局AIが言葉を解釈しています")
            # 言葉→設計図の解釈はコンセプトの肝 — ルートB(Gemini)が必須本線
            # (2026-07-11方針)。モデルは GEMINI_TEXT_MODEL で差し替え可能。
            # Gemini側の障害時のみ compile_blueprint_llm が規範解釈(ルートA)へ
            # 自動フォールバックし、route にその事実が記録される
            bp, route = compile_blueprint_llm(text)
            timings["interpret"] = round(time.time() - t0, 1)
            _set(job_id, route=route, timings=dict(timings))
            workdir.mkdir(parents=True, exist_ok=True)
            bp_path = workdir / "blueprint.json"
            bp_path.write_text(json.dumps(bp, ensure_ascii=False, indent=2), encoding="utf-8")

            t1 = time.time()
            _set(job_id, status="forging", stage=2,
                 phase="鍛造中(装甲を成形し適合審査しています)",
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
            timings["build"] = round(time.time() - t1, 1)

            t2 = time.time()
            _set(job_id, status="uploading", stage=3,
                 phase="保管庫へ格納しています", timings=dict(timings))
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
            try:
                _update_gallery(manifest)
            except Exception as exc:  # noqa: BLE001
                print(f"GALLERY_UPDATE_FAILED: {exc}")
            timings["upload"] = round(time.time() - t2, 1)
            timings["total"] = round(time.time() - t0, 1)
            fs = result.get("fit_summary", {})
            _set(job_id, status="done", stage=4, code=code, phase="蒸着準備完了",
                 timings=dict(timings),
                 fit=f"{fs.get('parts_pass', '?')}/{fs.get('parts_total', '?')}")
            print(f"FORGE_DONE: {code} timings={json.dumps(timings)}")
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
        if parsed.path in ("/health", "/healthz"):  # healthz はローカル専用(GFEが予約)
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
        job_id = uuid.uuid4().hex[:12]
        _set(job_id, status="queued", phase="鍛造炉の順番待ち", text=text[:80])
        threading.Thread(target=_forge_job, args=(job_id, text), daemon=True).start()
        self._json({"ok": True, "job_id": job_id})


def main() -> None:
    # ローカル実行時はリポ直下 .env を自動読込(既存の環境変数優先)
    try:
        from henshin._env import load_dotenv
        for k, v in load_dotenv().items():
            os.environ.setdefault(k, v)
    except Exception:  # noqa: BLE001
        pass
    # GEMINI_API_KEY も必須: 言葉の解釈(ルートB)がコンセプトの肝であるため。
    # 実行時のGemini障害はフォールバックで凌ぐが、鍵なし運用は契約違反として起動拒否
    for req_key in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GEMINI_API_KEY"):
        val = os.environ.get(req_key, "")
        if not val or val.startswith("YOUR_"):
            raise SystemExit(f"env {req_key} is required")
    port = int(os.environ.get("PORT", "8080"))
    model = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
    print(f"FORGE_READY: port={port} blender={find_blender()} interpreter={model}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
