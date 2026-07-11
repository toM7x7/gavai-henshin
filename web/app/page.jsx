'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { galleryUrl } from '../lib/suit';

export default function Home() {
  const [code, setCode] = useState('');
  const [gallery, setGallery] = useState([]);
  const router = useRouter();

  useEffect(() => {
    fetch(galleryUrl(), { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : []))
      .then((items) => Array.isArray(items) && setGallery(items.slice(0, 8)))
      .catch(() => {});
  }, []);
  // 入力はGAVAI-の続き5文字だけ。フル呼出符を貼り付けても自動で剥がす
  const normalize = (v) => v.toUpperCase().replace(/^GAVAI-?/, '').replace(/[^A-Z0-9]/g, '').slice(0, 5);
  const go = (e) => {
    e.preventDefault();
    const c = normalize(code);
    if (c) router.push(`/s/GAVAI-${c}`);
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
          <form onSubmit={go} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{
              color: '#5fc7e8', fontSize: 16, letterSpacing: '0.14em',
              fontFamily: 'monospace', flex: 'none',
            }}>GAVAI-</span>
            <input
              className="input-code"
              value={code}
              onChange={(e) => setCode(normalize(e.target.value))}
              placeholder="XXXXX"
              maxLength={5}
              aria-label="呼出符(GAVAI-の続き5文字)"
              style={{ letterSpacing: '0.3em', fontFamily: 'monospace' }}
            />
            <button type="submit" className="btn-main" style={{ whiteSpace: 'nowrap' }}>召喚</button>
          </form>
          <a href="/vr" style={{ color: '#5a7284', fontSize: 12, textDecoration: 'none' }}>
            🥽 Questから来た人はこちら(VR直行入口)→
          </a>
        </div>
      </div>

      {gallery.length > 0 && (
        <section className="rise" style={{ width: 'min(760px, 94vw)', animationDelay: '0.2s' }}>
          <div style={{ fontSize: 11, letterSpacing: '0.4em', color: '#5fc7e8', marginBottom: 10 }}>
            鍛造記録 / RECENT FORGE
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {gallery.map((g) => (
              <a key={g.code} href={`/s/${g.code}`} style={{
                display: 'flex', flexDirection: 'column', gap: 4,
                border: '1px solid #24425a', borderRadius: 8, padding: '10px 14px',
                textDecoration: 'none', background: 'rgba(7,14,22,0.8)',
              }}>
                <span style={{ display: 'flex', gap: 4 }}>
                  {['base_surface', 'accent', 'emissive'].map((k) => g.palette?.[k] && (
                    <i key={k} style={{
                      width: 10, height: 10, borderRadius: 2, background: g.palette[k],
                    }} />
                  ))}
                </span>
                <span style={{ color: '#9fdcff', fontSize: 14, letterSpacing: '0.12em' }}>{g.code}</span>
                {g.intent && <span style={{ color: '#5a7284', fontSize: 11 }}>{g.intent}</span>}
              </a>
            ))}
          </div>
        </section>
      )}

      <footer className="rise" style={{ color: '#5a7284', fontSize: 11, letterSpacing: '0.2em', animationDelay: '0.24s' }}>
        SEAL: READY — COSMIC FORGE NETWORK
      </footer>
    </main>
  );
}
