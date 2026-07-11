'use client';
// 全ページ共通のクリック音 — ボタン/メニュータイル/カードに反応。
// /se/click.mp3 を置くと鳴る(無ければ無音のまま)
import { useEffect } from 'react';
import { sfx } from '../lib/audio';

export default function UiSound() {
  useEffect(() => {
    const h = (e) => {
      const t = e.target.closest && e.target.closest('button, .menu-tile, .choice, .btn-main, .btn-ghost, #VRButton');
      if (t) sfx('click', 0.5);
    };
    document.addEventListener('pointerdown', h);
    return () => document.removeEventListener('pointerdown', h);
  }, []);
  return null;
}
