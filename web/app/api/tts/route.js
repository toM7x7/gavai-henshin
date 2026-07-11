// 管制アナウンス — Sakura AI Engine TTS(/audio/speech)プロキシ。
// 「蒸着、完了。」等の短文専用。トークンはSTTと同じサーバ専用env。
const TOKEN = process.env.SAKURA_AI_ENGINE_TOKEN || process.env.SAKURA_AI_ENGINE_API_KEY || '';
const BASE = (process.env.SAKURA_AI_ENGINE_BASE_URL || 'https://api.ai.sakura.ad.jp/v1').replace(/\/+$/, '');
const MODEL = process.env.SAKURA_TTS_MODEL || 'zundamon';
const VOICE = process.env.SAKURA_TTS_VOICE || 'normal';
const FORMAT = process.env.SAKURA_TTS_FORMAT || 'wav';

export async function GET(req) {
  if (!TOKEN) return Response.json({ ok: false, error: 'TTS未設定' }, { status: 503 });
  const text = (new URL(req.url).searchParams.get('text') || '').slice(0, 80);
  if (!text) return Response.json({ ok: false, error: 'no text' }, { status: 400 });
  const r = await fetch(`${BASE}/audio/speech`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      'Content-Type': 'application/json',
      Accept: `audio/${FORMAT}`,
    },
    body: JSON.stringify({ model: MODEL, input: text, voice: VOICE, response_format: FORMAT }),
  });
  if (!r.ok) return Response.json({ ok: false, error: `tts ${r.status}` }, { status: 502 });
  return new Response(await r.arrayBuffer(), {
    headers: {
      'content-type': `audio/${FORMAT}`,
      'cache-control': 'public, max-age=86400',  // 定型句はブラウザに覚えさせる
    },
  });
}
