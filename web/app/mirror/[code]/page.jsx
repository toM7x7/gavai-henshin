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
import { VRMAnimationLoaderPlugin, createVRMAnimationClip } from '@pixiv/three-vrm-animation';
import { fetchManifest, fileUrl, setArmorVisible } from '../../../lib/suit';
import { TRIGGER_RE, announce, hasNativeSR, pickAudioMime, recordChunk, transcribe, sttEnabled } from '../../../lib/stt';

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
  const [voiceOn, setVoiceOn] = useState(false);
  const [flashKey, setFlashKey] = useState(0);
  const [worn, setWorn] = useState(false);
  const [arMode, setArMode] = useState(false);  // 実写合成(カメラ映像に重ねる)

  useEffect(() => {
    if (!mountRef.current || !code) return;
    let disposed = false;
    const mount = mountRef.current;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
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
    const grid = new THREE.GridHelper(4, 24, 0x1a3448, 0x0d1c28);
    scene.add(grid);
    const key = new THREE.DirectionalLight(0xffffff, 1.4);
    key.position.set(2, 3, 2);
    scene.add(key);

    let vrm = null, bones = null, euro = null;
    let pose = null, video = null, run = false;
    let vrmaData = null, mixer = null, motionPlaying = false, particles = null;

    // VRM Humanoid 正規化リグからボーンを取得し、バインド情報を実測
    const grabBones = () => {
      if (!vrm) return null;
      const h = vrm.humanoid;
      const g = (n) => h.getNormalizedBoneNode(n);
      const b = {
        head: g('head'), chest: g('upperChest') || g('chest'), hips: g('hips'),
        hipsNode: g('hips'),
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

    // ---- 蒸着: 素体に鎧が装着される瞬間 ----
    // フラッシュ + SE + 粒子収束 + 鎧マテリアライズ + ヘンシンモーション。
    // スタートは必ず「変身していない状態」から(2026-07-11方針)
    const henshin = () => {
      if (!vrm || motionPlaying) return;
      motionPlaying = true;
      setFlashKey((k) => k + 1);
      try { new Audio('/se/henshin.mp3').play().catch(() => {}); } catch {}
      setArmorVisible(vrm.scene, true);   // 閃光の中で鎧が現れる
      setWorn(true);
      // 粒子収束(蒸着エネルギー)
      const N = 1600;
      const pos = new Float32Array(N * 3);
      for (let i = 0; i < N; i++) {
        const r = 1.2 + Math.random() * 2.2, a = Math.random() * 6.283;
        pos[i * 3] = Math.cos(a) * r;
        pos[i * 3 + 1] = Math.random() * 2.0;
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
      // ヘンシンモーション(henshin.vrma — 構え→溜め→十字受け→展開→見得)
      if (vrmaData) {
        const clip = createVRMAnimationClip(vrmaData, vrm);
        mixer = new THREE.AnimationMixer(vrm.scene);
        const action = mixer.clipAction(clip);
        action.setLoop(THREE.LoopOnce);
        action.clampWhenFinished = true;
        mixer.addEventListener('finished', () => {
          mixer.stopAllAction();
          mixer = null;
          bones = null;   // 追跡再開時にバインドポーズへ戻して再実測
          motionPlaying = false;
          setStatus('蒸着完了 — 体連携を再開');
          announce('蒸着、完了。');
        });
        action.play();
        setStatus('蒸着 — ヘンシンモーション実行中');
      } else {
        setTimeout(() => { motionPlaying = false; announce('蒸着、完了。'); }, 2400);
      }
    };
    apiRef.current.henshin = henshin;

    // 解除: 鎧を還す(巻き戻し)。素体に戻って何度でも蒸着できる
    apiRef.current.release = () => {
      if (!vrm || motionPlaying) return;
      setFlashKey((k) => k + 1);
      setArmorVisible(vrm.scene, false);
      setWorn(false);
      setStatus('蒸着解除 — 素体待機。「蒸着!」でいつでも装着');
    };

    const drive = (poseRes) => {
      if (motionPlaying) return;  // 見得の最中は追跡を握らせない
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

      // ---- 実写AR合成: カメラ映像内の体にスーツを整列 ----
      // 2Dランドマーク(画面座標)を z=0 平面へ逆投影し、腰の位置と
      // 肩-腰スパンでアバターの位置・スケールを実写の体に合わせる。
      // v1は遮蔽なしオーバーレイ(前後関係は Image Segmenter 導入のv2で)
      const lm2d = apiRef.current.ar && poseRes && poseRes.landmarks && poseRes.landmarks[0];
      if (lm2d && bones.hipsNode) {
        const toWorld = (nx, ny) => {
          const v = new THREE.Vector3((mir ? 1 - nx : nx) * 2 - 1, -(ny * 2 - 1), 0.5)
            .unproject(camera);
          const dir = v.sub(camera.position).normalize();
          const t = (0 - camera.position.z) / dir.z;   // z=0 平面と交差
          return camera.position.clone().add(dir.multiplyScalar(t));
        };
        const hipW = toWorld((lm2d[23].x + lm2d[24].x) / 2, (lm2d[23].y + lm2d[24].y) / 2);
        const shW = toWorld((lm2d[11].x + lm2d[12].x) / 2, (lm2d[11].y + lm2d[12].y) / 2);
        const span = hipW.distanceTo(shW);
        // アバター側の同スパン(肩=両上腕付根の中点)
        const aHip = bones.hipsNode.getWorldPosition(new THREE.Vector3());
        const aSh = bones.lUp.getWorldPosition(new THREE.Vector3())
          .add(bones.rUp.getWorldPosition(new THREE.Vector3())).multiplyScalar(0.5);
        const aSpan = Math.max(1e-3, aHip.distanceTo(aSh));
        const cur = vrm.scene.scale.x || 1;
        const target = THREE.MathUtils.clamp(cur * (span / aSpan), 0.4, 3.0);
        const next = cur + (target - cur) * 0.15;   // 呼吸レベルの揺れは均す
        if (Math.abs(next / cur - 1) > 1e-4) {
          const f = next / cur;
          vrm.scene.scale.setScalar(next);
          for (const k in bones.len) bones.len[k] *= f;  // IKの腕長も追従
        }
        vrm.scene.updateMatrixWorld(true);
        const aHip2 = bones.hipsNode.getWorldPosition(new THREE.Vector3());
        const shift = hipW.sub(aHip2);
        vrm.scene.position.add(shift.multiplyScalar(0.35));  // 位置も滑らかに寄せる
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

    // 実写モードの見た目切替: カメラ映像を背景に出し、WebGLを透過させる
    apiRef.current.applyAr = () => {
      const ar = apiRef.current.ar;
      scene.background = ar ? null : new THREE.Color(0x04080d);
      grid.visible = !ar;
      if (video) {
        video.style.display = ar ? 'block' : 'none';
        Object.assign(video.style, {
          position: 'fixed', inset: '0', width: '100%', height: '100%',
          objectFit: 'cover', zIndex: '0',
          transform: apiRef.current.mirror ? 'scaleX(-1)' : 'none',
        });
      }
      mount.style.zIndex = '1';
      if (!ar && vrm) {
        // 点群モードに戻す時は定位置へ
        vrm.scene.position.set(0, 0, 0);
        vrm.scene.scale.setScalar(1);
        bones = null;
      }
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
        apiRef.current.applyAr();
        setStatus(apiRef.current.ar
          ? '実写合成 — 君の体にスーツが重なる。「蒸着!」と唱えよ'
          : '追跡中 — Two-Bone IK + One Euro(映像は表示・保存しません)');
        loop();
      } catch (e) {
        setStatus('カメラ起動失敗: ' + (e.message || e));
      }
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
        const k = Math.min(1, u.t / 1.6);
        const p = particles.geometry.attributes.position;
        for (let i = 0; i < p.count; i++) {
          p.array[i * 3] = u.start[i * 3] * (1 - k * 0.985);
          p.array[i * 3 + 2] = u.start[i * 3 + 2] * (1 - k * 0.985);
        }
        p.needsUpdate = true;
        particles.material.opacity = 0.95 * (1 - k);
        if (k >= 1) { scene.remove(particles); particles = null; }
      }
      if (vrm) vrm.update(dt);
      renderer.render(scene, camera);
    };
    animate();

    // ---- 音声認証(ハイブリッド) ----
    // 一次: Web Speech(Chrome系 — 低遅延・無料)
    // 二次: Sakura Whisper(/api/stt 経由。Questブラウザ等 Web Speech 不在の道)
    let rec = null, wantVoice = false, whisperStream = null;
    const whisperLoop = async () => {
      const mime = pickAudioMime();
      if (!mime) { setStatus('この端末は録音に未対応です'); wantVoice = false; setVoiceOn(false); return; }
      try {
        whisperStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch { setStatus('マイクを起動できません'); wantVoice = false; setVoiceOn(false); return; }
      setStatus('音声認証 待機中(Sakura Whisper)—「蒸着!」と唱えよ');
      while (wantVoice && !disposed) {
        try {
          const blob = await recordChunk(whisperStream, 2600, mime);
          if (!wantVoice || disposed) break;
          const text = await transcribe(blob);
          if (TRIGGER_RE.test(text)) henshin();
        } catch { /* 一時失敗は無視して次のチャンクへ */ }
      }
      if (whisperStream) { whisperStream.getTracks().forEach((t) => t.stop()); whisperStream = null; }
    };
    apiRef.current.voiceToggle = async () => {
      if (wantVoice) {
        wantVoice = false;
        try { rec && rec.stop(); } catch {}
        setVoiceOn(false);
        setStatus('音声認証 OFF');
        return;
      }
      if (hasNativeSR()) {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        rec = new SR();
        rec.lang = 'ja-JP';
        rec.continuous = true;
        rec.interimResults = true;
        rec.onresult = (e) => {
          for (let i = e.resultIndex; i < e.results.length; i++) {
            const t = e.results[i][0].transcript;
            if (TRIGGER_RE.test(t)) { henshin(); break; }
          }
        };
        rec.onend = () => { if (wantVoice && !disposed) { try { rec.start(); } catch {} } };
        rec.onerror = () => {};
        wantVoice = true;
        try { rec.start(); setVoiceOn(true); setStatus('音声認証 待機中 — 「蒸着!」と唱えよ'); }
        catch { wantVoice = false; }
      } else if (await sttEnabled()) {
        wantVoice = true;
        setVoiceOn(true);
        whisperLoop();
      } else {
        setStatus('この端末は音声認識に未対応です(Whisper未設定 — Vercel に SAKURA_AI_ENGINE_TOKEN を)');
      }
    };

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
        loader.register((parser) => new VRMAnimationLoaderPlugin(parser));
        const gltf = await loader.loadAsync(fileUrl(code, m.files.vrm));
        vrm = gltf.userData.vrm;
        VRMUtils.rotateVRM0(vrm);  // VRM0はZ+向き — VRM1と同じ向きに揃える
        scene.add(vrm.scene);
        if (m.files.vrma) {
          try {
            const ag = await loader.loadAsync(fileUrl(code, m.files.vrma));
            vrmaData = (ag.userData.vrmAnimations || [])[0] || null;
          } catch { vrmaData = null; }
        }
        setArmorVisible(vrm.scene, false);  // スタートは素体から — これが儀式の前提
        setWorn(false);
        setStatus('素体待機 — カメラを開始し、「蒸着!」と唱えよ');
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

  useEffect(() => { apiRef.current.mirror = mirrorMode; apiRef.current.applyAr && apiRef.current.applyAr(); }, [mirrorMode]);
  useEffect(() => { apiRef.current.ar = arMode; apiRef.current.applyAr && apiRef.current.applyAr(); }, [arMode]);

  return (
    <main style={{ position: 'fixed', inset: 0 }}>
      <div ref={mountRef} style={{ position: 'absolute', inset: 0 }} />
      {flashKey > 0 && <div key={flashKey} className="henshin-flash" />}
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
        <button onClick={() => apiRef.current.voiceToggle && apiRef.current.voiceToggle()} style={{
          background: voiceOn ? 'linear-gradient(135deg,#7a5a1d,#bf8f2c)' : '#0a121c',
          color: voiceOn ? '#fff' : '#d9b45f', border: '1px solid #4a3a1a',
          borderRadius: 8, padding: '10px 18px', fontSize: 14, cursor: 'pointer',
          letterSpacing: '0.15em',
        }}>{voiceOn ? '音声認証 待機中' : '音声認証 ON'}</button>
        <button onClick={() => (worn
          ? apiRef.current.release && apiRef.current.release()
          : apiRef.current.henshin && apiRef.current.henshin())} style={{
          background: worn ? '#0a121c' : 'linear-gradient(135deg,#1d5f8a,#2c8fbf)',
          color: worn ? '#9fdcff' : '#fff', border: '1px solid #24425a',
          borderRadius: 8, padding: '10px 18px', fontSize: 14, cursor: 'pointer',
          letterSpacing: '0.25em',
        }}>{worn ? '解除' : '蒸着'}</button>
        <label style={{ fontSize: 12, color: '#dce8f2', cursor: 'pointer' }}>
          <input type="checkbox" checked={mirrorMode}
            onChange={(e) => setMirrorMode(e.target.checked)} /> 鏡像
        </label>
        <label style={{ fontSize: 12, color: '#dce8f2', cursor: 'pointer' }}>
          <input type="checkbox" checked={arMode}
            onChange={(e) => setArMode(e.target.checked)} /> 実写に重ねる(AR)
        </label>
        <canvas ref={canvasRef} width={192} height={144}
          style={{ border: '1px solid #24425a', background: '#04080d', borderRadius: 4 }} />
        <span style={{ fontSize: 12, color: '#8fa7b8', maxWidth: 380 }}>{status}</span>
      </div>
      <nav className="topnav">
        <a href="/">⌂ 扉へ</a>
        <a href={`/s/${code}`}>← 蒸着室</a>
      </nav>
    </main>
  );
}
