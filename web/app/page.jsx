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
      alignItems: 'center', justifyContent: 'center', gap: 34, padding: 24,
    }}>
      <header className="rise" style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 12, letterSpacing: '0.6em', color: '#5fc7e8' }}>蒸 着 執 行 録</div>
        <h1 style={{
          fontSize: 40, margin: '10px 0 0', letterSpacing: '0.14em',
          textShadow: '0 0 24px rgba(95,199,232,0.35)',
        }}>GAVAI HENSHIN</h1>
        <p style={{ color: '#8fa7b8', marginTop: 12, fontSize: 14, lineHeight: 2 }}>
          銀河の法は、言葉を鎧に変える。<br />
          思いを唱え、鍛造し、呼出符とともに蒸着せよ。
        </p>
      </header>

      <div className="rise" style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: 18, width: 'min(760px, 94vw)', animationDelay: '0.12s',
      }}>
        {/* 選択1: 鍛造 */}
        <a className="choice" href="/forge">
          <span className="kicker">FORGE</span>
          <h2>言葉から鍛造する</h2>
          <p>
            思い・意匠を言葉にすると、設計局AIが設計図として公示し、
            鍛造炉が装甲を成形。適合審査を経て、君だけの呼出符が発行される。
          </p>
          <span style={{ color: '#9fdcff', fontSize: 13, letterSpacing: '0.2em' }}>鍛造炉へ →</span>
        </a>

        {/* 選択2: 召喚 */}
        <div className="choice" style={{ cursor: 'default' }}>
          <span className="kicker">SUMMON</span>
          <h2>呼出符で召喚する</h2>
          <p>発行済みの呼出符を唱えると、保管庫から鎧が転送され蒸着する。</p>
          <form onSubmit={go} style={{ display: 'flex', gap: 8 }}>
            <input
              className="input-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="GAVAI-XXXXX"
              aria-label="呼出符"
            />
            <button type="submit" className="btn-main" style={{ whiteSpace: 'nowrap' }}>召喚</button>
          </form>
        </div>
      </div>

      <footer className="rise" style={{ color: '#5a7284', fontSize: 11, letterSpacing: '0.2em', animationDelay: '0.24s' }}>
        SEAL: READY — COSMIC FORGE NETWORK
      </footer>
    </main>
  );
}
