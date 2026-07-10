"""Armor Forge check UI — type a message, press 生成, watch the suit build.

A small stdlib HTTP server (no deps) that exposes the three engine layers to a
browser so you can iterate on wording and see, in real time:

  Layer 1  text -> ArmorBlueprint decode (instant; emotion axes, palette, parts)
  Layer 2  build parts -> GLB + render (Blender, ~10s/part)
  Layer 3  assemble the full suit on the VRM body + fit audit (Blender, ~1min)

Run from the repo root (D:/personal_dev/gavai-henshin/gavai-henshin):

  python tools/armor_lab_server.py            # serves http://localhost:8020/
  python tools/armor_lab_server.py --port 8030

Blender is auto-discovered (HENSHIN_BLENDER_EXE env -> PATH -> Program Files).
Renders are written under output/blueprint-armor/lab-ui/<blueprint_id>/.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from henshin.armor_blueprint import AXES, compile_blueprint, compile_blueprint_llm  # noqa: E402

RENDER_ROOT = REPO_ROOT / "output" / "blueprint-armor" / "lab-ui"
VENDOR_ROOT = REPO_ROOT / "viewer" / "body-fit" / "vendor" / "three"
BUILDER = REPO_ROOT / "tools" / "blender" / "armor_blueprint_builder.py"
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

_BLENDER_LOCK = threading.Lock()  # Blender is heavy; run one job at a time
_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()


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


def blueprint_summary(bp: dict) -> dict:
    parts = []
    for p in bp.get("parts", []):
        surf = p.get("surface", {})
        parts.append({
            "module": p["module"],
            "cross": p.get("silhouette", {}).get("cross_section", "-"),
            "rings": len(surf.get("ring_grooves", [])),
            "meridians": len(surf.get("meridian_grooves", [])),
            "features": [f.get("kind") for f in p.get("features", [])],
        })
    return {
        "blueprint_id": bp["blueprint_id"],
        "design_intent": bp.get("design_intent", ""),
        "axes": [{"name": a, "value": bp.get("emotion_axes", {}).get(a, 0.0)}
                 for a in AXES if bp.get("emotion_axes", {}).get(a, 0.0) > 0],
        "palette": bp.get("palette", {}),
        "parts": parts,
    }


def _rel_render(path: str) -> str | None:
    try:
        rel = Path(path).resolve().relative_to(RENDER_ROOT.resolve())
        return "/r/" + str(rel).replace("\\", "/")
    except ValueError:
        return None


def _run_blender(cmd: list[str], marker: str) -> dict | None:
    with _BLENDER_LOCK:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (proc.stdout or "").splitlines():
        if line.startswith(marker):
            return json.loads(line.split(":", 1)[1])
    raise RuntimeError((proc.stdout or "")[-1500:] + "\n" + (proc.stderr or "")[-800:])


def _build_job(job_id: str, blueprint_id: str, modules: str) -> None:
    out_dir = RENDER_ROOT / blueprint_id
    bp_path = out_dir / "blueprint.json"
    cmd = [find_blender(), "--background", "--factory-startup", "--python", str(BUILDER), "--",
           "--blueprint", str(bp_path), "--out-dir", str(out_dir), "--quality", "preview", "--render", "1"]
    if modules and modules != "all":
        cmd += ["--modules", modules]
    try:
        result = _run_blender(cmd, "ARMOR_BLUEPRINT_RESULT:")
        renders = []
        for m in result["modules"]:
            png = out_dir / m["module"] / "preview" / f"{m['module']}_3q.png"
            url = _rel_render(str(png))
            if url and png.exists():
                renders.append({"label": m["module"], "url": url,
                                "meta": f"{m['triangles']} tris"})
        _set_job(job_id, status="done", renders=renders)
    except Exception as exc:  # noqa: BLE001
        _set_job(job_id, status="error", error=str(exc)[-800:])


def _assemble_job(job_id: str, blueprint_id: str) -> None:
    out_dir = RENDER_ROOT / blueprint_id
    bp_path = out_dir / "blueprint.json"
    fb_dir = out_dir / "fullbody"
    cmd = [find_blender(), "--background", "--python", str(ASSEMBLER), "--",
           "--blueprint", str(bp_path), "--out-dir", str(fb_dir), "--quality", "preview",
           "--label", blueprint_id, "--export-glb", "1",
           "--export-skinned-glb", "1", "--export-vrm", "1"]
    try:
        result = _run_blender(cmd, "ARMOR_FULLBODY_RESULT:")
        fs = result.get("fit_summary", {})
        renders = []
        for name, path in result.get("views", {}).items():
            url = _rel_render(path)
            if url:
                renders.append({"label": name, "url": url, "meta": ""})
        glb_url = _rel_render(result.get("glb", "")) if result.get("glb") else None
        skinned_url = _rel_render(result.get("skinned_glb", "")) if result.get("skinned_glb") else None
        vrm_url = _rel_render(result.get("vrm", "")) if result.get("vrm") else None
        _set_job(job_id, status="done", renders=renders, glb=glb_url,
                 skinned=skinned_url, vrm=vrm_url,
                 fit=f"パーツ適合 {fs.get('parts_pass','?')}/{fs.get('parts_total','?')} ・ "
                     f"関節 {fs.get('joints_pass','?')}/{fs.get('joints_total','?')}")
    except Exception as exc:  # noqa: BLE001
        _set_job(job_id, status="error", error=str(exc)[-800:])


def _set_job(job_id: str, **fields) -> None:
    with _JOBS_LOCK:
        _JOBS.setdefault(job_id, {}).update(fields)


def _history_entries(limit: int = 24) -> list[dict]:
    """蒸着庫 — 過去の全身装着をディスクから復元する。

    ジョブ一覧はメモリ保持のみだったため、サーバ再起動でVRMダウンロード等の
    導線が全部消えていた(2026-07-10ユーザー報告の真因)。assembly.json が
    物証としてディスクに残っているので、そこから一覧を再構成する。"""
    entries: list[dict] = []
    if not RENDER_ROOT.is_dir():
        return entries
    for bp_dir in RENDER_ROOT.iterdir():
        fb = bp_dir / "fullbody"
        if not fb.is_dir():
            continue
        for aj in fb.glob("*.assembly.json"):
            try:
                data = json.loads(aj.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            renders = []
            for name, path in (data.get("views") or {}).items():
                url = _rel_render(path)
                if url and Path(path).exists():
                    renders.append({"label": name, "url": url, "meta": ""})

            def _url(key: str):
                p = data.get(key) or ""
                return _rel_render(p) if p and Path(p).exists() else None

            fs = data.get("fit_summary", {})
            entries.append({
                "status": "done",
                "blueprint_id": data.get("blueprint") or bp_dir.name,
                "mtime": aj.stat().st_mtime,
                "renders": renders,
                "glb": _url("glb"),
                "skinned": _url("skinned_glb"),
                "vrm": _url("vrm"),
                "fit": f"パーツ適合 {fs.get('parts_pass', '?')}/{fs.get('parts_total', '?')} ・ "
                       f"関節 {fs.get('joints_pass', '?')}/{fs.get('joints_total', '?')}",
            })
    entries.sort(key=lambda e: e["mtime"], reverse=True)
    return entries[:limit]


def _new_job(kind: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    _set_job(job_id, status="running", kind=kind, renders=[], error=None)
    return job_id


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # quiet
        return

    def _json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.startswith("/r/") or parsed.path.startswith("/vendor/"):
            if parsed.path.startswith("/r/"):
                root, rel = RENDER_ROOT, parsed.path[len("/r/"):]
            else:
                root, rel = VENDOR_ROOT, parsed.path[len("/vendor/"):]
            target = (root / rel).resolve()
            if root.resolve() not in target.parents or not target.is_file():
                self.send_error(404)
                return
            mime = {".png": "image/png", ".glb": "model/gltf-binary",
                    ".vrm": "application/octet-stream",
                    ".vrma": "model/gltf-binary",
                    ".js": "text/javascript; charset=utf-8",
                    ".json": "application/json; charset=utf-8"}.get(target.suffix.lower())
            if mime is None:
                self.send_error(404)
                return
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if parsed.path == "/api/job":
            job_id = (parse_qs(parsed.query).get("id") or [""])[0]
            with _JOBS_LOCK:
                job = dict(_JOBS.get(job_id, {"status": "unknown"}))
            self._json(job)
            return
        if parsed.path == "/api/history":
            self._json({"ok": True, "suits": _history_entries()})
            return
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json({"ok": False, "error": "bad json"}, 400)
            return

        if parsed.path == "/api/compile":
            text = str(payload.get("text", "")).strip()
            if not text:
                self._json({"ok": False, "error": "テキストを入力してください"}, 400)
                return
            route = "rule"
            if payload.get("llm"):
                bp, route = compile_blueprint_llm(text, modules=ALL_MODULES)
            else:
                bp = compile_blueprint(text, modules=ALL_MODULES)
            out_dir = RENDER_ROOT / bp["blueprint_id"]
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "blueprint.json").write_text(
                json.dumps(bp, ensure_ascii=False, indent=2), encoding="utf-8")
            self._json({"ok": True, "route": route, "summary": blueprint_summary(bp), "blueprint": bp})
            return

        if parsed.path in ("/api/build", "/api/assemble"):
            blueprint_id = str(payload.get("blueprint_id", "")).strip()
            if not (RENDER_ROOT / blueprint_id / "blueprint.json").exists():
                self._json({"ok": False, "error": "先に生成してください"}, 400)
                return
            if parsed.path == "/api/build":
                job_id = _new_job("build")
                modules = str(payload.get("modules", "helmet,chest"))
                threading.Thread(target=_build_job, args=(job_id, blueprint_id, modules), daemon=True).start()
            else:
                job_id = _new_job("assemble")
                threading.Thread(target=_assemble_job, args=(job_id, blueprint_id), daemon=True).start()
            self._json({"ok": True, "job_id": job_id})
            return

        self.send_error(404)


PAGE = r"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>蒸着執行録 — ARMOR FORGE CHECK</title>
<style>
:root{
  --bg:#0B1520; --panel:#101E2E; --panel2:#0E1A28; --line:#28425C; --faint:#1A2E42;
  --cyan:#5FC7E8; --cyan-dim:#3E7E9C; --text:#C6D6E3; --dim:#7E93A6;
  --oath:#FFA23F; --ok:#5ED89C; --refuse:#E05A70;
  --mono:"Consolas","SFMono-Regular",Menlo,monospace;
  --jp:"Hiragino Kaku Gothic ProN","Yu Gothic Medium",Meiryo,sans-serif;
}
*{box-sizing:border-box}
body{margin:0;background:
  repeating-linear-gradient(0deg,transparent 0 47px,rgba(95,199,232,.04) 47px 48px),
  repeating-linear-gradient(90deg,transparent 0 47px,rgba(95,199,232,.04) 47px 48px),var(--bg);
  color:var(--text);font-family:var(--jp);line-height:1.7;padding:0 18px 80px}
.wrap{max-width:1080px;margin:0 auto}
header{border:1px solid var(--line);background:linear-gradient(180deg,var(--panel),var(--panel2));
  margin-top:28px;padding:20px 26px;position:relative}
header::before{content:"";position:absolute;inset:5px;border:1px solid var(--faint);pointer-events:none}
h1{margin:0;font-size:22px;letter-spacing:.08em;color:#E8F2F9}
.sub{font-family:var(--mono);font-size:11px;letter-spacing:.18em;color:var(--cyan-dim);text-transform:uppercase;margin-top:4px}
.inputrow{display:flex;gap:12px;margin-top:20px;align-items:stretch}
textarea{flex:1;background:var(--panel2);border:1px solid var(--line);color:var(--text);
  font-family:var(--jp);font-size:15px;padding:12px 14px;resize:vertical;min-height:58px;border-radius:2px}
textarea:focus{outline:none;border-color:var(--cyan-dim)}
button{font-family:var(--mono);letter-spacing:.14em;cursor:pointer;border:1px solid var(--cyan-dim);
  background:var(--panel);color:var(--cyan);padding:0 22px;font-size:14px;border-radius:2px;white-space:nowrap}
button:hover{background:#12263a}
button:disabled{opacity:.4;cursor:default}
button.go{border-color:var(--oath);color:var(--oath);font-size:16px;font-weight:700}
button.go:hover{background:rgba(255,162,63,.1)}
.hint{font-size:12px;color:var(--dim);margin-top:8px}
.hint b{color:var(--cyan-dim);cursor:pointer}
.grid{display:grid;grid-template-columns:340px 1fr;gap:18px;margin-top:22px}
@media(max-width:820px){.grid{grid-template-columns:1fr}}
.card{border:1px solid var(--line);background:var(--panel);padding:16px 18px}
.card h2{margin:0 0 12px;font-family:var(--mono);font-size:11px;font-weight:400;letter-spacing:.2em;
  color:var(--cyan-dim);text-transform:uppercase}
.bpid{font-family:var(--mono);font-size:13px;color:var(--oath);margin-bottom:10px;word-break:break-all}
.axis{display:flex;align-items:center;gap:8px;margin:5px 0;font-family:var(--mono);font-size:12px}
.axis .n{width:64px;color:var(--dim)}
.bar{flex:1;height:9px;background:var(--faint);position:relative;overflow:hidden}
.bar i{position:absolute;left:0;top:0;bottom:0;background:var(--cyan);display:block}
.axis .v{width:34px;text-align:right;color:var(--text)}
.pal{display:flex;gap:6px;margin:10px 0 4px;flex-wrap:wrap}
.sw{display:flex;flex-direction:column;align-items:center;font-family:var(--mono);font-size:9px;color:var(--dim)}
.sw span{width:40px;height:26px;border:1px solid var(--line);margin-bottom:3px}
.parts{margin-top:10px;border-top:1px solid var(--faint);max-height:340px;overflow:auto}
.prow{display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-bottom:1px solid var(--faint);font-size:12px}
.prow .m{font-family:var(--mono);color:var(--text)}
.prow .f{color:var(--cyan-dim);font-size:11px;text-align:right}
.buildbar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.status{font-family:var(--mono);font-size:12px;color:var(--dim);margin-bottom:12px;min-height:18px}
.status.run{color:var(--oath)} .status.ok{color:var(--ok)} .status.err{color:var(--refuse)}
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px}
.tile{border:1px solid var(--line);background:var(--panel2)}
.tile img{width:100%;display:block;background:#0d1a28}
.tile .cap{font-family:var(--mono);font-size:11px;color:var(--dim);padding:6px 8px;display:flex;justify-content:space-between}
.tile .cap b{color:var(--cyan)}
.empty{color:var(--dim);font-size:13px;padding:20px 0;text-align:center}
.spin{display:inline-block;width:10px;height:10px;border:2px solid var(--cyan-dim);border-top-color:transparent;
  border-radius:50%;animation:s .8s linear infinite;vertical-align:-1px;margin-right:6px}
@keyframes s{to{transform:rotate(360deg)}}
.jsonlink{font-family:var(--mono);font-size:11px;color:var(--cyan-dim);margin-top:8px;word-break:break-all}
</style>
<script type="importmap">
{"imports": {"three": "/vendor/build/three.module.js", "three/addons/": "/vendor/examples/jsm/"}}
</script>
</head>
<body><div class="wrap">
<header>
  <h1>蒸着執行録 — 装甲設計 検証コンソール</h1>
  <div class="sub">ARMOR FORGE CHECK · text → blueprint → 3D</div>
  <div class="inputrow">
    <textarea id="text" placeholder="思い・意匠を入力（例：メタル系宇宙刑事。銀の装甲、青い誓いの光。仲間を守る盾、研ぎ澄まされた警戒。）"></textarea>
    <button class="go" id="go" onclick="forge()">生成</button>
  </div>
  <div class="hint">例：
    <b onclick="ex('闘志。赤い牙を剥き、前へ踏み込む誓い。')">闘志</b> ·
    <b onclick="ex('守護。仲間を包む盾、厚い胸甲。緑の誓い。')">守護</b> ·
    <b onclick="ex('哀傷。静かな青、長い残光を引く鎮魂。')">哀傷</b> ·
    <b onclick="ex('メタル系宇宙刑事。銀の装甲、青い光。守護と警戒。')">メタル系</b>
    &nbsp;&nbsp;<label style="cursor:pointer"><input type="checkbox" id="use_llm">
    生成AI解釈（ルートB / Gemini 1コール・失敗時はルールに自動フォールバック）</label>
  </div>
</header>

<div class="grid">
  <div class="card">
    <h2>設計図 解読 / Blueprint</h2>
    <div id="decode"><div class="empty">「生成」で言葉が設計図になります</div></div>
  </div>
  <div class="card">
    <h2>3D 構築 / Render</h2>
    <div class="buildbar">
      <button id="b_hc" onclick="build('helmet,chest')" disabled>兜+胸をビルド</button>
      <button id="b_all" onclick="build('all')" disabled>全18部位ビルド</button>
      <button id="b_asm" onclick="assemble()" disabled>全身装着（適合審査）</button>
    </div>
    <div class="status" id="status"></div>
    <div class="gallery" id="gallery"><div class="empty">ビルドすると3Dレンダがここに出ます</div></div>
  </div>
</div>

<div class="card" id="viewer_card" style="margin-top:18px;display:none">
  <h2>3D ビューア / ORBIT — ドラッグで回転・ホイールでズーム</h2>
  <div style="display:flex;gap:10px;margin-bottom:10px">
    <button id="b_deposit" onclick="window.V3D && V3D.deposit()">蒸着リプレイ</button>
    <button id="b_henshin" onclick="window.V3D && V3D.henshin()">ヘンシン・モーション</button>
    <a id="b_vrm" href="#" download style="display:none;font-family:var(--mono);font-size:13px;white-space:nowrap;
       color:var(--oath);border:1px solid var(--oath);padding:6px 14px;text-decoration:none">VRMをダウンロード</a>
    <span class="status" id="v3d_status" style="align-self:center"></span>
  </div>
  <div id="history" style="display:none;gap:6px;flex-wrap:wrap;margin-bottom:8px;align-items:center"></div>
  <div id="part_nav" style="display:none;gap:6px;flex-wrap:wrap;margin-bottom:8px"></div>
  <div id="v3d_wrap" style="width:100%;height:560px;border:1px solid var(--line);background:#0a141f"></div>
</div>

<div class="card" id="track_card" style="margin-top:18px;display:none">
  <h2>トラッキング実験 / WEBCAM — 映像は表示せず、点群のみ描画</h2>
  <div style="display:flex;gap:10px;margin-bottom:10px;flex-wrap:wrap;align-items:center">
    <button id="b_track" onclick="window.TRK && TRK.toggle()">トラッキング開始</button>
    <label style="cursor:pointer;font-size:12px;color:var(--text)">
      <input type="checkbox" id="trk_mirror" checked> 鏡像</label>
    <label style="cursor:pointer;font-size:12px;color:var(--text)">
      <input type="checkbox" id="trk_torso" checked> 胴体駆動</label>
    <label style="cursor:pointer;font-size:12px;color:var(--text)">
      <input type="checkbox" id="trk_face"> 顔詳細(任意)</label>
    <span class="status" id="trk_status" style="align-self:center"></span>
  </div>
  <div style="display:flex;gap:12px;flex-wrap:wrap">
    <canvas id="trk_canvas" width="640" height="480"
      style="border:1px solid var(--line);background:#04080d;max-width:48%;flex:1"></canvas>
    <div style="flex:1;min-width:300px;font-size:12px;color:var(--dim);line-height:1.9">
      体 33点のランドマークを点群描画します（カメラ映像は一切表示・保存しません）。
      変身後はマスクで表情は出ないため、<b>体のトラッキングを優先</b>し、
      頭の向きは体ランドマーク（鼻・両耳）から推定します。「顔詳細」をONにすると
      478点の顔メッシュも追加取得します（初回+15MB）。<br>
      腕の向きはモデルの<b>バインドポーズから実測したレスト方向</b>基準で駆動するため、
      A/Tポーズどちらのモデルでも破綻しません。<br>
      <span style="color:var(--cyan-dim)">オレンジ=体 / 白線=骨格 / シアン=顔（任意）</span>
    </div>
  </div>
</div>
</div>

<script>
let CURRENT = null;
function ex(t){ document.getElementById('text').value = t; forge(); }
async function post(url, body){
  const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  return r.json();
}
function setStatus(msg, cls){ const s=document.getElementById('status'); s.textContent=msg; s.className='status '+(cls||''); }
function enableBuild(on){ for(const id of ['b_hc','b_all','b_asm']) document.getElementById(id).disabled=!on; }

async function forge(){
  const text = document.getElementById('text').value.trim();
  if(!text) return;
  const llm = document.getElementById('use_llm').checked;
  document.getElementById('go').disabled = true;
  setStatus(llm ? '設計局AIが解釈中… (Gemini ~10-60s)' : '', llm ? 'run' : '');
  const res = await post('/api/compile', {text, llm});
  document.getElementById('go').disabled = false;
  if(!res.ok){ setStatus(res.error||'error','err'); return; }
  CURRENT = res.summary.blueprint_id;
  renderDecode(res.summary);
  const r = res.route || 'rule';
  setStatus(r.startsWith('llm') ? '設計局AI解釈 ('+r+')' :
            r.startsWith('rule_fallback') ? 'ルールへフォールバック ('+r.split(':').slice(0,2).join(':')+')' : '',
            r.startsWith('llm') ? 'ok' : '');
  enableBuild(true);
  document.getElementById('gallery').innerHTML = '<div class="empty">ビルドすると3Dレンダがここに出ます</div>';
}

function renderDecode(s){
  let h = '<div class="bpid">'+s.blueprint_id+'</div>';
  for(const a of s.axes){
    h += '<div class="axis"><span class="n">'+a.name+'</span><span class="bar"><i style="width:'
       +Math.round(a.value*100)+'%"></i></span><span class="v">'+a.value.toFixed(2)+'</span></div>';
  }
  h += '<div class="pal">';
  for(const [k,v] of Object.entries(s.palette)){
    h += '<div class="sw"><span style="background:'+v+'"></span>'+k.replace('_surface','').slice(0,6)+'</div>';
  }
  h += '</div><div class="parts">';
  for(const p of s.parts){
    const f = p.features.length? p.features.join(',') : '—';
    h += '<div class="prow"><span class="m">'+p.module+'</span><span class="f">'+p.cross
       +' · 溝'+p.rings+'/'+p.meridians+' · '+f+'</span></div>';
  }
  h += '</div><div class="jsonlink">設計図JSON: output/blueprint-armor/lab-ui/'+s.blueprint_id+'/blueprint.json</div>';
  document.getElementById('decode').innerHTML = h;
}

async function poll(job_id, kind){
  const r = await fetch('/api/job?id='+job_id);
  const j = await r.json();
  if(j.status === 'running'){
    setStatus((kind==='assemble'?'全身装着を構築中…':'3Dビルド中…')+' (Blender ~'+(kind==='assemble'?'60':'10-40')+'s)','run');
    document.getElementById('status').innerHTML = '<span class="spin"></span>'+document.getElementById('status').textContent;
    setTimeout(()=>poll(job_id, kind), 1600);
    return;
  }
  if(j.status === 'error'){ setStatus('起動拒否 / error: '+(j.error||'').split('\n').pop().slice(0,160),'err'); enableBuild(true); return; }
  showResult(j);
  enableBuild(true);
}

// 完了ジョブ/蒸着庫エントリ共通の結果表示。VRMダウンロードはここで常設される
function showResult(j, fromVault){
  const fit = j.fit ? (' · 適合審査 '+j.fit) : '';
  setStatus((fromVault ? '蒸着庫から復元: '+(j.blueprint_id||'') : '構築完了')+fit, 'ok');
  showRenders(j.renders||[]);
  const model = j.skinned || j.glb;
  if(model && window.V3D){ V3D.show(model); }
  if(j.skinned){ document.getElementById('track_card').style.display='block'; window.TRK && TRK.setModelReady(); }
  const a = document.getElementById('b_vrm');
  if(j.vrm){ a.href=j.vrm; a.download=(j.blueprint_id||'suit')+'.vrm'; a.style.display='inline-block'; }
  else { a.style.display='none'; }
}

// 蒸着庫: サーバ再起動後も過去の鎧(とVRMダウンロード)をディスクから復元
async function loadVault(){
  try{
    const r = await fetch('/api/history');
    const h = await r.json();
    if(!h.ok || !h.suits || !h.suits.length) return;
    const box = document.getElementById('history');
    box.innerHTML = '<span style="font-size:11px;color:var(--dim)">蒸着庫:</span>'
      + h.suits.map((s,i)=>'<button class="hist" data-i="'+i+'" style="font-size:12px">'
                           +s.blueprint_id+'</button>').join('');
    box.style.display = 'flex';
    box.querySelectorAll('button.hist').forEach(b => {
      b.onclick = () => showResult(h.suits[+b.dataset.i], true);
    });
    showResult(h.suits[0], true);  // 最新の鎧を自動復元(空のラボを開かない)
  }catch(e){ console.warn('vault load failed', e); }
}
window.addEventListener('load', loadVault);

function showRenders(renders){
  if(!renders.length){ document.getElementById('gallery').innerHTML='<div class="empty">レンダなし</div>'; return; }
  let h='';
  for(const r of renders){
    h += '<div class="tile"><img src="'+r.url+'?t='+Date.now()+'" alt="'+r.label+'">'
       + '<div class="cap"><b>'+r.label+'</b><span>'+(r.meta||'')+'</span></div></div>';
  }
  document.getElementById('gallery').innerHTML = h;
}

async function build(modules){
  if(!CURRENT) return;
  enableBuild(false);
  setStatus('ジョブ投入…','run');
  const res = await post('/api/build', {blueprint_id:CURRENT, modules});
  if(!res.ok){ setStatus(res.error||'error','err'); enableBuild(true); return; }
  poll(res.job_id, 'build');
}
async function assemble(){
  if(!CURRENT) return;
  enableBuild(false);
  setStatus('ジョブ投入…','run');
  const res = await post('/api/assemble', {blueprint_id:CURRENT});
  if(!res.ok){ setStatus(res.error||'error','err'); enableBuild(true); return; }
  poll(res.job_id, 'assemble');
}
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

let scene, camera, renderer, controls, suit = null, armorMeshes = [], particles = null;
let depositT = -1;

function ensure(){
  if(renderer) return;
  const wrap = document.getElementById('v3d_wrap');
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a141f);
  camera = new THREE.PerspectiveCamera(45, wrap.clientWidth/wrap.clientHeight, 0.05, 50);
  camera.position.set(1.3, 1.5, 2.4);
  renderer = new THREE.WebGLRenderer({antialias:true});
  renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio||1));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  wrap.appendChild(renderer.domElement);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envScene = new RoomEnvironment();
  scene.environment = pmrem.fromScene(envScene, 0.04).texture;
  envScene.dispose(); pmrem.dispose();
  controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0.9, 0);
  const key = new THREE.DirectionalLight(0xffffff, 1.4); key.position.set(2,3,-2); scene.add(key);
  const rim = new THREE.DirectionalLight(0x5fc7e8, 0.7); rim.position.set(-2,2,2); scene.add(rim);
  scene.add(new THREE.AmbientLight(0x8899aa, 0.15));
  const grid = new THREE.GridHelper(4, 20, 0x28425c, 0x1a2e42); scene.add(grid);
  window.addEventListener('resize', () => {
    camera.aspect = wrap.clientWidth/wrap.clientHeight; camera.updateProjectionMatrix();
    renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  });
  animate();
}

function animate(){
  requestAnimationFrame(animate);
  controls && controls.update();
  if(mixer) mixer.update(clock.getDelta());
  if(depositT >= 0){
    depositT = Math.min(1, depositT + 0.008);
    const n = armorMeshes.length;
    armorMeshes.forEach((m, i) => {
      const start = (i / Math.max(1,n)) * 0.55;
      const k = Math.max(0, Math.min(1, (depositT - start) / 0.4));
      m.material.opacity = k;
      m.material.emissiveIntensity = (m.userData.baseEmissive||0) + (1-k)*2.2 + Math.sin(depositT*40+i)*0.15*(1-k);
      m.visible = k > 0.01;
    });
    if(particles){
      particles.material.opacity = Math.max(0, 1 - depositT*1.2);
      particles.rotation.y += 0.02;
      particles.scale.setScalar(Math.max(0.15, 1 - depositT*0.8));
    }
    if(depositT >= 1){
      depositT = -1;
      armorMeshes.forEach(m => { m.material.transparent = false; m.material.opacity = 1;
        m.material.emissiveIntensity = m.userData.baseEmissive||0; });
      if(particles){ scene.remove(particles); particles = null; }
      document.getElementById('v3d_status').textContent = 'SEAL: APPLIED — 蒸着完了';
    }
  }
  renderer.render(scene, camera);
}

function show(url){
  document.getElementById('viewer_card').style.display = 'block';
  ensure();
  // the wrap may have been display:none at first init — resync the size
  const wrap = document.getElementById('v3d_wrap');
  if(renderer && wrap.clientWidth > 0){
    camera.aspect = wrap.clientWidth / wrap.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  }
  document.getElementById('v3d_status').textContent = 'モデル読込中…';
  if(suit){ scene.remove(suit); suit = null; }
  new GLTFLoader().load(url + '?t=' + Date.now(), (g) => {
    suit = g.scene; scene.add(suit);
    armorMeshes = [];
    suit.traverse(o => {
      if(o.isMesh){
        o.material = o.material.clone();
        const nm = (o.name||'').toLowerCase();
        if(nm.includes('armor') || nm.includes('abp')){
          o.userData.baseEmissive = o.material.emissiveIntensity || 0;
          armorMeshes.push(o);
        }
      }
    });
    document.getElementById('v3d_status').textContent =
      '読込完了 · 装甲メッシュ ' + armorMeshes.length + ' — 蒸着リプレイを押せます';
    buildPartNav();
    deposit();
  }, undefined, (e) => {
    document.getElementById('v3d_status').textContent = '読込エラー';
  });
}

function deposit(){
  if(!suit || !armorMeshes.length) return;
  armorMeshes.forEach(m => { m.material.transparent = true; m.material.opacity = 0; m.visible = false; });
  // 蒸着粒子: converging sparks around the body
  if(particles) scene.remove(particles);
  const N = 900, pos = new Float32Array(N*3);
  for(let i=0;i<N;i++){
    const a = Math.random()*Math.PI*2, r = 0.5+Math.random()*0.9, y = Math.random()*1.8;
    pos[i*3]=Math.cos(a)*r; pos[i*3+1]=y; pos[i*3+2]=Math.sin(a)*r;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  particles = new THREE.Points(geo, new THREE.PointsMaterial({
    color: 0x5fc7e8, size: 0.02, transparent: true, opacity: 1 }));
  scene.add(particles);
  depositT = 0;
  document.getElementById('v3d_status').textContent = 'DEPOSITION: START — 蒸着進行中…';
}

// ---- part inspection: 全身 <-> 単パーツの行き来 --------------------------
const PART_JP = {helmet:'兜', chest:'胸', back:'背', waist:'腰',
  left_shoulder:'左肩', right_shoulder:'右肩',
  left_upperarm:'左上腕', right_upperarm:'右上腕',
  left_forearm:'左前腕', right_forearm:'右前腕',
  left_hand:'左手', right_hand:'右手',
  left_thigh:'左腿', right_thigh:'右腿',
  left_shin:'左脛', right_shin:'右脛',
  left_boot:'左ブーツ', right_boot:'右ブーツ'};
let camHome = null, isolated = null;
function partKey(obj){
  // GLTFLoader: multi-primitive parts become a Group named armor_X_abp with
  // child meshes named after the mesh DATA — so walk up the parent chain
  for(let n = obj; n && n !== suit; n = n.parent){
    const m = /^armor_(.+?)_abp/.exec(n.name || '');
    if(m) return m[1];
  }
  return null;
}
function buildPartNav(){
  const nav = document.getElementById('part_nav');
  if(!nav || !suit) return;
  const keys = [];
  suit.traverse(o => { const k = o.isMesh ? partKey(o) : null;
    if(k && !keys.includes(k)) keys.push(k); });
  nav.innerHTML = '';
  if(!keys.length){ nav.style.display = 'none'; return; }
  const mk = (key, label) => {
    const b = document.createElement('button');
    b.textContent = label;
    b.dataset.part = key === null ? '' : key;
    b.style.cssText = 'font-size:12px;padding:4px 10px';
    b.onclick = () => isolate(key);
    nav.appendChild(b);
  };
  mk(null, '全身');
  const order = Object.keys(PART_JP);
  keys.sort((a,b) => order.indexOf(a) - order.indexOf(b));
  keys.forEach(k => mk(k, PART_JP[k] || k));
  nav.style.display = 'flex';
  markNav(null);
}
function markNav(key){
  const nav = document.getElementById('part_nav');
  [...nav.children].forEach(b => {
    b.style.outline = (b.dataset.part === (key || '')) ? '1px solid var(--cyan-dim)' : '';
  });
}
function isolate(key){
  if(!suit) return;
  isolated = key;
  const box = new THREE.Box3();
  let found = false;
  suit.updateMatrixWorld(true);
  suit.traverse(o => {
    const k = o.isMesh ? partKey(o) : null;
    if(!k) return;                         // 素体はそのまま見せる
    o.visible = (key === null) || (k === key);
    if(o.visible && key !== null){ box.expandByObject(o); found = true; }
  });
  markNav(key);
  if(key === null){
    if(camHome){ camera.position.copy(camHome.pos); controls.target.copy(camHome.tgt); }
    document.getElementById('v3d_status').textContent = '全身表示';
    return;
  }
  if(found){
    if(!camHome) camHome = {pos: camera.position.clone(), tgt: controls.target.clone()};
    const c = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3()).length();
    controls.target.copy(c);
    const dir = new THREE.Vector3(0.55, 0.3, 1).normalize();
    camera.position.copy(c.clone().add(dir.multiplyScalar(Math.max(0.3, size * 1.9))));
    document.getElementById('v3d_status').textContent = 'パーツ検分: ' + (PART_JP[key] || key);
  }
}
// ---- ヘンシン・モーション: henshin.vrma を装着モデルに再生 -------------
// vrma はこのスケルトン(J_Bip_*)から書き出しているのでトラック名がそのまま合う
let mixer = null;
const clock = new THREE.Clock();
function henshin(){
  if(!suit) return;
  new GLTFLoader().load('/r/henshin.vrma', (g) => {
    if(!g.animations || !g.animations.length){
      document.getElementById('v3d_status').textContent = 'モーションが見つかりません';
      return;
    }
    mixer = new THREE.AnimationMixer(suit);
    const action = mixer.clipAction(g.animations[0]);
    action.setLoop(THREE.LoopOnce, 1);
    action.clampWhenFinished = true;
    action.reset().play();
    deposit();  // 蒸着とモーションを同時に — VR装着シーケンスのローカル版
    document.getElementById('v3d_status').textContent = 'HENSHIN — 蒸着+モーション再生中…';
  }, undefined, () => {
    document.getElementById('v3d_status').textContent = 'henshin.vrma の読込に失敗';
  });
}
window.V3D = { show, deposit, henshin, getSuit: () => suit, isolate };
</script>
<script type="module">
import * as THREE from 'three';
import { FilesetResolver, FaceLandmarker, PoseLandmarker }
  from 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14';

// tracking v3 — 変身後はマスク。表情より体。
//  * 腕は Two-Bone IK(v4): 肩-肘-手首の位置から解く。腕長は剛体に保ち、
//    肘はポールベクトルとしてだけ効くので深度ノイズ・遮蔽に強い
//  * 平滑化は One Euro Filter(v4): 静止時は安定、速い動きに遅延しない
//  * 頭は体ランドマーク(鼻+両耳)から推定。478点の顔メッシュは任意
let running = false, video = null, face = null, pose = null, bones = null;
let faceLoading = false, files = null;
let euro = null;
const cv = () => document.getElementById('trk_canvas');
const st = (m, c) => { const e = document.getElementById('trk_status'); e.textContent = m; e.className = 'status '+(c||''); };
const isMirror = () => document.getElementById('trk_mirror').checked;
const useTorso = () => document.getElementById('trk_torso').checked;
const useFace = () => document.getElementById('trk_face').checked;

function grabBones(){
  const suit = window.V3D.getSuit && window.V3D.getSuit();
  if(!suit) return null;
  const map = {};
  suit.traverse(o => { if(o.isBone) map[o.name] = o; });
  const g = n => map[n] || null;
  const b = {
    head: g('J_Bip_C_Head'),
    chest: g('J_Bip_C_UpperChest') || g('J_Bip_C_Chest'),
    hips: g('J_Bip_C_Hips'),
    lSh: g('J_Bip_L_Shoulder'), rSh: g('J_Bip_R_Shoulder'),
    lUp: g('J_Bip_L_UpperArm'), lLo: g('J_Bip_L_LowerArm'), lHand: g('J_Bip_L_Hand'),
    rUp: g('J_Bip_R_UpperArm'), rLo: g('J_Bip_R_LowerArm'), rHand: g('J_Bip_R_Hand'),
    lMid: g('J_Bip_L_Middle1'), rMid: g('J_Bip_R_Middle1')  // 手のレスト方向の実測用
  };
  // restart-safe: put every driven bone back to its bind pose first
  for(const k in b){
    const bn = b[k];
    if(!bn) continue;
    if(!bn.userData.bindQ) bn.userData.bindQ = bn.quaternion.clone();
    else bn.quaternion.copy(bn.userData.bindQ);
    if(bn.userData.bindRotZ === undefined) bn.userData.bindRotZ = bn.rotation.z;
  }
  suit.updateMatrixWorld(true);
  // bind world orientation + MEASURED rest directions (works for A and T pose)
  for(const k in b){
    const bn = b[k];
    if(bn) bn.userData.bindWorldQ = bn.getWorldQuaternion(new THREE.Quaternion());
  }
  const wp = bn => bn.getWorldPosition(new THREE.Vector3());
  const seg = (a, c) => (a && c) ? wp(c).sub(wp(a)).normalize() : null;
  const len = (a, c) => (a && c) ? wp(c).distanceTo(wp(a)) : 0;
  b.rest = {
    lUp: seg(b.lUp, b.lLo), lLo: seg(b.lLo, b.lHand), lHand: seg(b.lHand, b.lMid),
    rUp: seg(b.rUp, b.rLo), rLo: seg(b.rLo, b.rHand), rHand: seg(b.rHand, b.rMid)
  };
  // IK は実ボーン長で解く(カメラ座標→モデル座標のスケール合わせに使う)
  b.len = {
    lUp: len(b.lUp, b.lLo), lLo: len(b.lLo, b.lHand),
    rUp: len(b.rUp, b.rLo), rLo: len(b.rLo, b.rHand)
  };
  return b;
}

async function setup(){
  st('MediaPipe 初期化中…', 'run');
  files = await FilesetResolver.forVisionTasks(
    'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm');
  pose = await PoseLandmarker.createFromOptions(files, {
    baseOptions: { modelAssetPath:
      'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task',
      delegate: 'GPU' },
    runningMode: 'VIDEO', numPoses: 1 });
}

async function ensureFace(){
  if(face || faceLoading || !files) return;
  faceLoading = true;
  try{
    face = await FaceLandmarker.createFromOptions(files, {
      baseOptions: { modelAssetPath:
        'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
        delegate: 'GPU' },
      runningMode: 'VIDEO', numFaces: 1, outputFacialTransformationMatrixes: true });
  }catch(e){ console.warn('face model load failed', e); }
  faceLoading = false;
}

const POSE_LINKS = [[11,13],[13,15],[12,14],[14,16],[11,12],[23,24],[11,23],[12,24],
                    [23,25],[25,27],[24,26],[26,28],[0,7],[0,8]];

function draw(faceRes, poseRes){
  const c = cv(), ctx = c.getContext('2d');
  const mir = isMirror();
  ctx.fillStyle = '#04080d'; ctx.fillRect(0,0,c.width,c.height);
  const X = x => (mir ? (1-x) : x) * c.width;
  const f = useFace() && faceRes && faceRes.faceLandmarks && faceRes.faceLandmarks[0];
  if(f){
    ctx.fillStyle = '#5fc7e8';
    for(const p of f){ ctx.fillRect(X(p.x), p.y*c.height, 1.4, 1.4); }
  }
  const b = poseRes && poseRes.landmarks && poseRes.landmarks[0];
  if(b){
    ctx.strokeStyle = 'rgba(230,240,250,0.8)'; ctx.lineWidth = 1.5;
    for(const pair of POSE_LINKS){
      const i = pair[0], j = pair[1];
      if(b[i] && b[j] && (b[i].visibility ?? 1) > 0.4 && (b[j].visibility ?? 1) > 0.4){
        ctx.beginPath();
        ctx.moveTo(X(b[i].x), b[i].y*c.height);
        ctx.lineTo(X(b[j].x), b[j].y*c.height);
        ctx.stroke();
      }
    }
    ctx.fillStyle = '#ffa23f';
    for(const p of b){ if((p.visibility ?? 1) > 0.4){
      ctx.beginPath(); ctx.arc(X(p.x), p.y*c.height, 3, 0, 6.283); ctx.fill(); } }
  }
}

// One Euro Filter over 33 world landmarks (v4) — EMA は速い動きで遅延した。
// 速度適応カットオフ: 静止時は強く平滑、突き/構えの速い動きは即追従
class OneEuro{
  constructor(minCutoff, beta){ this.mc = minCutoff; this.b = beta; this.dc = 1.0;
    this.x = null; this.dx = 0; this.t = null; }
  static a(cut, dt){ const r = 2 * Math.PI * cut * dt; return r / (r + 1); }
  f(x, t){
    if(this.t === null){ this.t = t; this.x = x; return x; }
    const dt = Math.min(0.1, Math.max(1e-3, t - this.t)); this.t = t;
    const dx = (x - this.x) / dt;
    this.dx += OneEuro.a(this.dc, dt) * (dx - this.dx);
    const cut = this.mc + this.b * Math.abs(this.dx);
    this.x += OneEuro.a(cut, dt) * (x - this.x);
    return this.x;
  }
}
function smoothWorld(w, tSec){
  if(!w) return null;
  if(!euro) euro = w.map(() => ({ x: new OneEuro(1.1, 0.6), y: new OneEuro(1.1, 0.6),
                                  z: new OneEuro(0.6, 0.35) })); // z(深度)が最もノイジー
  return w.map((p, i) => ({ x: euro[i].x.f(p.x, tSec), y: euro[i].y.f(p.y, tSec),
                            z: euro[i].z.f(p.z, tSec) }));
}

// camera space -> model space (mirror flips X)
function mp2three(p){
  const mir = isMirror();
  return new THREE.Vector3(mir ? -p.x : p.x, -p.y, -p.z);
}

const _pq = new THREE.Quaternion();
// drive a bone toward an ABSOLUTE world orientation, respecting the parent chain
function worldToLocal(bone, qWorldTarget, s){
  bone.parent.getWorldQuaternion(_pq);
  bone.quaternion.slerp(_pq.invert().multiply(qWorldTarget), s);
}
// rotate the bone so its measured bind-rest segment direction matches world dir d
function driveDir(bone, restDir, d, s){
  if(!bone || !restDir || !d || d.lengthSq() < 1e-8) return;
  const delta = new THREE.Quaternion().setFromUnitVectors(restDir, d.clone().normalize());
  worldToLocal(bone, delta.multiply(bone.userData.bindWorldQ), s);
}

// Two-Bone IK (v4): 肩-肘-手首の位置から解く。方向直結(v3)は肘の深度ノイズが
// 上腕ロールに直撃していた。IK は腕長を剛体に保ち、肘はポールベクトルとして
// だけ効く — 遮蔽や深度暴れで腕が折れ曲がらない
function solveArm(up, lo, hand, rest, lenUp, lenLo, mpSh, mpEl, mpWr, mpPk, mpIx, s){
  if(!up || !lo || !rest.up || !rest.lo) return;
  if(!(lenUp > 1e-4) || !(lenLo > 1e-4) || !mpSh || !mpEl || !mpWr) return;
  const S = up.getWorldPosition(new THREE.Vector3());   // 今フレームの胴回転込み
  const shM = mp2three(mpSh), elM = mp2three(mpEl), wrM = mp2three(mpWr);
  const mpLen = shM.distanceTo(elM) + elM.distanceTo(wrM);
  if(mpLen < 1e-4) return;
  const k = (lenUp + lenLo) / mpLen;                    // カメラ座標→モデル腕長
  const T = S.clone().add(wrM.clone().sub(shM).multiplyScalar(k));  // 手首目標
  const P = S.clone().add(elM.clone().sub(shM).multiplyScalar(k));  // 肘ヒント
  const d = THREE.MathUtils.clamp(S.distanceTo(T), Math.abs(lenUp - lenLo) + 1e-3,
                                  lenUp + lenLo - 1e-3);
  const n = T.clone().sub(S).normalize();
  // ポール: 肘ヒントの、肩→手首軸に直交な成分。潰れたら下方向へ逃がす
  let pole = P.clone().sub(S);
  pole.sub(n.clone().multiplyScalar(pole.dot(n)));
  if(pole.lengthSq() < 1e-6){
    pole = new THREE.Vector3(0, -1, 0);
    pole.sub(n.clone().multiplyScalar(pole.dot(n)));
    if(pole.lengthSq() < 1e-6) pole.set(0, 0, -1);
  }
  pole.normalize();
  const cosA = THREE.MathUtils.clamp(
    (lenUp * lenUp + d * d - lenLo * lenLo) / (2 * lenUp * d), -1, 1);
  const sinA = Math.sqrt(1 - cosA * cosA);
  const E = S.clone().add(n.clone().multiplyScalar(lenUp * cosA))
                     .add(pole.clone().multiplyScalar(lenUp * sinA));
  driveDir(up, rest.up, E.clone().sub(S), s);
  driveDir(lo, rest.lo, T.clone().sub(E), s);   // getWorldQuaternion が親を自動更新
  // 手首姿勢: pose の小指+人差指の中点方向で近似(HandLandmarker 導入までの v4)
  if(hand && rest.hand && mpPk && mpIx){
    const hd = mp2three(mpPk).add(mp2three(mpIx)).multiplyScalar(0.5).sub(mp2three(mpWr));
    driveDir(hand, rest.hand, hd, 0.4);
  }
}

function drive(faceRes, poseRes){
  if(!bones) bones = grabBones();
  if(!bones) return;
  const mir = isMirror();
  const suit = window.V3D.getSuit && window.V3D.getSuit();

  const wRaw = poseRes && poseRes.worldLandmarks && poseRes.worldLandmarks[0];
  const w = smoothWorld(wRaw, performance.now() / 1000);
  // mirror: the subject's RIGHT drives the model's LEFT (like a mirror)
  const L = mir ? {sh:12, el:14, wr:16, hip:24, ear:8, pk:18, ix:20}
                : {sh:11, el:13, wr:15, hip:23, ear:7, pk:17, ix:19};
  const R = mir ? {sh:11, el:13, wr:15, hip:23, ear:7, pk:17, ix:19}
                : {sh:12, el:14, wr:16, hip:24, ear:8, pk:18, ix:20};

  // ---- head: from face matrix when顔詳細ON, else from nose+ears (体優先) ----
  const mats = useFace() && faceRes && faceRes.facialTransformationMatrixes;
  if(bones.head && mats && mats[0]){
    const m = new THREE.Matrix4().fromArray(mats[0].data);
    const q = new THREE.Quaternion().setFromRotationMatrix(m);
    if(mir){ q.set(-q.x, -q.y, q.z, q.w); } else { q.set(-q.x, q.y, q.z, q.w); }
    q.normalize();
    worldToLocal(bones.head, q.multiply(bones.head.userData.bindWorldQ), 0.35);
  } else if(bones.head && w){
    const earL = mp2three(w[L.ear]), earR = mp2three(w[R.ear]), nose = mp2three(w[0]);
    const E = earL.clone().sub(earR);
    const yaw = Math.atan2(E.z, E.x);
    const roll = Math.atan2(E.y, Math.hypot(E.x, E.z));
    const mid = earL.clone().add(earR).multiplyScalar(0.5);
    const fwd = nose.clone().sub(mid);
    const pitchRaw = Math.atan2(fwd.y, Math.hypot(fwd.x, fwd.z)) + 0.35; // nose sits below the ear line
    const pitch = THREE.MathUtils.clamp(pitchRaw, -0.55, 0.55);
    const qh = new THREE.Quaternion().setFromEuler(
      new THREE.Euler(-pitch * 0.9, -yaw * 0.9, -roll * 0.9, 'YXZ'));
    worldToLocal(bones.head, qh.multiply(bones.head.userData.bindWorldQ), 0.35);
  }

  if(!w) return;

  // ---- torso: yaw / roll / pitch from shoulder & hip lines ----
  if(useTorso() && bones.chest){
    const shL = mp2three(w[L.sh]), shR = mp2three(w[R.sh]);
    const hipL = mp2three(w[L.hip]), hipR = mp2three(w[R.hip]);
    const S = shL.clone().sub(shR);
    const yaw   = Math.atan2(S.z, S.x);
    const roll  = Math.atan2(S.y, Math.hypot(S.x, S.z));
    const shMid = shL.clone().add(shR).multiplyScalar(0.5);
    const hipMid = hipL.clone().add(hipR).multiplyScalar(0.5);
    const spineDir = shMid.clone().sub(hipMid).normalize();
    const pitch = Math.atan2(-spineDir.z, spineDir.y);
    const qT = new THREE.Quaternion().setFromEuler(new THREE.Euler(pitch*0.8, -yaw*0.7, -roll*0.8, 'YXZ'));
    worldToLocal(bones.chest, qT.multiply(bones.chest.userData.bindWorldQ), 0.25);
    if(bones.hips){
      const qH = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, -yaw*0.3, 0));
      worldToLocal(bones.hips, qH.multiply(bones.hips.userData.bindWorldQ), 0.2);
    }
    const torsoLen = Math.max(0.05, shMid.distanceTo(hipMid));
    const shrugL = (shL.y - shMid.y) / torsoLen;
    const shrugR = (shR.y - shMid.y) / torsoLen;
    if(bones.lSh) bones.lSh.rotation.z = bones.lSh.userData.bindRotZ
      + THREE.MathUtils.clamp(-shrugL*1.6, -0.35, 0.35);
    if(bones.rSh) bones.rSh.rotation.z = bones.rSh.userData.bindRotZ
      + THREE.MathUtils.clamp(shrugR*1.6, -0.35, 0.35);
  }

  // arms LAST, with fresh world matrices so the parent-chain math sees the
  // torso/shoulder rotations from THIS frame (stale parents shoved arms
  // into the head whenever the torso turned)
  if(suit) suit.updateMatrixWorld(true);
  // 可視性ゲート: フレーム外の腕は最後の姿勢で保持(v3は画面外でも暴れた)
  const vis = i => wRaw && wRaw[i] && (wRaw[i].visibility ?? 1) > 0.35;
  if(vis(L.sh) && vis(L.el) && vis(L.wr)){
    solveArm(bones.lUp, bones.lLo, bones.lHand,
             {up: bones.rest.lUp, lo: bones.rest.lLo, hand: bones.rest.lHand},
             bones.len.lUp, bones.len.lLo,
             w[L.sh], w[L.el], w[L.wr], w[L.pk], w[L.ix], 0.45);
  }
  if(vis(R.sh) && vis(R.el) && vis(R.wr)){
    solveArm(bones.rUp, bones.rLo, bones.rHand,
             {up: bones.rest.rUp, lo: bones.rest.rLo, hand: bones.rest.rHand},
             bones.len.rUp, bones.len.rLo,
             w[R.sh], w[R.el], w[R.wr], w[R.pk], w[R.ix], 0.45);
  }
}

async function loop(){
  if(!running) return;
  if(useFace() && !face) ensureFace();
  const ts = performance.now();
  let fr = null, pr = null;
  if(face && useFace()){ try { fr = face.detectForVideo(video, ts); } catch(e){} }
  try { pr = pose.detectForVideo(video, ts); } catch(e){}
  draw(fr, pr);
  drive(fr, pr);
  requestAnimationFrame(loop);
}

async function toggle(){
  if(running){
    running = false;
    if(video && video.srcObject){ video.srcObject.getTracks().forEach(t=>t.stop()); }
    st('停止しました'); document.getElementById('b_track').textContent = 'トラッキング開始';
    return;
  }
  try{
    if(!pose) await setup();
    if(!video){ video = document.createElement('video');
      video.style.display='none'; video.muted=true; video.playsInline=true;
      document.body.appendChild(video); }
    const stream = await navigator.mediaDevices.getUserMedia({video:{width:640,height:480}, audio:false});
    video.srcObject = stream; await video.play();
    running = true; bones = null; euro = null;
    document.getElementById('b_track').textContent = 'トラッキング停止';
    st('追跡中 v4 — Two-Bone IK + One Euro（顔詳細は任意・映像は非表示）', 'ok');
    loop();
  }catch(e){ st('カメラ/モデル初期化エラー: '+(e.message||e), 'err'); }
}

window.TRK = { toggle, setModelReady(){ bones = null; euro = null; } };
</script>
</body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8020)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    RENDER_ROOT.mkdir(parents=True, exist_ok=True)
    # 蒸着モーションをビューアから再生できるように配信ルートへ複製
    vrma_src = RENDER_ROOT.parent / "henshin.vrma"
    if vrma_src.is_file():
        import shutil as _shutil
        _shutil.copy2(vrma_src, RENDER_ROOT / "henshin.vrma")
    try:
        find_blender()
    except FileNotFoundError as exc:
        print(f"WARNING: {exc} — Layer 1 (decode) still works; builds will error.")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(json.dumps({"ok": True, "url": f"http://localhost:{args.port}/",
                      "render_root": str(RENDER_ROOT)}, ensure_ascii=False))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
