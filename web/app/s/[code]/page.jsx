'use client';
// /s/<code> — 呼出符ビューア: オービット + IBL + 蒸着エフェクト。
// 検証コンソール(tools/armor_lab_server.py の V3D)の Web 移植版 M2。
import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { fetchManifest, fileUrl } from '../../../lib/suit';

export default function SuitViewer() {
  const { code } = useParams();
  const mountRef = useRef(null);
  const apiRef = useRef({});
  const [manifest, setManifest] = useState(null);
  const [status, setStatus] = useState('呼出符を照合中…');
  const [depositing, setDepositing] = useState(false);

  useEffect(() => {
    if (!mountRef.current || !code) return;
    let disposed = false;

    const mount = mountRef.current;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x04080d);
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

    const camera = new THREE.PerspectiveCamera(
      40, mount.clientWidth / mount.clientHeight, 0.01, 50);
    camera.position.set(0.9, 1.35, 2.6);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0.95, 0);
    controls.enableDamping = true;

    const key = new THREE.DirectionalLight(0xffffff, 1.6);
    key.position.set(2, 3, 2);
    scene.add(key);
    scene.add(new THREE.DirectionalLight(0x88bbee, 0.7).translateX(-2).translateY(1.5).translateZ(-1));

    const grid = new THREE.GridHelper(4, 24, 0x1a3448, 0x0d1c28);
    scene.add(grid);

    let suit = null;
    let particles = null;
    let depositT = -1;

    // 蒸着: 粒子収束 + 下から上へのフェード(V3D deposit の移植・簡易版)
    const deposit = () => {
      if (!suit || depositT >= 0) return;
      depositT = 0;
      setDepositing(true);
      try { new Audio('/se/deposit.mp3').play().catch(() => {}); } catch {}
      const geo = new THREE.BufferGeometry();
      const N = 2200;
      const pos = new Float32Array(N * 3);
      for (let i = 0; i < N; i++) {
        const r = 1.5 + Math.random() * 2.5, a = Math.random() * 6.283;
        pos[i * 3] = Math.cos(a) * r;
        pos[i * 3 + 1] = Math.random() * 2.2;
        pos[i * 3 + 2] = Math.sin(a) * r;
      }
      geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      particles = new THREE.Points(geo, new THREE.PointsMaterial({
        color: 0x9fdcff, size: 0.02, transparent: true, opacity: 0.95,
        blending: THREE.AdditiveBlending, depthWrite: false,
      }));
      particles.userData.start = pos.slice();
      scene.add(particles);
      // 部位の正規化高さは開始時に一度だけ測る(毎フレームの
      // Box3.setFromObject は 34万tris 全走査でレンダラが凍る)
      const box = new THREE.Box3().setFromObject(suit);
      const span = Math.max(1e-3, box.max.y - box.min.y);
      const wp = new THREE.Vector3();
      suit.traverse((o) => {
        if (o.isMesh) {
          o.material = o.material.clone();
          o.material.transparent = true;
          o.material.opacity = 0;
          o.userData.h = (o.getWorldPosition(wp).y - box.min.y) / span;
        }
      });
      suit.visible = true;
    };
    apiRef.current.deposit = deposit;

    const clock = new THREE.Clock();
    const animate = () => {
      if (disposed) return;
      requestAnimationFrame(animate);
      const dt = clock.getDelta();
      if (depositT >= 0) {
        depositT += dt;
        const k = Math.min(1, depositT / 2.4);
        if (particles) {
          const p = particles.geometry.attributes.position;
          const s = particles.userData.start;
          for (let i = 0; i < p.count; i++) {
            p.array[i * 3] = s[i * 3] * (1 - k * 0.985);
            p.array[i * 3 + 2] = s[i * 3 + 2] * (1 - k * 0.985);
          }
          p.needsUpdate = true;
          particles.material.opacity = 0.95 * (1 - k);
        }
        if (suit) {
          suit.traverse((o) => {
            if (o.isMesh) {
              o.material.opacity = Math.min(1, Math.max(0, (k * 1.4 - o.userData.h * 0.5)));
            }
          });
        }
        if (k >= 1) {
          if (particles) { scene.remove(particles); particles = null; }
          suit && suit.traverse((o) => { if (o.isMesh) { o.material.opacity = 1; o.material.transparent = false; } });
          depositT = -1;
          setDepositing(false);
        }
      }
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    (async () => {
      try {
        const m = await fetchManifest(code);
        if (disposed) return;
        setManifest(m);
        setStatus('鎧データを転送中…');
        const file = m.files.assembly || m.files.lod1;
        const gltf = await new GLTFLoader().loadAsync(fileUrl(code, file));
        if (disposed) return;
        suit = gltf.scene;
        suit.visible = false;
        scene.add(suit);
        setStatus('');
        deposit();
      } catch (e) {
        setStatus(String(e.message || e));
      }
    })();

    const onResize = () => {
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    };
    window.addEventListener('resize', onResize);
    return () => {
      disposed = true;
      window.removeEventListener('resize', onResize);
      controls.dispose();
      renderer.dispose();
      pmrem.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, [code]);

  return (
    <main style={{ position: 'fixed', inset: 0 }}>
      <div ref={mountRef} style={{ position: 'absolute', inset: 0 }} />
      <div style={{
        position: 'absolute', top: 14, left: 18, pointerEvents: 'none',
        textShadow: '0 1px 6px #000',
      }}>
        <div style={{ fontSize: 11, letterSpacing: '0.4em', color: '#5fc7e8' }}>蒸着執行録</div>
        <div style={{ fontSize: 20, letterSpacing: '0.12em' }}>{code}</div>
        {manifest && (
          <div style={{ fontSize: 12, color: '#8fa7b8', marginTop: 4 }}>
            {manifest.blueprint_id}
            {manifest.fit_summary &&
              ` — 適合 ${manifest.fit_summary.parts_pass}/${manifest.fit_summary.parts_total}`}
          </div>
        )}
      </div>
      {status && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
          justifyContent: 'center', color: '#9fdcff', fontSize: 15,
          letterSpacing: '0.2em', pointerEvents: 'none', textShadow: '0 1px 6px #000',
        }}>{status}</div>
      )}
      <div style={{ position: 'absolute', bottom: 18, left: 18, display: 'flex', gap: 10 }}>
        <button
          onClick={() => apiRef.current.deposit && apiRef.current.deposit()}
          disabled={depositing}
          style={{
            background: depositing ? '#123246' : 'linear-gradient(135deg,#1d5f8a,#2c8fbf)',
            color: '#fff', border: 'none', borderRadius: 8, padding: '10px 18px',
            fontSize: 14, cursor: depositing ? 'default' : 'pointer', letterSpacing: '0.25em',
          }}>蒸着</button>
        {manifest && manifest.files.vrm && (
          <a href={`/ar/${code}`} style={{
            background: '#0a121c', color: '#9fdcff', border: '1px solid #24425a',
            borderRadius: 8, padding: '10px 18px', fontSize: 14, textDecoration: 'none',
            letterSpacing: '0.1em',
          }}>VR/ARで装着</a>
        )}
        {manifest && manifest.files.vrm && (
          <a href={`/mirror/${code}`} style={{
            background: '#0a121c', color: '#9fdcff', border: '1px solid #24425a',
            borderRadius: 8, padding: '10px 18px', fontSize: 14, textDecoration: 'none',
            letterSpacing: '0.1em',
          }}>鏡で体連携</a>
        )}
        {manifest && manifest.files.vrm && (
          <a href={fileUrl(code, manifest.files.vrm)} download={`${code}.vrm`} style={{
            background: '#0a121c', color: '#9fdcff', border: '1px solid #24425a',
            borderRadius: 8, padding: '10px 18px', fontSize: 14, textDecoration: 'none',
            letterSpacing: '0.1em',
          }}>VRMを持ち出す</a>
        )}
      </div>
    </main>
  );
}
