'use client';
// /vr — Quest向けのVR直行入口。
// Questブラウザでこのページを開き、呼出符の続き5文字を入れるだけで
// 蒸着チャンバー(/ar/<code>)へ飛ぶ。鍛造記録からのワンタップ入場も可。
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { galleryUrl } from '../../lib/suit';

export default function VrGate() {
  const [code, setCode] = useState('');
  const [gallery, setGallery] = useState([]);
  const router = useRouter();

  useEffect(() => {
    fetch(galleryUrl(), { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : []))
      .then((items) => Array.isArray(items) && setGallery(items.slice(0, 6)))
      .catch(() => {});
  }, []);

  const normalize = (v) => v.toUpperCase().replace(/^GAVAI-?/, '').replace(/[^A-Z0-9]/g, '').slice(0, 5);
  const go = (e) => {
    e.preventDefault();
    const c = normalize(code);
    if (c) router.push(`/ar/GAVAI-${c}`);
  };

  return (
    <main style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 26, padding: 24,
    }}>
      <header className="rise" style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 12, letterSpacing: '0.55em', color: '#5fc7e8' }}>蒸 着 執 行 録</div>
        <h1 style={{ fontSize: 30, margin: '10px 0 0', letterSpacing: '0.14em' }}>🥽 VR直行入口</h1>
        <p style={{ color: '#8fa7b8', marginTop: 10, fontSize: 14, lineHeight: 2 }}>
          呼出符の続き5文字を入れるだけで、蒸着チャンバーへ転送する。
        </p>
      </header>

      <form onSubmit={go} className="rise" style={{
        display: 'flex', gap: 10, alignItems: 'center', animationDelay: '0.1s',
      }}>
        <span style={{
          color: '#5fc7e8', fontSize: 22, letterSpacing: '0.14em', fontFamily: 'monospace',
        }}>GAVAI-</span>
        <input
          className="input-code"
          value={code}
          onChange={(e) => setCode(normalize(e.target.value))}
          placeholder="XXXXX"
          maxLength={5}
          autoFocus
          style={{ width: 190, fontSize: 24, letterSpacing: '0.35em', fontFamily: 'monospace', padding: '14px 16px' }}
          aria-label="呼出符(GAVAI-の続き5文字)"
        />
        <button type="submit" className="btn-main" style={{ fontSize: 17, padding: '15px 26px', whiteSpace: 'nowrap' }}>
          転送
        </button>
      </form>

      {gallery.length > 0 && (
        <section className="rise" style={{ width: 'min(560px, 94vw)', animationDelay: '0.18s' }}>
          <div style={{ fontSize: 11, letterSpacing: '0.4em', color: '#5fc7e8', marginBottom: 10 }}>
            鍛造記録からワンタップ入場
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {gallery.map((g) => (
              <a key={g.code} href={`/ar/${g.code}`} className="btn-ghost"
                style={{ fontSize: 15, letterSpacing: '0.12em', padding: '12px 18px' }}>
                {g.code}
              </a>
            ))}
          </div>
        </section>
      )}

      <div className="rise" style={{ color: '#5a7284', fontSize: 12, lineHeight: 2, textAlign: 'center', animationDelay: '0.25s' }}>
        PCからQuestへURLを送るには: このページのURL(<code>/vr</code>)を<br />
        Metaのスマホアプリ「ヘッドセットに送信」か、Questブラウザのアドレスバーに直接入力。
      </div>
      <a href="/" style={{ color: '#5a7284', fontSize: 12, textDecoration: 'none' }}>← 執行録の扉へ</a>
    </main>
  );
}
