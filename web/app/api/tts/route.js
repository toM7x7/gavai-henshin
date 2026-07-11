// 管制アナウンス — プロバイダ切替式TTSプロキシ。
//   TTS_PROVIDER=aivis (本命・Aivis Cloud) / sakura / gemini
// 定型句ホワイトリスト制: 任意文言の読み上げ装置として乱用されない。
// 鍵はすべてサーバ専用env(NEXT_PUBLIC禁止)。
// Aivisのクレジット方針(2026-07-11): 自動追加しない。残高切れ(402/429)は
// 「今日は喋らない日」— 利用者には一切通知せず無音で続行し、
// サーバログ(AIVIS_CREDIT_OUT)にだけ残して管理者が後で確認する
import { rateLimit, clientIp } from '../../../lib/ratelimit';

const AIVIS_KEY = process.env.AIVIS_API_KEY || '';
const SAKURA_TOKEN = process.env.SAKURA_AI_ENGINE_TOKEN || process.env.SAKURA_AI_ENGINE_API_KEY || '';
const SAKURA_BASE = (process.env.SAKURA_AI_ENGINE_BASE_URL || 'https://api.ai.sakura.ad.jp/v1').replace(/\/+$/, '');
const GEMINI_KEY = process.env.GEMINI_API_KEY || '';
const PROVIDER = process.env.TTS_PROVIDER
  || (AIVIS_KEY ? 'aivis' : SAKURA_TOKEN ? 'sakura' : GEMINI_KEY ? 'gemini' : '');

const ALLOWED = new Set([
  '蒸着、完了。',
  '鍛造、完了。適合審査、通過。呼出符を発行する。',
  '蒸着解除。',
  '音声認証、成立。',
]);

// Gemini TTS は 24kHz 16bit mono PCM を返す — WAVヘッダを被せて返却
const wavWrap = (pcm, rate = 24000) => {
  const h = Buffer.alloc(44);
  h.write('RIFF', 0); h.writeUInt32LE(36 + pcm.length, 4); h.write('WAVE', 8);
  h.write('fmt ', 12); h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20);
  h.writeUInt16LE(1, 22); h.writeUInt32LE(rate, 24); h.writeUInt32LE(rate * 2, 28);
  h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34);
  h.write('data', 36); h.writeUInt32LE(pcm.length, 40);
  return Buffer.concat([h, pcm]);
};

async function aivisTts(text) {
  // https://api.aivis-project.com/v1/docs — POST /v1/tts/synthesize
  const model = process.env.AIVIS_MODEL_UUID
    || 'a59cb814-0083-4369-8542-f51a29e72af7';  // 公式既定モデル(Anneli)
  const r = await fetch('https://api.aivis-project.com/v1/tts/synthesize', {
    method: 'POST',
    headers: { Authorization: `Bearer ${AIVIS_KEY}`, 'content-type': 'application/json' },
    body: JSON.stringify({ model_uuid: model, text, output_format: 'mp3' }),
  });
  if (r.status === 402 || r.status === 429) {
    console.log(`AIVIS_CREDIT_OUT: HTTP ${r.status}`);  // 管理者向けの痕跡のみ
    return { silent: true };
  }
  if (!r.ok) {
    console.log(`AIVIS_TTS_FAILED: HTTP ${r.status}`);
    return null;
  }
  return { buf: Buffer.from(await r.arrayBuffer()), type: 'audio/mpeg' };
}

async function sakuraTts(text) {
  const model = process.env.SAKURA_TTS_MODEL || 'zundamon';
  const voice = process.env.SAKURA_TTS_VOICE || 'normal';
  const format = process.env.SAKURA_TTS_FORMAT || 'wav';
  const r = await fetch(`${SAKURA_BASE}/audio/speech`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${SAKURA_TOKEN}`,
      'Content-Type': 'application/json',
      Accept: `audio/${format}`,
    },
    body: JSON.stringify({ model, input: text, voice, response_format: format }),
  });
  if (!r.ok) return null;
  return { buf: Buffer.from(await r.arrayBuffer()), type: `audio/${format}` };
}

async function geminiTts(text) {
  const model = process.env.GEMINI_TTS_MODEL || 'gemini-2.5-flash-preview-tts';
  const voice = process.env.GEMINI_TTS_VOICE || 'Charon';  // 低め・管制向き
  const r = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-goog-api-key': GEMINI_KEY },
      body: JSON.stringify({
        contents: [{ parts: [{ text }] }],
        generationConfig: {
          responseModalities: ['AUDIO'],
          speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: voice } } },
        },
      }),
    });
  if (!r.ok) return null;
  const j = await r.json().catch(() => null);
  const b64 = j?.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
  if (!b64) return null;
  return { buf: wavWrap(Buffer.from(b64, 'base64')), type: 'audio/wav' };
}

export async function GET(req) {
  if (!PROVIDER) return Response.json({ ok: false, error: 'TTS未設定' }, { status: 503 });
  if (!rateLimit(`tts:${clientIp(req)}`, 12, 60 * 1000)) {
    return Response.json({ ok: false, error: 'rate limited' }, { status: 429 });
  }
  const text = (new URL(req.url).searchParams.get('text') || '').slice(0, 80);
  if (!ALLOWED.has(text)) return Response.json({ ok: false, error: 'phrase not allowed' }, { status: 400 });
  const out = PROVIDER === 'aivis' ? await aivisTts(text)
    : PROVIDER === 'gemini' ? await geminiTts(text)
    : await sakuraTts(text);
  // クレジット切れ: 503を返すとクライアント(announce)はこのセッション中
  // 静かに黙る — 利用者への通知はしない
  if (out && out.silent) return Response.json({ ok: false }, { status: 503 });
  if (!out) return Response.json({ ok: false, error: 'tts failed' }, { status: 502 });
  return new Response(out.buf, {
    headers: {
      'content-type': out.type,
      'cache-control': 'public, max-age=3600',  // 声の切替が翌日まで残らない程度に
    },
  });
}
