'use client';
// /forge — 言葉から鎧を鍛造する(Cloud Run工場をプロキシ経由で叩く)。
// 2〜4分のビルドは「鍛造炉」の演出として見せる。
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';

const PHASES = {
  queued: '鍛造炉の順番待ち…',
  forging: '鍛造中 — 装甲を成形し、適合審査を通しています',
  uploading: '保管庫へ格納しています',
};

export default function Forge() {
  const [text, setText] = useState('');
  const [job, setJob] = useState(null);      // {job_id}
  const [state, setState] = useState(null);  // ジョブの最新状態
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
          setTimeout(() => router.push(`/s/${s.code}`), 1600);
          return;
        }
        if (s.status === 'error') return;
      } catch {}
      setTimeout(poll, 3000);
    };
    poll();
    return () => { stop = true; clearInterval(timerRef.current); };
  }, [job, router]);

  const running = job && (!state || ['queued', 'forging', 'uploading'].includes(state.status));
  const mm = String(Math.floor(elapsed / 60)).padStart(1, '0');
  const ss = String(elapsed % 60).padStart(2, '0');

  return (
    <main style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 22, padding: 24,
    }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 13, letterSpacing: '0.5em', color: '#5fc7e8' }}>蒸着執行録</div>
        <h1 style={{ fontSize: 30, margin: '8px 0 0', letterSpacing: '0.12em' }}>鍛造炉 / FORGE</h1>
        <p style={{ color: '#8fa7b8', marginTop: 10 }}>
          思い・意匠を言葉にせよ — 設計図が紡がれ、装甲が鍛造される
        </p>
      </div>

      <form onSubmit={start} style={{ display: 'flex', flexDirection: 'column', gap: 12, width: 'min(560px, 92vw)' }}>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="例: 蒼雷を纏う疾風の剣士。仲間を守る誓いの盾。"
          rows={3}
          disabled={!!running}
          style={{
            background: '#0a121c', color: '#dce8f2', border: '1px solid #24425a',
            borderRadius: 8, padding: '12px 14px', fontSize: 15, resize: 'vertical',
            outline: 'none', lineHeight: 1.7,
          }}
        />
        <div style={{ fontSize: 12, color: '#8fa7b8' }}>
          言葉は設計局AI(Gemini)が解釈し、設計図として公示されます
        </div>
        <button type="submit" disabled={!!running || !text.trim()} style={{
          background: running ? '#123246' : 'linear-gradient(135deg,#1d5f8a,#2c8fbf)',
          color: '#fff', border: 'none', borderRadius: 8, padding: '12px 22px',
          fontSize: 16, cursor: running ? 'default' : 'pointer', letterSpacing: '0.25em',
        }}>{running ? '鍛造中…' : '鍛造開始'}</button>
      </form>

      {job && (
        <div style={{
          width: 'min(560px, 92vw)', border: '1px solid #24425a', borderRadius: 8,
          padding: '16px 18px', background: '#070e16', fontSize: 14, lineHeight: 2,
        }}>
          {state?.status === 'done' ? (
            <>
              <div style={{ color: '#7ee2a8' }}>
                ■ 鍛造完了 — 適合審査 {state.fit}
                {state.route && state.route.startsWith('llm') && ' — 設計局AI解釈'}
              </div>
              {state.route && state.route.startsWith('rule_fallback') && (
                <div style={{ color: '#d9b45f', fontSize: 12 }}>
                  ※設計局AIが応答せず、規範解釈で鍛造されました ({state.route})
                </div>
              )}
              <div>呼出符 <b style={{ fontSize: 20, letterSpacing: '0.15em', color: '#9fdcff' }}>{state.code}</b></div>
              <div style={{ color: '#8fa7b8' }}>蒸着室へ移動します…</div>
            </>
          ) : state?.status === 'error' ? (
            <div style={{ color: '#ff9a8a' }}>■ 鍛造失敗: {state.error}</div>
          ) : (
            <>
              <div style={{ color: '#9fdcff' }}>
                <span className="pulse">■</span> {PHASES[state?.status] || '鍛造炉を点火しています…'}
              </div>
              <div style={{ color: '#5a7284' }}>
                経過 {mm}:{ss} — 鍛造には2〜4分かかります(炉が冷えている時はさらに+1分)
              </div>
              {state?.blueprint_id && (
                <div style={{ color: '#5a7284', fontFamily: 'monospace' }}>{state.blueprint_id}</div>
              )}
            </>
          )}
        </div>
      )}
      <a href="/" style={{ color: '#5a7284', fontSize: 12, textDecoration: 'none' }}>← 呼出符で召喚する</a>
      <style jsx>{`
        .pulse { animation: pulse 1.2s ease-in-out infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.25; } }
      `}</style>
    </main>
  );
}
