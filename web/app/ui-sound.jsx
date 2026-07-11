'use client';
// 全ページ共通: クリック音 + 右下のSEミュートトグル(localStorage永続)。
import { useEffect, useState } from 'react';
import { sfx, isMuted, setMuted } from '../lib/audio';

export default function UiSound() {
  const [muted, setM] = useState(false);
  useEffect(() => { setM(isMuted()); }, []);
  useEffect(() => {
    const h = (e) => {
      const t = e.target.closest && e.target.closest('button, .menu-tile, .choice, .btn-main, .btn-ghost, #VRButton');
      if (t) sfx('click', 0.5);
    };
    document.addEventListener('pointerdown', h);
    return () => document.removeEventListener('pointerdown', h);
  }, []);
  const toggle = () => { const next = !muted; setMuted(next); setM(next); };
  return (
    <button
      onClick={toggle}
      aria-label={muted ? 'SEをオンにする' : 'SEをオフにする'}
      title={muted ? 'SE: OFF' : 'SE: ON'}
      style={{
        position: 'fixed', right: 14, bottom: 14, zIndex: 60,
        width: 40, height: 40, borderRadius: '50%',
        border: '1px solid #24425a', cursor: 'pointer',
        background: 'rgba(7,14,22,0.85)', color: muted ? '#5a7284' : '#9fdcff',
        fontSize: 17, lineHeight: 1,
      }}
    >{muted ? '🔇' : '🔊'}</button>
  );
}
