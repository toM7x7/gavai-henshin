// 音声認識プロキシ — Sakura AI Engine Whisper(OpenAI互換)。
// Web Speech API が無い環境(Questブラウザ等)の変身音声認証がここを通る。
// トークンはサーバ専用env: SAKURA_AI_ENGINE_TOKEN(ブラウザには出さない)。
const TOKEN = process.env.SAKURA_AI_ENGINE_TOKEN || process.env.SAKURA_AI_ENGINE_API_KEY || '';
const BASE = (process.env.SAKURA_AI_ENGINE_BASE_URL || 'https://api.ai.sakura.ad.jp/v1').replace(/\/+$/, '');
const MODEL = process.env.SAKURA_WHISPER_MODEL || 'whisper-large-v3-turbo';
const MAX_BYTES = 2 * 1024 * 1024;  // 2.5〜3秒のopusは数十KB — 2MBあれば十分

export async function GET() {
  return Response.json({ ok: true, enabled: !!TOKEN });
}

export async function POST(req) {
  if (!TOKEN) {
    return Response.json({ ok: false, error: 'STT未設定(SAKURA_AI_ENGINE_TOKEN)' }, { status: 503 });
  }
  const buf = await req.arrayBuffer();
  if (!buf.byteLength || buf.byteLength > MAX_BYTES) {
    return Response.json({ ok: false, error: 'bad audio size' }, { status: 400 });
  }
  const mime = req.headers.get('content-type') || 'audio/webm';
  const ext = mime.includes('ogg') ? 'ogg' : mime.includes('mp4') ? 'mp4' : 'webm';
  const form = new FormData();
  form.append('model', MODEL);
  form.append('file', new Blob([buf], { type: mime }), `voice.${ext}`);
  const r = await fetch(`${BASE}/audio/transcriptions`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${TOKEN}` },
    body: form,
  });
  if (!r.ok) {
    return Response.json({ ok: false, error: `whisper ${r.status}` }, { status: 502 });
  }
  const j = await r.json().catch(() => ({}));
  return Response.json({ ok: true, text: String(j.text || '') });
}
