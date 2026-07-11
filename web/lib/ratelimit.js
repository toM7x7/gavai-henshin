// 簡易レート制限(インスタンス内メモリ・スライディングウィンドウ)。
// サーバレスはインスタンスごとにリセットされるため厳密ではないが、
// カジュアルな乱用(スクリプトでの連打)には十分効く。本丸の防衛は
// 鍛造工場側のキュー上限(forge_server)と短文上限(stt/tts)が担う。
const buckets = new Map();

export function rateLimit(key, limit, windowMs) {
  const now = Date.now();
  const hits = (buckets.get(key) || []).filter((t) => now - t < windowMs);
  if (hits.length >= limit) {
    buckets.set(key, hits);
    return false;
  }
  hits.push(now);
  buckets.set(key, hits);
  if (buckets.size > 5000) buckets.clear();  // 念のためのメモリ上限
  return true;
}

export function clientIp(req) {
  return (req.headers.get('x-forwarded-for') || '').split(',')[0].trim() || 'unknown';
}
