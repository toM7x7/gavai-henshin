// SE基盤 — /se/<name>.mp3 を置くだけで鳴る(無ければ無音)。
// 単発(sfx)とループ(loopStart/loopStop、フェード付き)を提供する。
// 全体ミュート: localStorage 'se-muted' に永続(SoundToggleが切替UI)。
// 長いループは duckAfter 秒後に自動で音量を落とす — 鍛造が数分続いても
// 同じ金属音が同じ大きさで鳴り続けない(2026-07-11 体験課題T1)
const loops = {};
let muted = false;
try { muted = typeof localStorage !== 'undefined' && localStorage.getItem('se-muted') === '1'; } catch {}

export const isMuted = () => muted;
export const setMuted = (m) => {
  muted = m;
  try { localStorage.setItem('se-muted', m ? '1' : '0'); } catch {}
  // 進行中のループにも即反映
  for (const name of Object.keys(loops)) {
    const a = loops[name];
    if (m) fade(a, 0, 0.3);
    else fade(a, a._targetVol || 0.3, 0.5);
  }
};

const fade = (a, target, sec, done) => {
  const from = a.volume;
  const t0 = performance.now();
  const step = (t) => {
    const k = Math.min(1, (t - t0) / (sec * 1000));
    a.volume = Math.max(0, Math.min(1, from + (target - from) * k));
    if (k < 1) requestAnimationFrame(step);
    else if (done) done();
  };
  requestAnimationFrame(step);
};

export const sfx = (name, vol = 1) => {
  if (muted) return;
  try {
    const a = new Audio(`/se/${name}.mp3`);
    a.volume = vol;
    a.play().catch(() => {});
  } catch { /* SE未配置は無音 */ }
};

export const loopStart = (name, vol = 0.4, fadeSec = 1.2, duckAfterSec = 20, duckVol = 0.1) => {
  if (loops[name]) return;
  try {
    const a = new Audio(`/se/${name}.mp3`);
    a.loop = true;
    a.volume = 0;
    a._targetVol = vol;
    loops[name] = a;
    a.play().then(() => {
      if (!muted) fade(a, vol, fadeSec);
      // 長丁場は環境音レベルまで自動で退く
      a._duckTimer = setTimeout(() => {
        a._targetVol = duckVol;
        if (!muted && loops[name] === a) fade(a, duckVol, 3.0);
      }, duckAfterSec * 1000);
    }).catch(() => { delete loops[name]; });
  } catch { delete loops[name]; }
};

export const loopStop = (name, fadeSec = 1.0) => {
  const a = loops[name];
  if (!a) return;
  delete loops[name];
  if (a._duckTimer) clearTimeout(a._duckTimer);
  fade(a, 0, fadeSec, () => a.pause());
};
