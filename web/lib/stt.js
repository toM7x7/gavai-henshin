// 変身音声認証の共有ヘルパ。
// 一次: ブラウザ内蔵 Web Speech(Chrome系 — Google認識、低遅延・無料)
// 二次: MediaRecorder で音声を録り /api/stt(Sakura Whisper)で文字起こし
//       — Questブラウザ等 Web Speech の無い環境の道

// 合言葉は「蒸着!」がメイン(2026-07-11方針)。音声認識は じょうちゃく を
// 定着/常着 等に聞き間違えるので、その揺れも拾う。「変身」も言い間違い救済で許容
export const TRIGGER_RE = /蒸着|じょうちゃく|ジョウチャク|定着|常着|ていちゃく|上着|変身|へんしん|ヘンシン/;

// VR用の緩い照合(2026-07-11 T6): トリガーを引いて唱える方式では
// 「それっぽければ通す」。〜着/〜しん系・じょう/しょう系の断片まで許容。
// ※常時聞き取りの鏡では使わない(誤発火する)
export const TRIGGER_LOOSE_RE = /着|ちゃく|チャク|chaku|じょう|ジョウ|しょう|ショウ|ちょう|チョウ|変身|へん|ヘン|しん|シン|hen|jyo|jo/i;

// 管制アナウンス(Sakura TTS)。/api/tts が未設定なら静かに何もしない
let _ttsOk = null;
export const announce = async (text) => {
  try {
    if (_ttsOk === false) return;
    const r = await fetch(`/api/tts?text=${encodeURIComponent(text)}`);
    if (!r.ok) { if (r.status === 503) _ttsOk = false; return; }
    _ttsOk = true;
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = new Audio(url);
    a.onended = () => URL.revokeObjectURL(url);
    a.play().catch(() => {});
  } catch { /* 無音で続行 */ }
};

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
