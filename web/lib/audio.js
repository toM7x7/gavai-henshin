// SE基盤 — /se/<name>.mp3 を置くだけで鳴る(無ければ無音)。
// 単発(sfx)とループ(loopStart/loopStop、フェード付き)を提供する。
// 音量の設計: クリック0.5 / 環境ループ0.3〜0.4 / 儀式の主役SE 1.0
const loops = {};

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
  try {
    const a = new Audio(`/se/${name}.mp3`);
    a.volume = vol;
    a.play().catch(() => {});
  } catch { /* SE未配置は無音 */ }
};

export const loopStart = (name, vol = 0.4, fadeSec = 1.2) => {
  if (loops[name]) return;
  try {
    const a = new Audio(`/se/${name}.mp3`);
    a.loop = true;
    a.volume = 0;
    loops[name] = a;
    a.play().then(() => fade(a, vol, fadeSec)).catch(() => { delete loops[name]; });
  } catch { delete loops[name]; }
};

export const loopStop = (name, fadeSec = 1.0) => {
  const a = loops[name];
  if (!a) return;
  delete loops[name];
  fade(a, 0, fadeSec, () => a.pause());
};
