'use client';
// /ar/<code> — Quest WebXR 装着体験(M4)。パススルーARに鎧が現れ、
// コントローラのトリガー(select)で蒸着 — 粒子収束+ヘンシンモーション+SE。
// immersive-ar 非対応機では immersive-vr へフォールバックする。
import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { ARButton } from 'three/examples/jsm/webxr/ARButton.js';
import { VRButton } from 'three/examples/jsm/webxr/VRButton.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import { VRMAnimationLoaderPlugin, createVRMAnimationClip } from '@pixiv/three-vrm-animation';
import { fetchManifest, fileUrl, setArmorVisible } from '../../../lib/suit';
import { TRIGGER_RE, announce, pickAudioMime, recordChunk, transcribe, sttEnabled } from '../../../lib/stt';

export default function ArExperience() {
  const { code } = useParams();
  const mountRef = useRef(null);
  const [status, setStatus] = useState('転送装置を起動中…');

  useEffect(() => {
    if (!mountRef.current || !code) return;
    let disposed = false;
    const mount = mountRef.current;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.xr.enabled = true;
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    const camera = new THREE.PerspectiveCamera(50, mount.clientWidth / mount.clientHeight, 0.01, 60);
    camera.position.set(0, 1.5, 0);
    const key = new THREE.DirectionalLight(0xffffff, 1.2);
    key.position.set(1, 3, 2);
    scene.add(key);
    scene.add(new THREE.AmbientLight(0x88aacc, 0.4));

    let vrm = null, vrmaData = null, mixer = null, motionPlaying = false, particles = null;
    let vrGrid = null;

    const henshin = () => {
      if (!vrm || motionPlaying) return;
      motionPlaying = true;
      try { new Audio('/se/henshin.mp3').play().catch(() => {}); } catch {}
      setArmorVisible(vrm.scene, true);   // 素体に鎧が装着される
      const N = 1800;
      const pos = new Float32Array(N * 3);
      const base = vrm.scene.position;
      for (let i = 0; i < N; i++) {
        const r = 0.9 + Math.random() * 1.6, a = Math.random() * 6.283;
        pos[i * 3] = base.x + Math.cos(a) * r;
        pos[i * 3 + 1] = Math.random() * 2.0;
        pos[i * 3 + 2] = base.z + Math.sin(a) * r;
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      particles = new THREE.Points(geo, new THREE.PointsMaterial({
        color: 0x9fdcff, size: 0.02, transparent: true, opacity: 0.95,
        blending: THREE.AdditiveBlending, depthWrite: false,
      }));
      particles.userData = { start: pos.slice(), t: 0, cx: base.x, cz: base.z };
      scene.add(particles);
      if (vrmaData) {
        const clip = createVRMAnimationClip(vrmaData, vrm);
        mixer = new THREE.AnimationMixer(vrm.scene);
        const action = mixer.clipAction(clip);
        action.setLoop(THREE.LoopOnce);
        action.clampWhenFinished = true;
        mixer.addEventListener('finished', () => {
          motionPlaying = false;
          announce('蒸着、完了。');
        });
        action.play();
      } else {
        setTimeout(() => { motionPlaying = false; announce('蒸着、完了。'); }, 2400);
      }
    };

    // コントローラのトリガー(画面タップも select になる)。
    // Whisper設定済みなら「トリガーを引いて唱える」儀式(旧展示UX):
    // 3秒録音→Sakura Whisper→合言葉照合→蒸着。未設定ならトリガー=直接蒸着
    let voiceMode = false, micStream = null, listening = false;
    const onSelect = async () => {
      if (motionPlaying || listening) return;
      if (!voiceMode || !micStream) { henshin(); return; }
      listening = true;
      setStatus('唱えよ —「蒸着!」(3秒)');
      try {
        const blob = await recordChunk(micStream, 3000, pickAudioMime());
        setStatus('Sakura Whisperで音声解析中…');
        const text = await transcribe(blob);
        if (TRIGGER_RE.test(text)) {
          henshin();
          setStatus('音声認証 成立 — 蒸着');
        } else {
          setStatus(`「${text || '…'}」— 合言葉未検出。もう一度トリガー`);
        }
      } catch {
        setStatus('音声解析に失敗 — もう一度トリガー(無音でも蒸着したい時は2連続で引く)');
        voiceMode = false;  // 障害時は次のトリガーで直接蒸着に切替
      }
      listening = false;
    };
    const c0 = renderer.xr.getController(0);
    const c1 = renderer.xr.getController(1);
    c0.addEventListener('select', onSelect);
    c1.addEventListener('select', onSelect);
    scene.add(c0); scene.add(c1);

    const clock = new THREE.Clock();
    renderer.setAnimationLoop(() => {
      if (disposed) return;
      const dt = clock.getDelta();
      if (mixer) mixer.update(dt);
      if (particles) {
        const u = particles.userData;
        u.t += dt;
        const k = Math.min(1, u.t / 1.6);
        const p = particles.geometry.attributes.position;
        for (let i = 0; i < p.count; i++) {
          p.array[i * 3] = u.cx + (u.start[i * 3] - u.cx) * (1 - k * 0.985);
          p.array[i * 3 + 2] = u.cz + (u.start[i * 3 + 2] - u.cz) * (1 - k * 0.985);
        }
        p.needsUpdate = true;
        particles.material.opacity = 0.95 * (1 - k);
        if (k >= 1) { scene.remove(particles); particles = null; }
      }
      if (vrm) vrm.update(dt);
      renderer.render(scene, camera);
    });

    (async () => {
      try {
        const m = await fetchManifest(code);
        if (disposed) return;
        if (!m.files.vrm) { setStatus('このパッケージにはVRMがありません'); return; }
        setStatus('鎧データを転送中…');
        const loader = new GLTFLoader();
        loader.register((parser) => new VRMLoaderPlugin(parser));
        loader.register((parser) => new VRMAnimationLoaderPlugin(parser));
        const gltf = await loader.loadAsync(fileUrl(code, m.files.vrm));
        vrm = gltf.userData.vrm;
        VRMUtils.rotateVRM0(vrm);
        vrm.scene.position.set(0, 0, -1.6);   // 目の前1.6mに立つ
        scene.add(vrm.scene);
        setArmorVisible(vrm.scene, false);    // スタートは素体 — 儀式で装着する
        if (m.files.vrma) {
          try {
            const ag = await loader.loadAsync(fileUrl(code, m.files.vrma));
            vrmaData = (ag.userData.vrmAnimations || [])[0] || null;
          } catch { vrmaData = null; }
        }

        // 音声認証(Sakura Whisper)が使えるならXR入場前にマイク許可を取っておく
        // (セッション内での許可ダイアログは体験を折る)
        voiceMode = await sttEnabled();
        if (voiceMode && pickAudioMime()) {
          try {
            micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
          } catch { voiceMode = false; }
        } else { voiceMode = false; }
        const ritual = voiceMode ? 'トリガーを引いて「蒸着!」と唱えよ' : 'トリガーで蒸着';

        // AR(パススルー)優先、非対応なら VR、それも無ければ案内のみ
        const xr = navigator.xr;
        const arOK = xr && await xr.isSessionSupported('immersive-ar').catch(() => false);
        const vrOK = xr && await xr.isSessionSupported('immersive-vr').catch(() => false);
        if (arOK) {
          document.body.appendChild(ARButton.createButton(renderer, {
            requiredFeatures: ['local-floor'],
          }));
          setStatus(`READY — 「START AR」で転送。${ritual}`);
        } else if (vrOK) {
          // VRは無背景だと寂しいので床グリッドを敷く
          vrGrid = new THREE.GridHelper(6, 30, 0x1a3448, 0x0d1c28);
          scene.add(vrGrid);
          scene.background = new THREE.Color(0x04080d);
          document.body.appendChild(VRButton.createButton(renderer));
          setStatus(`READY — 「ENTER VR」で転送。${ritual}`);
        } else {
          setStatus('この端末はWebXR非対応です。Quest Browserで開いてください');
        }
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
      if (micStream) micStream.getTracks().forEach((t) => t.stop());
      window.removeEventListener('resize', onResize);
      renderer.setAnimationLoop(null);
      renderer.dispose(); pmrem.dispose();
      mount.removeChild(renderer.domElement);
      document.querySelectorAll('#ARButton, #VRButton').forEach((b) => b.remove());
    };
  }, [code]);

  return (
    <main style={{ position: 'fixed', inset: 0 }}>
      <div ref={mountRef} style={{ position: 'absolute', inset: 0 }} />
      <div style={{ position: 'absolute', top: 14, left: 18, textShadow: '0 1px 6px #000' }}>
        <div style={{ fontSize: 11, letterSpacing: '0.4em', color: '#5fc7e8' }}>蒸着執行録 / XR</div>
        <div style={{ fontSize: 20, letterSpacing: '0.12em' }}>{code}</div>
        <div style={{ fontSize: 12, color: '#8fa7b8', marginTop: 6, maxWidth: 340 }}>{status}</div>
      </div>
      <a href={`/s/${code}`} style={{
        position: 'absolute', top: 16, right: 18, color: '#5a7284', fontSize: 12,
        textDecoration: 'none',
      }}>← ビューアへ</a>
    </main>
  );
}
