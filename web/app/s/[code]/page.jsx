'use client';
// /s/<code> — 蒸着室(呼出符ビューア)。
// スタートは素体。蒸着ボタンで 閃光+SE+粒子収束+鎧マテリアライズ+
// ヘンシンモーション(henshin.vrma)が一体で走る。解除で素体に戻る。
// VRMがあればVRM+VRMAで動かし、無い古いパッケージはassembly.glbに退避。
import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import { VRMAnimationLoaderPlugin, createVRMAnimationClip } from '@pixiv/three-vrm-animation';
import { fetchManifest, fileUrl, armorMeshes, setArmorVisible } from '../../../lib/suit';
import { announce } from '../../../lib/stt';

export default function SuitViewer() {
  const { code } = useParams();
  const mountRef = useRef(null);
  const apiRef = useRef({});
  const [manifest, setManifest] = useState(null);
  const [status, setStatus] = useState('呼出符を照合中…');
  const [busy, setBusy] = useState(false);
  const [worn, setWorn] = useState(false);
  const [flashKey, setFlashKey] = useState(0);

  useEffect(() => {
    if (!mountRef.current || !code) return;
    let disposed = false;

    const mount = mountRef.current;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
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
    scene.add(new THREE.GridHelper(4, 24, 0x1a3448, 0x0d1c28));

    let vrm = null, vrmaData = null, mixer = null;
    let suit = null;            // GLBフォールバック用
    let armor = [];
    let particles = null, fadeT = -1, motionPlaying = false;

    const burst = () => {
      const N = 2200;
      const pos = new Float32Array(N * 3);
      for (let i = 0; i < N; i++) {
        const r = 1.5 + Math.random() * 2.5, a = Math.random() * 6.283;
        pos[i * 3] = Math.cos(a) * r;
        pos[i * 3 + 1] = Math.random() * 2.2;
        pos[i * 3 + 2] = Math.sin(a) * r;
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      particles = new THREE.Points(geo, new THREE.PointsMaterial({
        color: 0x9fdcff, size: 0.02, transparent: true, opacity: 0.95,
        blending: THREE.AdditiveBlending, depthWrite: false,
      }));
      particles.userData = { start: pos.slice(), t: 0 };
      scene.add(particles);
    };

    // 蒸着 — 変身モーションと共に装着する(体験の主役ボタン)
    const deposit = () => {
      if ((!vrm && !suit) || motionPlaying || fadeT >= 0 || !armor.length) return;
      setBusy(true);
      setFlashKey((k) => k + 1);
      try { new Audio('/se/deposit.mp3').play().catch(() => {}); } catch {}
      burst();
      if (vrm) {
        setArmorVisible(vrm.scene, true);   // 閃光の中で鎧が現れる
        if (vrmaData) {
          motionPlaying = true;
          const clip = createVRMAnimationClip(vrmaData, vrm);
          mixer = new THREE.AnimationMixer(vrm.scene);
          const action = mixer.clipAction(clip);
          action.setLoop(THREE.LoopOnce);
          action.clampWhenFinished = true;
          mixer.addEventListener('finished', () => {
            mixer.stopAllAction();
            mixer = null;
            motionPlaying = false;
            setBusy(false);
            setWorn(true);
            setStatus('');
            announce('蒸着、完了。');
          });
          action.play();
          setStatus('蒸着 — ヘンシンモーション実行中');
        } else {
          setTimeout(() => {
            setBusy(false); setWorn(true); setStatus('');
            announce('蒸着、完了。');
          }, 2400);
        }
      } else {
        // GLBフォールバック: 下から上へのマテリアライズ
        fadeT = 0;
        const box = new THREE.Box3().setFromObject(suit);
        const span = Math.max(1e-3, box.max.y - box.min.y);
        const wp = new THREE.Vector3();
        for (const o of armor) {
          o.material = o.material.clone();
          o.material.transparent = true;
          o.material.opacity = 0;
          o.userData.h = (o.getWorldPosition(wp).y - box.min.y) / span;
          o.visible = true;
        }
      }
    };
    apiRef.current.deposit = deposit;

    // 解除 — 鎧を還して素体に戻す(何度でも蒸着できる)
    apiRef.current.release = () => {
      if (motionPlaying || fadeT >= 0) return;
      setFlashKey((k) => k + 1);
      const root = vrm ? vrm.scene : suit;
      if (root) for (const o of armor) o.visible = false;
      setWorn(false);
      setStatus('素体待機 — 蒸着せよ');
    };

    const clock = new THREE.Clock();
    const animate = () => {
      if (disposed) return;
      requestAnimationFrame(animate);
      const dt = clock.getDelta();
      if (mixer) mixer.update(dt);
      if (particles) {
        const u = particles.userData;
        u.t += dt;
        const k = Math.min(1, u.t / 2.0);
        const p = particles.geometry.attributes.position;
        for (let i = 0; i < p.count; i++) {
          p.array[i * 3] = u.start[i * 3] * (1 - k * 0.985);
          p.array[i * 3 + 2] = u.start[i * 3 + 2] * (1 - k * 0.985);
        }
        p.needsUpdate = true;
        particles.material.opacity = 0.95 * (1 - k);
        if (k >= 1) { scene.remove(particles); particles = null; }
      }
      if (fadeT >= 0) {
        fadeT += dt;
        const k = Math.min(1, fadeT / 2.4);
        for (const o of armor) {
          o.material.opacity = Math.min(1, Math.max(0, (k * 1.4 - o.userData.h * 0.5)));
        }
        if (k >= 1) {
          for (const o of armor) { o.material.opacity = 1; o.material.transparent = false; }
          fadeT = -1;
          setBusy(false);
          setWorn(true);
          setStatus('');
          announce('蒸着、完了。');
        }
      }
      if (vrm) vrm.update(dt);
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
        if (m.files.vrm) {
          const loader = new GLTFLoader();
          loader.register((parser) => new VRMLoaderPlugin(parser));
          loader.register((parser) => new VRMAnimationLoaderPlugin(parser));
          const gltf = await loader.loadAsync(fileUrl(code, m.files.vrm));
          if (disposed) return;
          vrm = gltf.userData.vrm;
          VRMUtils.rotateVRM0(vrm);
          scene.add(vrm.scene);
          armor = armorMeshes(vrm.scene);
          setArmorVisible(vrm.scene, false);
          if (m.files.vrma) {
            try {
              const ag = await loader.loadAsync(fileUrl(code, m.files.vrma));
              vrmaData = (ag.userData.vrmAnimations || [])[0] || null;
            } catch { vrmaData = null; }
          }
        } else {
          const file = m.files.assembly || m.files.lod1;
          const gltf = await new GLTFLoader().loadAsync(fileUrl(code, file));
          if (disposed) return;
          suit = gltf.scene;
          scene.add(suit);
          armor = armorMeshes(suit);
          for (const o of armor) o.visible = false;
        }
        setStatus('素体待機 — 蒸着せよ');
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
      {flashKey > 0 && <div key={flashKey} className="henshin-flash" />}

      <div style={{
        position: 'absolute', top: 14, left: 18, pointerEvents: 'none',
        textShadow: '0 1px 6px #000',
      }}>
        <div style={{ fontSize: 11, letterSpacing: '0.4em', color: '#5fc7e8' }}>蒸着執行録 / 蒸着室</div>
        <div style={{ fontSize: 20, letterSpacing: '0.12em' }}>{code}</div>
        {manifest && (
          <div style={{ fontSize: 12, color: '#8fa7b8', marginTop: 4 }}>
            {manifest.blueprint_id}
            {manifest.fit_summary &&
              ` — 適合 ${manifest.fit_summary.parts_pass}/${manifest.fit_summary.parts_total}`}
          </div>
        )}
      </div>

      <nav className="topnav">
        <a href="/">⌂ 扉へ</a>
        <a href="/forge">⚒ 鍛造炉</a>
      </nav>

      {status && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
          justifyContent: 'center', color: '#9fdcff', fontSize: 15,
          letterSpacing: '0.2em', pointerEvents: 'none', textShadow: '0 1px 6px #000',
        }}>{status}</div>
      )}

      <div className="menu">
        <button
          className={`menu-tile ${worn ? '' : 'primary'}`}
          onClick={() => (worn
            ? apiRef.current.release && apiRef.current.release()
            : apiRef.current.deposit && apiRef.current.deposit())}
          disabled={busy}
        >
          <span className="ic">{worn ? '↺' : '⚡'}</span>
          {busy ? '蒸着中…' : worn ? '解除' : '蒸着'}
          <span className="sub">{worn ? '素体に戻す' : '変身モーションと共に装着'}</span>
        </button>
        {manifest?.files?.vrm && (
          <a className="menu-tile" href={`/ar/${code}`}>
            <span className="ic">🥽</span>
            VRで蒸着
            <span className="sub">Quest — 現実空間で装着</span>
          </a>
        )}
        {manifest?.files?.vrm && (
          <a className="menu-tile" href={`/mirror/${code}`}>
            <span className="ic">📷</span>
            Webカメラで変身体験
            <span className="sub">体の動きと鎧がリンク</span>
          </a>
        )}
        {manifest?.files?.vrm && (
          <a className="menu-tile" href={fileUrl(code, manifest.files.vrm)} download={`${code}.vrm`}>
            <span className="ic">💾</span>
            VRMエクスポート
            <span className="sub">メタバースへ持ち出す</span>
          </a>
        )}
      </div>
    </main>
  );
}
