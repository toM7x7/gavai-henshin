'use client';
// /forge — 言葉から鎧を鍛造する。工場のジョブ進行(stage/timings)を
// 工程トラッカーで見せる: 待ち時間は「儀式の進行」であって空白ではない。
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';

const STEPS = [
  { n: 1, key: 'interpret', name: '解釈', sub: '設計局AIが言葉を読む' },
  { n: 2, key: 'build', name: '鍛造', sub: '装甲成形・適合審査' },
  { n: 3, key: 'upload', name: '格納', sub: '保管庫へ封緘' },
  { n: 4, key: 'issue', name: '公示', sub: '呼出符の発行' },
];

export default function Forge() {
  const [text, setText] = useState('');
  const [job, setJob] = useState(null);
  const [state, setState] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef(null);
  const router = useRouter();

  const start = async (e) => {
    e.preventDefault();
    const t = text.trim();
    if (!t || job) return;
    setState(null);
    const r = await fetch('/api/forge', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ text: t }),
    });
    const j = await r.json();
    if (!j.ok) { setState({ status: 'error', error: j.error || 'error' }); return; }
    setJob(j);
    setElapsed(0);
  };

  useEffect(() => {
    if (!job) return;
    let stop = false;
    timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);
    const poll = async () => {
      if (stop) return;
      try {
        const r = await fetch(`/api/forge?id=${job.job_id}`, { cache: 'no-store' });
        const s = await r.json();
        setState(s);
        if (s.status === 'done') {
          setTimeout(() => router.push(`/s/${s.code}`), 2200);
          return;
        }
        if (s.status === 'error') return;
      } catch {}
      setTimeout(poll, 2500);
    };
    poll();
    return () => { stop = true; clearInterval(timerRef.current); };
  }, [job, router]);

  const stage = state?.status === 'done' ? 5 : (state?.stage || (job ? 1 : 0));
  const running = job && (!state || !['done', 'error'].includes(state.status));
  const mm = Math.floor(elapsed / 60);
  const ss = String(elapsed % 60).padStart(2, '0');
  const timings = state?.timings || {};

  return (
    <main style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 24, padding: 24,
    }}>
      <header className="rise" style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 11, letterSpacing: '0.5em', color: '#5fc7e8' }}>蒸着執行録 / COSMIC FORGE</div>
        <h1 style={{ fontSize: 30, margin: '8px 0 0', letterSpacing: '0.14em' }}>鍛 造 炉</h1>
      </header>

      {!job && (
        <form onSubmit={start} className="rise" style={{
          display: 'flex', flexDirection: 'column', gap: 12, width: 'min(560px, 92vw)',
          animationDelay: '0.1s',
        }}>
          <p style={{ color: '#8fa7b8', fontSize: 13, lineHeight: 1.9, margin: 0 }}>
            思い・意匠を言葉にせよ。言葉は設計局AI(Gemini)が解釈し、設計図として公示される。
          </p>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="例: 蒼雷を纏う疾風の剣士。仲間を守る誓いの盾。"
            rows={3}
            style={{
              background: '#0a121c', color: '#dce8f2', border: '1px solid #24425a',
              borderRadius: 8, padding: '12px 14px', fontSize: 15, resize: 'vertical',
              outline: 'none', lineHeight: 1.7,
            }}
          />
          <button type="submit" className="btn-main" disabled={!text.trim()}>鍛造開始</button>
        </form>
      )}

      {job && (
        <section className="rise" style={{
          width: 'min(620px, 94vw)', border: '1px solid #24425a', borderRadius: 12,
          padding: '26px 22px', background: 'rgba(7,14,22,0.85)',
          display: 'flex', flexDirection: 'column', gap: 22,
        }}>
          {running && (
            <div className="forge-core">
              <div className="ring" /><div className="ring2" /><div className="heart" />
            </div>
          )}

          <div className="tracker">
            {STEPS.map((s) => (
              <div key={s.key}
                className={`step ${stage > s.n ? 'done' : ''} ${stage === s.n ? 'now' : ''}`}>
                <div className="dot">{stage > s.n ? '✓' : s.n}</div>
                <div className="name">{s.name}</div>
                <div className="sub">
                  {timings[s.key] ? `${timings[s.key]}s` : s.sub}
                </div>
              </div>
            ))}
          </div>

          {state?.status === 'done' ? (
            <div style={{ textAlign: 'center', lineHeight: 2.2 }}>
              <div style={{ color: '#7ee2a8', letterSpacing: '0.2em' }}>
                ■ 鍛造完了 — 適合審査 {state.fit}
                {state.route && state.route.startsWith('llm') && ' — 設計局AI解釈'}
              </div>
              <div style={{ fontSize: 26, letterSpacing: '0.2em', color: '#9fdcff' }}>{state.code}</div>
              <div style={{ color: '#8fa7b8', fontSize: 13 }}>この呼出符が君の鎧の名だ。蒸着室へ移動する…</div>
              {state.route && state.route.startsWith('rule_fallback') && (
                <div style={{ color: '#d9b45f', fontSize: 12 }}>
                  ※設計局AIが応答せず、規範解釈で鍛造されました
                </div>
              )}
            </div>
          ) : state?.status === 'error' ? (
            <div style={{ color: '#ff9a8a', textAlign: 'center', lineHeight: 1.9 }}>
              ■ 鍛造失敗: {state.error}
              <div><a className="btn-ghost" href="/forge" style={{ marginTop: 10 }}>炉に再点火する</a></div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', color: '#9fdcff', fontSize: 14, lineHeight: 2 }}>
              <span className="pulse">▮</span> {state?.phase || '鍛造炉を点火しています(炉が冷えていると+1分)…'}
              <div style={{ color: '#5a7284', fontSize: 12 }}>
                経過 {mm}:{ss} — 鍛造の儀は数分を要する。逸る心も装備のうち。
              </div>
              {state?.blueprint_id && (
                <div style={{ color: '#5a7284', fontSize: 11, fontFamily: 'monospace' }}>
                  設計図公示: {state.blueprint_id}
                </div>
              )}
            </div>
          )}
        </section>
      )}

      <a href="/" style={{ color: '#5a7284', fontSize: 12, textDecoration: 'none' }}>← 執行録の扉へ</a>
    </main>
  );
}
