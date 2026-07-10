'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const [code, setCode] = useState('');
  const router = useRouter();
  const go = (e) => {
    e.preventDefault();
    const c = code.trim().toUpperCase();
    if (c) router.push(`/s/${c}`);
  };
  return (
    <main style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 24, padding: 24,
    }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 13, letterSpacing: '0.5em', color: '#5fc7e8' }}>蒸着執行録</div>
        <h1 style={{ fontSize: 34, margin: '8px 0 0', letterSpacing: '0.12em' }}>GAVAI HENSHIN</h1>
        <p style={{ color: '#8fa7b8', marginTop: 10 }}>呼出符を唱えよ — 言葉から鍛造された鎧が蒸着する</p>
      </div>
      <form onSubmit={go} style={{ display: 'flex', gap: 10 }}>
        <input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="GAVAI-0001"
          autoFocus
          style={{
            background: '#0a121c', color: '#dce8f2', border: '1px solid #24425a',
            borderRadius: 8, padding: '12px 16px', fontSize: 18, width: 220,
            letterSpacing: '0.15em', textTransform: 'uppercase', outline: 'none',
          }}
        />
        <button type="submit" style={{
          background: 'linear-gradient(135deg,#1d5f8a,#2c8fbf)', color: '#fff',
          border: 'none', borderRadius: 8, padding: '12px 22px', fontSize: 16,
          cursor: 'pointer', letterSpacing: '0.2em',
        }}>召喚</button>
      </form>
      <a href="/forge" style={{
        color: '#9fdcff', fontSize: 14, textDecoration: 'none',
        border: '1px solid #24425a', borderRadius: 8, padding: '10px 18px',
        letterSpacing: '0.15em',
      }}>言葉から鍛造する →</a>
      <div style={{ color: '#5a7284', fontSize: 12 }}>
        または ローカルForge + <code>package_suit_for_web.py</code> で登録
      </div>
    </main>
  );
}
