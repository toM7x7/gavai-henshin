// 鍛造工場(Cloud Run)へのサーバサイドプロキシ。
// FORGE_TOKEN はここ(サーバ)だけが知る — ブラウザには渡さない。
// このプロキシは誰でも叩ける入口なので、ここでのレート制限が
// 「工場の重いビルドを他人に回させない」ための第一防衛線になる
import { rateLimit, clientIp } from '../../../lib/ratelimit';

const FORGE = (process.env.FORGE_URL || '').replace(/\/+$/, '');
const TOKEN = process.env.FORGE_TOKEN || '';

const notConfigured = () => Response.json(
  { ok: false, error: '鍛造工場が未接続です(FORGE_URL未設定)' }, { status: 503 });

export async function POST(req) {
  if (!FORGE) return notConfigured();
  if (!rateLimit(`forge:${clientIp(req)}`, 3, 10 * 60 * 1000)) {
    return Response.json(
      { ok: false, error: '鍛造炉が過熱している — 少し待ってから再点火を' }, { status: 429 });
  }
  const body = await req.json().catch(() => ({}));
  const r = await fetch(`${FORGE}/forge`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-forge-token': TOKEN },
    body: JSON.stringify({ text: String(body.text || '').slice(0, 400) }),
  });
  return new Response(await r.text(), {
    status: r.status, headers: { 'content-type': 'application/json' },
  });
}

export async function GET(req) {
  if (!FORGE) return notConfigured();
  const id = new URL(req.url).searchParams.get('id') || '';
  const r = await fetch(`${FORGE}/job?id=${encodeURIComponent(id)}`, { cache: 'no-store' });
  return new Response(await r.text(), {
    status: r.status, headers: { 'content-type': 'application/json' },
  });
}
