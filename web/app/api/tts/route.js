// 管制アナウンス — Sakura AI Engine TTS(/audio/speech)プロキシ。
// 定型句のホワイトリスト制: 任意文言の読み上げ装置として乱用されない
// (許可句を増やす時はこの一覧に足す)。トークンはSTTと同じサーバ専用env。
import { rateLimit, clientIp } from '../../../lib/ratelimit';

const TOKEN = process.env.SAKURA_AI_ENGINE_TOKEN || process.env.SAKURA_AI_ENGINE_API_KEY || '';
const BASE = (process.env.SAKURA_AI_ENGINE_BASE_URL || 'https://api.ai.sakura.ad.jp/v1').replace(/\/+$/, '');
const MODEL = process.env.SAKURA_TTS_MODEL || 'zundamon';
const VOICE = process.env.SAKURA_TTS_VOICE || 'normal';
const FORMAT = process.env.SAKURA_TTS_FORMAT || 'wav';

const ALLOWED = new Set([
  '蒸着、完了。',
  '鍛造、完了。適合審査、通過。呼出符を発行する。',
  '蒸着解除。',
  '音声認証、成立。',
]);

export async function GET(req) {
  if (!TOKEN) return Response.json({ ok: false, error: 'TTS未設定' }, { status: 503 });
  if (!rateLimit(`tts:${clientIp(req)}`, 12, 60 * 1000)) {
    return Response.json({ ok: false, error: 'rate limited' }, { status: 429 });
  }
  const text = (new URL(req.url).searchParams.get('text') || '').slice(0, 80);
  if (!ALLOWED.has(text)) return Response.json({ ok: false, error: 'phrase not allowed' }, { status: 400 });
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
