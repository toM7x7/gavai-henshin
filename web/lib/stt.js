// 変身音声認証の共有ヘルパ。
// 一次: ブラウザ内蔵 Web Speech(Chrome系 — Google認識、低遅延・無料)
// 二次: MediaRecorder で音声を録り /api/stt(Sakura Whisper)で文字起こし
//       — Questブラウザ等 Web Speech の無い環境の道

export const TRIGGER_RE = /変身|へんしん|ヘンシン|蒸着|じょうちゃく/;

export const hasNativeSR = () =>
  typeof window !== 'undefined' &&
  !!(window.SpeechRecognition || window.webkitSpeechRecognition);

export const pickAudioMime = () => {
  if (typeof MediaRecorder === 'undefined') return '';
  const cands = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
  return cands.find((t) => MediaRecorder.isTypeSupported(t)) || '';
};

// stream から ms ミリ秒ぶん録音して Blob を返す
export const recordChunk = (stream, ms, mime) => new Promise((resolve, reject) => {
  let rec;
  try { rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined); }
  catch (e) { reject(e); return; }
  const parts = [];
  rec.ondataavailable = (e) => { if (e.data && e.data.size) parts.push(e.data); };
  rec.onstop = () => resolve(new Blob(parts, { type: mime || 'audio/webm' }));
  rec.onerror = (e) => reject(e.error || new Error('recorder error'));
  rec.start();
  setTimeout(() => { try { rec.stop(); } catch {} }, ms);
});

export const transcribe = async (blob) => {
  const r = await fetch('/api/stt', {
    method: 'POST',
    headers: { 'content-type': blob.type || 'audio/webm' },
    body: blob,
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || !j.ok) throw new Error(j.error || `stt ${r.status}`);
  return j.text || '';
};

export const sttEnabled = async () => {
  try {
    const r = await fetch('/api/stt', { cache: 'no-store' });
    const j = await r.json();
    return !!j.enabled;
  } catch { return false; }
};
