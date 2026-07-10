'use client';
// /mirror/<code> — Webカメラ体連携(鏡)。ラボの tracking v4 の移植:
//  * MediaPipe pose 33点(映像は描画しない — 点群のみ)
//  * 腕は Two-Bone IK(腕長剛体・肘はポールベクトル)、平滑化は One Euro
//  * 頭は鼻+両耳から推定。可視性ゲートでフレーム外の腕は保持
// モデルは suit-package の VRM を three-vrm 正規化リグで駆動する。
import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import { fetchManifest, fileUrl } from '../../../lib/suit';

// ---- One Euro Filter(速度適応平滑化) ----
class OneEuro {
  constructor(minCutoff, beta) {
    this.mc = minCutoff; this.b = beta; this.dc = 1.0;
    this.x = null; this.dx = 0; this.t = null;
  }
  static a(cut, dt) { const r = 2 * Math.PI * cut * dt; return r / (r + 1); }
  f(x, t) {
    if (this.t === null) { this.t = t; this.x = x; return x; }
    const dt = Math.min(0.1, Math.max(1e-3, t - this.t)); this.t = t;
    const dx = (x - this.x) / dt;
    this.dx += OneEuro.a(this.dc, dt) * (dx - this.dx);
    const cut = this.mc + this.b * Math.abs(this.dx);
    this.x += OneEuro.a(cut, dt) * (x - this.x);
    return this.x;
  }
}

export default function Mirror() {
  const { code } = useParams();
  const mountRef = useRef(null);
  const canvasRef = useRef(null);
  const apiRef = useRef({});
  const [status, setStatus] = useState('鏡を準備中…');
  const [running, setRunning] = useState(false);
  const [mirrorMode, setMirrorMode] = useState(true);

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
    const camera = new THREE.PerspectiveCamera(40, mount.clientWidth / mount.clientHeight, 0.01, 50);
    camera.position.set(0, 1.25, 2.6);
    camera.lookAt(0, 0.95, 0);
    scene.add(new THREE.GridHelper(4, 24, 0x1a3448, 0x0d1c28));
    const key = new THREE.DirectionalLight(0xffffff, 1.4);
    key.position.set(2, 3, 2);
    scene.add(key);

    let vrm = null, bones = null, euro = null;
    let pose = null, video = null, run = false;

    // VRM Humanoid 正規化リグからボーンを取得し、バインド情報を実測
    const grabBones = () => {
      if (!vrm) return null;
      const h = vrm.humanoid;
      const g = (n) => h.getNormalizedBoneNode(n);
      const b = {
        head: g('head'), chest: g('upperChest') || g('chest'), hips: g('hips'),
        lUp: g('leftUpperArm'), lLo: g('leftLowerArm'), lHand: g('leftHand'),
        rUp: g('rightUpperArm'), rLo: g('rightLowerArm'), rHand: g('rightHand'),
        lMid: g('leftMiddleProximal'), rMid: g('rightMiddleProximal'),
      };
      for (const k in b) {
        const bn = b[k];
        if (!bn) continue;
        if (!bn.userData.bindQ) bn.userData.bindQ = bn.quaternion.clone();
        else bn.quaternion.copy(bn.userData.bindQ);
      }
      vrm.scene.updateMatrixWorld(true);
      for (const k in b) {
        const bn = b[k];
        if (bn) bn.userData.bindWorldQ = bn.getWorldQuaternion(new THREE.Quaternion());
      }
      const wp = (bn) => bn.getWorldPosition(new THREE.Vector3());
      const seg = (a, c) => (a && c) ? wp(c).sub(wp(a)).normalize() : null;
      const len = (a, c) => (a && c) ? wp(c).distanceTo(wp(a)) : 0;
      b.rest = {
        lUp: seg(b.lUp, b.lLo), lLo: seg(b.lLo, b.lHand), lHand: seg(b.lHand, b.lMid),
        rUp: seg(b.rUp, b.rLo), rLo: seg(b.rLo, b.rHand), rHand: seg(b.rHand, b.rMid),
      };
      b.len = {
        lUp: len(b.lUp, b.lLo), lLo: len(b.lLo, b.lHand),
        rUp: len(b.rUp, b.rLo), rLo: len(b.rLo, b.rHand),
      };
      return b;
    };

    const smoothWorld = (w, t) => {
      if (!w) return null;
      if (!euro) euro = w.map(() => ({
        x: new OneEuro(1.1, 0.6), y: new OneEuro(1.1, 0.6), z: new OneEuro(0.6, 0.35),
      }));
      return w.map((p, i) => ({
        x: euro[i].x.f(p.x, t), y: euro[i].y.f(p.y, t), z: euro[i].z.f(p.z, t),
      }));
    };
    const mp2three = (p) => new THREE.Vector3(
      apiRef.current.mirror ? -p.x : p.x, -p.y, -p.z);

    const _pq = new THREE.Quaternion();
    const worldToLocal = (bone, qW, s) => {
      bone.parent.getWorldQuaternion(_pq);
      bone.quaternion.slerp(_pq.invert().multiply(qW), s);
    };
    const driveDir = (bone, restDir, d, s) => {
      if (!bone || !restDir || !d || d.lengthSq() < 1e-8) return;
      const delta = new THREE.Quaternion().setFromUnitVectors(restDir, d.clone().normalize());
      worldToLocal(bone, delta.multiply(bone.userData.bindWorldQ), s);
    };
    // Two-Bone IK(ラボv4と同一の解): 腕長剛体・肘はポールベクトル
    const solveArm = (up, lo, hand, rest, lenUp, lenLo, mpSh, mpEl, mpWr, mpPk, mpIx, s) => {
      if (!up || !lo || !rest.up || !rest.lo) return;
      if (!(lenUp > 1e-4) || !(lenLo > 1e-4) || !mpSh || !mpEl || !mpWr) return;
      const S = up.getWorldPosition(new THREE.Vector3());
      const shM = mp2three(mpSh), elM = mp2three(mpEl), wrM = mp2three(mpWr);
      const mpLen = shM.distanceTo(elM) + elM.distanceTo(wrM);
      if (mpLen < 1e-4) return;
      const k = (lenUp + lenLo) / mpLen;
      const T = S.clone().add(wrM.clone().sub(shM).multiplyScalar(k));
      const P = S.clone().add(elM.clone().sub(shM).multiplyScalar(k));
      const d = THREE.MathUtils.clamp(S.distanceTo(T), Math.abs(lenUp - lenLo) + 1e-3,
        lenUp + lenLo - 1e-3);
      const n = T.clone().sub(S).normalize();
      let pole = P.clone().sub(S);
      pole.sub(n.clone().multiplyScalar(pole.dot(n)));
      if (pole.lengthSq() < 1e-6) {
        pole = new THREE.Vector3(0, -1, 0);
        pole.sub(n.clone().multiplyScalar(pole.dot(n)));
        if (pole.lengthSq() < 1e-6) pole.set(0, 0, -1);
      }
      pole.normalize();
      const cosA = THREE.MathUtils.clamp(
        (lenUp * lenUp + d * d - lenLo * lenLo) / (2 * lenUp * d), -1, 1);
      const sinA = Math.sqrt(1 - cosA * cosA);
      const E = S.clone().add(n.clone().multiplyScalar(lenUp * cosA))
        .add(pole.clone().multiplyScalar(lenUp * sinA));
      driveDir(up, rest.up, E.clone().sub(S), s);
      driveDir(lo, rest.lo, T.clone().sub(E), s);
      if (hand && rest.hand && mpPk && mpIx) {
        const hd = mp2three(mpPk).add(mp2three(mpIx)).multiplyScalar(0.5).sub(mp2three(mpWr));
        driveDir(hand, rest.hand, hd, 0.4);
      }
    };

    const drive = (poseRes) => {
      if (!bones) bones = grabBones();
      if (!bones) return;
      const mir = apiRef.current.mirror;
      const wRaw = poseRes && poseRes.worldLandmarks && poseRes.worldLandmarks[0];
      const w = smoothWorld(wRaw, performance.now() / 1000);
      const L = mir ? { sh: 12, el: 14, wr: 16, hip: 24, ear: 8, pk: 18, ix: 20 }
                    : { sh: 11, el: 13, wr: 15, hip: 23, ear: 7, pk: 17, ix: 19 };
      const R = mir ? { sh: 11, el: 13, wr: 15, hip: 23, ear: 7, pk: 17, ix: 19 }
                    : { sh: 12, el: 14, wr: 16, hip: 24, ear: 8, pk: 18, ix: 20 };
      if (!w) return;
      // 頭: 鼻+両耳から推定(変身後はマスク — 体優先)
      if (bones.head) {
        const earL = mp2three(w[L.ear]), earR = mp2three(w[R.ear]), nose = mp2three(w[0]);
        const E = earL.clone().sub(earR);
        const yaw = Math.atan2(E.z, E.x);
        const roll = Math.atan2(E.y, Math.hypot(E.x, E.z));
        const mid = earL.clone().add(earR).multiplyScalar(0.5);
        const fwd = nose.clone().sub(mid);
        const pitch = THREE.MathUtils.clamp(
          Math.atan2(fwd.y, Math.hypot(fwd.x, fwd.z)) + 0.35, -0.55, 0.55);
        const qh = new THREE.Quaternion().setFromEuler(
          new THREE.Euler(-pitch * 0.9, -yaw * 0.9, -roll * 0.9, 'YXZ'));
        worldToLocal(bones.head, qh.multiply(bones.head.userData.bindWorldQ), 0.35);
      }
      // 胴: 肩線+腰線
      if (bones.chest) {
        const shL = mp2three(w[L.sh]), shR = mp2three(w[R.sh]);
        const hipL = mp2three(w[L.hip]), hipR = mp2three(w[R.hip]);
        const S = shL.clone().sub(shR);
        const yaw = Math.atan2(S.z, S.x);
        const roll = Math.atan2(S.y, Math.hypot(S.x, S.z));
        const shMid = shL.clone().add(shR).multiplyScalar(0.5);
        const hipMid = hipL.clone().add(hipR).multiplyScalar(0.5);
        const spine = shMid.clone().sub(hipMid).normalize();
        const pitch = Math.atan2(-spine.z, spine.y);
        const qT = new THREE.Quaternion().setFromEuler(
          new THREE.Euler(pitch * 0.8, -yaw * 0.7, -roll * 0.8, 'YXZ'));
        worldToLocal(bones.chest, qT.multiply(bones.chest.userData.bindWorldQ), 0.25);
        if (bones.hips) {
          const qH = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, -yaw * 0.3, 0));
          worldToLocal(bones.hips, qH.multiply(bones.hips.userData.bindWorldQ), 0.2);
        }
      }
      vrm.scene.updateMatrixWorld(true);
      const vis = (i) => wRaw && wRaw[i] && (wRaw[i].visibility ?? 1) > 0.35;
      if (vis(L.sh) && vis(L.el) && vis(L.wr)) {
        solveArm(bones.lUp, bones.lLo, bones.lHand,
          { up: bones.rest.lUp, lo: bones.rest.lLo, hand: bones.rest.lHand },
          bones.len.lUp, bones.len.lLo, w[L.sh], w[L.el], w[L.wr], w[L.pk], w[L.ix], 0.45);
      }
      if (vis(R.sh) && vis(R.el) && vis(R.wr)) {
        solveArm(bones.rUp, bones.rLo, bones.rHand,
          { up: bones.rest.rUp, lo: bones.rest.rLo, hand: bones.rest.rHand },
          bones.len.rUp, bones.len.rLo, w[R.sh], w[R.el], w[R.wr], w[R.pk], w[R.ix], 0.45);
      }
    };

    const drawLandmarks = (poseRes) => {
      const c = canvasRef.current;
      if (!c) return;
      const ctx = c.getContext('2d');
      ctx.fillStyle = '#04080d'; ctx.fillRect(0, 0, c.width, c.height);
      const b = poseRes && poseRes.landmarks && poseRes.landmarks[0];
      if (!b) return;
      const X = (x) => (apiRef.current.mirror ? (1 - x) : x) * c.width;
      ctx.fillStyle = '#ffa23f';
      for (const p of b) {
        if ((p.visibility ?? 1) > 0.4) {
          ctx.beginPath(); ctx.arc(X(p.x), p.y * c.height, 2.5, 0, 6.283); ctx.fill();
        }
      }
    };

    const loop = () => {
      if (disposed || !run) return;
      let pr = null;
      try { pr = pose.detectForVideo(video, performance.now()); } catch {}
      drawLandmarks(pr);
      drive(pr);
      requestAnimationFrame(loop);
    };

    apiRef.current.toggle = async () => {
      if (run) {
        run = false;
        if (video && video.srcObject) video.srcObject.getTracks().forEach((t) => t.stop());
        setRunning(false); setStatus('停止しました');
        return;
      }
      try {
        setStatus('MediaPipe 初期化中…');
        const vision = await import('@mediapipe/tasks-vision');
        const files = await vision.FilesetResolver.forVisionTasks(
          'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm');
        pose = await vision.PoseLandmarker.createFromOptions(files, {
          baseOptions: {
            modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task',
            delegate: 'GPU',
          },
          runningMode: 'VIDEO', numPoses: 1,
        });
        if (!video) {
          video = document.createElement('video');
          video.style.display = 'none'; video.muted = true; video.playsInline = true;
          document.body.appendChild(video);
        }
        const stream = await navigator.mediaDevices.getUserMedia(
          { video: { width: 640, height: 480 }, audio: false });
        video.srcObject = stream;
        await video.play();
        run = true; bones = null; euro = null;
        setRunning(true);
        setStatus('追跡中 — Two-Bone IK + One Euro(映像は表示・保存しません)');
        loop();
      } catch (e) {
        setStatus('カメラ起動失敗: ' + (e.message || e));
      }
    };

    const clock = new THREE.Clock();
    const animate = () => {
      if (disposed) return;
      requestAnimationFrame(animate);
      if (vrm) vrm.update(clock.getDelta());
      renderer.render(scene, camera);
    };
    animate();

    (async () => {
      try {
        const m = await fetchManifest(code);
        if (disposed || !m.files.vrm) {
          if (!m.files.vrm) setStatus('このパッケージにはVRMがありません');
          return;
        }
        setStatus('鎧データを転送中…');
        const loader = new GLTFLoader();
        loader.register((parser) => new VRMLoaderPlugin(parser));
        const gltf = await loader.loadAsync(fileUrl(code, m.files.vrm));
        vrm = gltf.userData.vrm;
        VRMUtils.rotateVRM0(vrm);  // VRM0はZ+向き — VRM1と同じ向きに揃える
        scene.add(vrm.scene);
        setStatus('準備完了 — カメラを開始してください');
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
      disposed = true; run = false;
      if (video && video.srcObject) video.srcObject.getTracks().forEach((t) => t.stop());
      window.removeEventListener('resize', onResize);
      renderer.dispose(); pmrem.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, [code]);

  useEffect(() => { apiRef.current.mirror = mirrorMode; }, [mirrorMode]);

  return (
    <main style={{ position: 'fixed', inset: 0 }}>
      <div ref={mountRef} style={{ position: 'absolute', inset: 0 }} />
      <div style={{ position: 'absolute', top: 14, left: 18, textShadow: '0 1px 6px #000' }}>
        <div style={{ fontSize: 11, letterSpacing: '0.4em', color: '#5fc7e8' }}>蒸着執行録 / MIRROR</div>
        <div style={{ fontSize: 20, letterSpacing: '0.12em' }}>{code}</div>
      </div>
      <div style={{
        position: 'absolute', bottom: 18, left: 18, display: 'flex', gap: 10,
        alignItems: 'center', flexWrap: 'wrap',
      }}>
        <button onClick={() => apiRef.current.toggle && apiRef.current.toggle()} style={{
          background: running ? '#5a2430' : 'linear-gradient(135deg,#1d5f8a,#2c8fbf)',
          color: '#fff', border: 'none', borderRadius: 8, padding: '10px 18px',
          fontSize: 14, cursor: 'pointer', letterSpacing: '0.2em',
        }}>{running ? '停止' : 'カメラ開始'}</button>
        <label style={{ fontSize: 12, color: '#dce8f2', cursor: 'pointer' }}>
          <input type="checkbox" checked={mirrorMode}
            onChange={(e) => setMirrorMode(e.target.checked)} /> 鏡像
        </label>
        <canvas ref={canvasRef} width={192} height={144}
          style={{ border: '1px solid #24425a', background: '#04080d', borderRadius: 4 }} />
        <span style={{ fontSize: 12, color: '#8fa7b8', maxWidth: 380 }}>{status}</span>
      </div>
      <a href={`/s/${code}`} style={{
        position: 'absolute', top: 16, right: 18, color: '#5a7284', fontSize: 12,
        textDecoration: 'none',
      }}>← ビューアへ</a>
    </main>
  );
}
