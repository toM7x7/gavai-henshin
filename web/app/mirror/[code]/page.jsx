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
import { fetchManifest, fileUrl, setArmorVisible, setBodyVisible } from '../../../lib/suit';
import { TRIGGER_RE, announce, hasNativeSR, pickAudioMime, recordChunk, transcribe, sttEnabled } from '../../../lib/stt';

// MediaPipe Pose 33点の骨格辺(dev計測: 体取得検証オーバーレイ用)
const SKEL = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [24, 26], [26, 28],
  [27, 29], [27, 31], [28, 30], [28, 32],
  [0, 7], [0, 8],
];

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
  const debugRef = useRef(null);   // dev用: AR整列の十字マーカー描画先
  const apiRef = useRef({});
  const [status, setStatus] = useState('鏡を準備中…');
  const [running, setRunning] = useState(false);
  const [mirrorMode, setMirrorMode] = useState(true);
  const [voiceOn, setVoiceOn] = useState(false);
  const [flashKey, setFlashKey] = useState(0);
  const [worn, setWorn] = useState(false);
  const [arMode, setArMode] = useState(false);  // 実写合成(カメラ映像に重ねる)
  // 実写ARは整列品質が未達のためユーザー向けには非公開(2026-07-11 T12)。
  // /mirror/<code>?dev=1 でのみトグルが現れる — 機能は温存し裏で磨く
  const [devMode, setDevMode] = useState(false);
  useEffect(() => {
    setDevMode(new URLSearchParams(window.location.search).has('dev'));
  }, []);
  // AR計測パネル(dev): ①骨格=体を撮れているかの検証 ②残差=モデル追従の検証。
  // 二つを分離して確かめられることが「がっちゃんこ」前の前提
  const [dbgSkel, setDbgSkel] = useState(true);
  const [dbgResid, setDbgResid] = useState(true);
  const [dbgModel, setDbgModel] = useState(true);
  const [dbgMask, setDbgMask] = useState(true);   // ③蒸着後の実写マスク(自分を沈める)
  const devInfoRef = useRef(null);

  useEffect(() => {
    if (!mountRef.current || !code) return;
    let disposed = false;
    const mount = mountRef.current;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    // レイヤ規約: mount内 video=0 / マスクfx=1 / WebGL=2、mount外 debug=3 / HUD=5 / CTA=6 / 計測=7 / nav=10。
    // videoは必ずmountの中に置く — body直下だとfixedのmainがstacking contextになり
    // (Chromium)、後入れのvideoがUI全部の上に描画される事故になる
    Object.assign(renderer.domElement.style, { position: 'absolute', inset: '0', zIndex: '2' });
    mount.appendChild(renderer.domElement);
    // 実写マスク中間レイヤ: 蒸着後、実写の自分をシルエットに沈める(ヒーロー像の成立)
    const fxCan = document.createElement('canvas');
    Object.assign(fxCan.style, {
      position: 'absolute', inset: '0', width: '100%', height: '100%',
      pointerEvents: 'none', zIndex: '1',
    });
    mount.appendChild(fxCan);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x9aa3ac);  // 素体(黒)が沈まないスタジオグレー
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    const camera = new THREE.PerspectiveCamera(40, mount.clientWidth / mount.clientHeight, 0.01, 50);
    camera.position.set(0, 1.25, 2.6);
    camera.lookAt(0, 0.95, 0);
    const grid = new THREE.GridHelper(4, 24, 0x7b8790, 0x8d97a0);
    scene.add(grid);
    const key = new THREE.DirectionalLight(0xffffff, 1.4);
    key.position.set(2, 3, 2);
    scene.add(key);

    let vrm = null, bones = null, euro = null;
    let pose = null, video = null, run = false;
    let vrmaData = null, mixer = null, motionPlaying = false, particles = null;
    let wornFlag = false;   // React stateはクロージャで古くなるため、applyAr用に生フラグを持つ
    let arDbg = { dist: 0, yaw: 0 };                    // dev計測パネルに出す配置推定値
    let detectErr = null, fpsT = 0, fpsV = 0, infoT = 0;

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
        lUpLeg: g('leftUpperLeg'), lLoLeg: g('leftLowerLeg'), lFoot: g('leftFoot'),
        rUpLeg: g('rightUpperLeg'), rLoLeg: g('rightLowerLeg'), rFoot: g('rightFoot'),
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
        lUpLeg: seg(b.lUpLeg, b.lLoLeg), lLoLeg: seg(b.lLoLeg, b.lFoot),
        rUpLeg: seg(b.rUpLeg, b.rLoLeg), rLoLeg: seg(b.rLoLeg, b.rFoot),
      };
      b.len = {
        lUp: len(b.lUp, b.lLo), lLo: len(b.lLo, b.lHand),
        rUp: len(b.rUp, b.rLo), rLo: len(b.rLo, b.rHand),
        lUpLeg: len(b.lUpLeg, b.lLoLeg), lLoLeg: len(b.lLoLeg, b.lFoot),
        rUpLeg: len(b.rUpLeg, b.rLoLeg), rLoLeg: len(b.rLoLeg, b.rFoot),
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
      setBodyVisible(vrm.scene, true);    // AR: 素体(アンダースーツ)ごと現れる — 空洞の鎧を防ぐ
      setWorn(true);
      wornFlag = true;
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
      // ヘンシンモーション(henshin.vrma — 構え→溜め→十字受け→展開→見得)。
      // 実写ARでは体が主役: 数秒の缶詰モーションは実写とズレて破綻するので
      // スキップし、追跡を途切れさせない(閃光+粒子+マスクが演出を担う)
      if (apiRef.current.ar) {
        motionPlaying = false;
        setStatus('蒸着完了 — 君がヒーローだ');
        setTimeout(() => announce('蒸着、完了。'), 900);
      } else if (vrmaData) {
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
      setBodyVisible(vrm.scene, !apiRef.current.ar);  // ARでは素の自分に戻る
      setWorn(false);
      wornFlag = false;
      setStatus('蒸着解除 — 素体待機。「蒸着!」でいつでも装着');
    };

    // 2Dアンカー用の平滑化バンク(worldとは別 — 実写ARの吸い付き用)
    let euro2d = null;
    const sm2 = (i, pt) => {
      if (!euro2d) euro2d = {};
      if (!euro2d[i]) euro2d[i] = { x: new OneEuro(1.4, 0.9), y: new OneEuro(1.4, 0.9) };
      const t = performance.now() / 1000;
      return { x: euro2d[i].x.f(pt.x, t), y: euro2d[i].y.f(pt.y, t) };
    };

    const drive = (poseRes) => {
      if (motionPlaying) return;  // 見得の最中は追跡を握らせない
      if (!bones) bones = grabBones();
      if (!bones) return;
      const mir = apiRef.current.mirror;
      const ar = apiRef.current.ar;
      const wRaw = poseRes && poseRes.worldLandmarks && poseRes.worldLandmarks[0];
      const w = smoothWorld(wRaw, performance.now() / 1000);
      const lm2d = poseRes && poseRes.landmarks && poseRes.landmarks[0];
      const L = mir ? { sh: 12, el: 14, wr: 16, hip: 24, ear: 8, pk: 18, ix: 20, kn: 26, an: 28 }
                    : { sh: 11, el: 13, wr: 15, hip: 23, ear: 7, pk: 17, ix: 19, kn: 25, an: 27 };
      const R = mir ? { sh: 11, el: 13, wr: 15, hip: 23, ear: 7, pk: 17, ix: 19, kn: 25, an: 27 }
                    : { sh: 12, el: 14, wr: 16, hip: 24, ear: 8, pk: 18, ix: 20, kn: 26, an: 28 };
      if (!w) {
        // 体が取れていない — dev計測に明示(体取得検証の第一関門)
        if (ar) {
          const dbg0 = apiRef.current.debugCanvas;
          if (dbg0) dbg0.getContext('2d').clearRect(0, 0, dbg0.width, dbg0.height);
          const info0 = apiRef.current.devInfo;
          if (info0) info0.textContent = detectErr
            ? `推論エラー: ${detectErr}`
            : '捕捉 ✗ 体が見つからない — 全身が入る距離・明るさに';
        }
        return;
      }
      const vis = (i) => wRaw && wRaw[i] && (wRaw[i].visibility ?? 1) > 0.35;
      const wrapA = (a) => Math.atan2(Math.sin(a), Math.cos(a));

      // ---- 画面写像(実写AR): cover crop 補正 + ミラー ----
      // ★T12根本原因: 映像は object-fit:cover でクロップ表示されるが、
      // ランドマークはクロップ前の動画フレーム正規化座標
      const W = mount.clientWidth, H = mount.clientHeight;
      const coverMap = (nx, ny) => {
        const vw = video && video.videoWidth, vh = video && video.videoHeight;
        if (!vw || !vh) return { x: nx, y: ny };
        const cs = Math.max(W / vw, H / vh);
        return {
          x: (nx * vw * cs + (W - vw * cs) / 2) / W,
          y: (ny * vh * cs + (H - vh * cs) / 2) / H,
        };
      };
      const toScreen = (nx, ny) => {
        const m = coverMap(nx, ny);
        return { x: mir ? 1 - m.x : m.x, y: m.y };  // CSSのscaleX(-1)と同じ向き
      };
      // 画面点を通るレイ上の、指定ワールドZの点(横位置=画面精度、奥行きは別供給)
      const rayAtZ = (scr, z) => {
        const v = new THREE.Vector3(scr.x * 2 - 1, -(scr.y * 2 - 1), 0.5).unproject(camera);
        const dir = v.sub(camera.position).normalize();
        const t = (z - camera.position.z) / dir.z;
        return camera.position.clone().add(dir.multiplyScalar(t));
      };
      const rayDir = (scr) => new THREE.Vector3(scr.x * 2 - 1, -(scr.y * 2 - 1), 0.5)
        .unproject(camera).sub(camera.position).normalize();

      // ---- 実写AR: 全身の配置を最初に確定(奥行き+体の向き) ----
      // スケールは等倍固定 — 見かけサイズは「カメラからの距離」で表現する。
      // 距離 = 焦点距離(px) × アバターの肩腰スパン(m) ÷ 画面上のスパン(px)。
      // 近寄る/離れるが遠近として正しく出る(連続リスケールは廃止)
      if (ar && lm2d && bones.hipsNode && bones.lUp && bones.rUp) {
        const h23 = sm2(23, lm2d[23]), h24 = sm2(24, lm2d[24]);
        const s11 = sm2(11, lm2d[11]), s12 = sm2(12, lm2d[12]);
        const hipS = toScreen((h23.x + h24.x) / 2, (h23.y + h24.y) / 2);
        const shS = toScreen((s11.x + s12.x) / 2, (s11.y + s12.y) / 2);
        const pixSpan = Math.max(1, Math.hypot((hipS.x - shS.x) * W, (hipS.y - shS.y) * H));
        vrm.scene.updateMatrixWorld(true);
        const aHip = bones.hipsNode.getWorldPosition(new THREE.Vector3());
        const aSh = bones.lUp.getWorldPosition(new THREE.Vector3())
          .add(bones.rUp.getWorldPosition(new THREE.Vector3())).multiplyScalar(0.5);
        const aSpan = Math.max(1e-3, aHip.distanceTo(aSh));
        const fpx = 0.5 * H / Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
        const dist = THREE.MathUtils.clamp(fpx * aSpan / pixSpan, 0.8, 8);
        const ndcV = new THREE.Vector3(hipS.x * 2 - 1, -(hipS.y * 2 - 1), 0.5).unproject(camera);
        const dir = ndcV.sub(camera.position).normalize();
        const hipTarget = camera.position.clone().add(dir.multiplyScalar(dist));
        vrm.scene.position.add(hipTarget.sub(aHip).multiplyScalar(0.45));
        // 体の向き: 腰ラインのyawでルートごと回す(胸だけ捻る方式を廃止 —
        // 横を向いた時に脚・胴が実写と揃うための土台)
        const hd = mp2three(w[L.hip]).sub(mp2three(w[R.hip]));
        const rootYaw = -Math.atan2(hd.z, hd.x);
        vrm.scene.rotation.y += wrapA(rootYaw - vrm.scene.rotation.y) * 0.25;
        vrm.scene.updateMatrixWorld(true);
        arDbg.dist = dist; arDbg.yaw = vrm.scene.rotation.y;
      }

      // ---- 頭: 鼻+両耳から推定(変身後はマスク — 体優先) ----
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

      // ---- 胴: 肩線+腰線 ----
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
        if (!ar && bones.hips) {   // ARではルートyawが体の向きを担う
          const qH = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, -yaw * 0.3, 0));
          worldToLocal(bones.hips, qH.multiply(bones.hips.userData.bindWorldQ), 0.2);
        }
      }
      vrm.scene.updateMatrixWorld(true);

      if (!ar) {
        // ---- 点群モード: 従来のworld空間IK(腕のみ) ----
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
        return;
      }

      // ---- 実写AR: 画面空間拘束IK — 手足を実写の手足そのものに重ねる ----
      // 目標(手首/足首)と中間関節(肘/膝)は「2Dランドマークを通るレイ」上に置く。
      // 横位置は画面ピクセル精度、奥行きだけworldランドマークの相対Zを使う
      if (!lm2d) return;
      const ik2d = (upK, loK, SH, EL, WR, str) => {
        const up = bones[upK], lo = bones[loK];
        const restUp = bones.rest[upK], restLo = bones.rest[loK];
        const lenUp = bones.len[upK], lenLo = bones.len[loK];
        if (!up || !lo || !restUp || !restLo || !(lenUp > 1e-4) || !(lenLo > 1e-4)) return null;
        if (!vis(SH) || !vis(EL) || !vis(WR)) return null;
        const S = up.getWorldPosition(new THREE.Vector3());
        const e2 = sm2(EL, lm2d[EL]), t2 = sm2(WR, lm2d[WR]);
        // 目標=「2Dレイ上で、届く範囲のうち希望奥行きに最も近い点」。
        // 固定奥行き+後段の腕長クランプだと、腕を伸ばした時に届かず
        // 画面上でズレる(実測残差40px級の正体)— レイ×到達球の交差で解く
        const reach = lenUp + lenLo - 1e-3;
        const rd = rayDir(toScreen(t2.x, t2.y));
        const ro = camera.position;
        const wantT = (S.z - (w[WR].z - w[SH].z) - ro.z) / rd.z;
        const oc = ro.clone().sub(S);
        const bq = oc.dot(rd);
        const disc = bq * bq - (oc.lengthSq() - reach * reach);
        let tPick;
        if (disc >= 0) {
          const sq = Math.sqrt(disc);
          tPick = THREE.MathUtils.clamp(wantT, -bq - sq + 1e-3, -bq + sq - 1e-3);
        } else {
          tPick = -bq;   // 幾何的に届かない: レイ上の最近点=画面ズレ最小の妥協
        }
        const T = ro.clone().add(rd.clone().multiplyScalar(Math.max(0.1, tPick)));
        const P = rayAtZ(toScreen(e2.x, e2.y), S.z - (w[EL].z - w[SH].z));
        const d = THREE.MathUtils.clamp(S.distanceTo(T),
          Math.abs(lenUp - lenLo) + 1e-3, lenUp + lenLo - 1e-3);
        const n = T.clone().sub(S).normalize();
        let pole = P.clone().sub(S);
        pole.sub(n.clone().multiplyScalar(pole.dot(n)));
        if (pole.lengthSq() < 1e-6) pole.set(0, 0, -1);
        pole.normalize();
        const cosA = THREE.MathUtils.clamp(
          (lenUp * lenUp + d * d - lenLo * lenLo) / (2 * lenUp * d), -1, 1);
        const sinA = Math.sqrt(1 - cosA * cosA);
        const E = S.clone().add(n.clone().multiplyScalar(lenUp * cosA))
          .add(pole.clone().multiplyScalar(lenUp * sinA));
        driveDir(up, restUp, E.clone().sub(S), str);
        driveDir(lo, restLo, T.clone().sub(E), str);
        return t2;
      };
      ik2d('lUp', 'lLo', L.sh, L.el, L.wr, 0.6);
      ik2d('rUp', 'rLo', R.sh, R.el, R.wr, 0.6);
      ik2d('lUpLeg', 'lLoLeg', L.hip, L.kn, L.an, 0.55);
      ik2d('rUpLeg', 'rLoLeg', R.hip, R.kn, R.an, 0.55);

      // ---- dev計測: ①体取得 ②モデル追従 を分離して検証する可視化 ----
      // 骨格(緑系)が実写の体に乗る → 検出+cover写像は正しい。
      // その上でマゼンタ○(モデル関節の投影)が骨格に重なる → 追従も正しい。
      // 骨格が乗らなければ取得/写像の問題、骨格は乗るが○がズレるならIK/配置の問題
      const dbg = apiRef.current.debugCanvas;
      const opts = apiRef.current.dbgOpts || {};
      vrm.scene.visible = opts.model !== false;
      if (dbg) {
        if (dbg.width !== W || dbg.height !== H) { dbg.width = W; dbg.height = H; }
        const ctx = dbg.getContext('2d');
        ctx.clearRect(0, 0, W, H);
        const P2 = (i) => toScreen(lm2d[i].x, lm2d[i].y);
        if (opts.skel !== false) {
          for (const [a, bIdx] of SKEL) {
            const va = wRaw[a] ? (wRaw[a].visibility ?? 1) : 0;
            const vb = wRaw[bIdx] ? (wRaw[bIdx].visibility ?? 1) : 0;
            const v2 = Math.min(va, vb);
            ctx.strokeStyle = v2 > 0.6 ? 'rgba(65,224,127,0.9)'
              : v2 > 0.35 ? 'rgba(224,195,65,0.9)' : 'rgba(224,83,65,0.55)';
            ctx.lineWidth = 3;
            const pa = P2(a), pb = P2(bIdx);
            ctx.beginPath();
            ctx.moveTo(pa.x * W, pa.y * H); ctx.lineTo(pb.x * W, pb.y * H);
            ctx.stroke();
          }
          for (let i = 0; i < 33; i++) {
            const p = P2(i);
            ctx.fillStyle = vis(i) ? '#41e07f' : '#e05341';
            ctx.beginPath(); ctx.arc(p.x * W, p.y * H, 4, 0, 6.283); ctx.fill();
          }
        }
        let residTxt = '';
        if (opts.resid !== false) {
          vrm.scene.updateMatrixWorld(true);   // IK直後のボーン位置で投影する
          const v3 = new THREE.Vector3();
          const jointPairs = [
            [bones.lHand || bones.lLo, L.wr, '手L'], [bones.rHand || bones.rLo, R.wr, '手R'],
            [bones.lFoot, L.an, '足L'], [bones.rFoot, R.an, '足R'],
          ];
          for (const [bone, li, tag] of jointPairs) {
            if (!bone || !vis(li)) continue;
            bone.getWorldPosition(v3).project(camera);
            const mx = (v3.x * 0.5 + 0.5) * W, my = (0.5 - v3.y * 0.5) * H;
            const lp = P2(li);
            ctx.strokeStyle = '#ff5fd0'; ctx.lineWidth = 2;
            ctx.beginPath(); ctx.arc(mx, my, 8, 0, 6.283); ctx.stroke();
            ctx.strokeStyle = 'rgba(255,95,208,0.5)';
            ctx.beginPath(); ctx.moveTo(mx, my); ctx.lineTo(lp.x * W, lp.y * H); ctx.stroke();
            residTxt += ` ${tag}${Math.round(Math.hypot(mx - lp.x * W, my - lp.y * H))}`;
          }
        }
        const now2 = performance.now();
        fpsV = fpsT ? fpsV * 0.9 + (1000 / Math.max(1, now2 - fpsT)) * 0.1 : 0;
        fpsT = now2;
        const info = apiRef.current.devInfo;
        if (info && now2 - infoT > 200) {
          infoT = now2;
          let nVis = 0;
          for (let i = 0; i < 33; i++) if (vis(i)) nVis++;
          info.textContent =
            `捕捉 ✓ 可視 ${nVis}/33 | ${fpsV.toFixed(1)}fps\n` +
            `距離 ${arDbg.dist.toFixed(2)}m | 体yaw ${(arDbg.yaw * 57.3).toFixed(0)}°\n` +
            (residTxt ? `残差px${residTxt}` : '残差 — 手足が画面外/低確度');
        }
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
      try { pr = pose.detectForVideo(video, performance.now()); detectErr = null; }
      catch (e) { detectErr = String((e && e.message) || e); }  // 黙殺しない — dev計測に出す
      drawLandmarks(pr);
      drive(pr);
      maskFx(pr);
      if (pr && pr.segmentationMasks) {
        for (const m of pr.segmentationMasks) { try { m.close(); } catch {} }
      }
      requestAnimationFrame(loop);
    };

    // ---- 実写マスク: 蒸着後、人物領域をシルエットに沈める ----
    // 「変身した以上、素の自分が映っていてはいけない」— 人物セグメンテーションで
    // 自分の写り込み(袖・肌)を暗いシルエットに落とし、その上にモデル(素体+鎧)が乗る。
    // マスクはぼかして広めに取り、端の写り込みを柔らかく包む
    let mCan = null, mCtx = null;
    const maskFx = (pr) => {
      const W = mount.clientWidth, H = mount.clientHeight;
      if (fxCan.width !== W || fxCan.height !== H) { fxCan.width = W; fxCan.height = H; }
      const fctx = fxCan.getContext('2d');
      fctx.clearRect(0, 0, W, H);
      const mask = pr && pr.segmentationMasks && pr.segmentationMasks[0];
      const active = apiRef.current.ar && wornFlag &&
        (apiRef.current.dbgOpts || {}).mask !== false;
      if (!active || !mask || !video || !video.videoWidth) return;
      const mw = mask.width, mh = mask.height;
      if (!mCan) { mCan = document.createElement('canvas'); mCtx = mCan.getContext('2d'); }
      if (mCan.width !== mw || mCan.height !== mh) { mCan.width = mw; mCan.height = mh; }
      const data = mask.getAsFloat32Array();
      const img = mCtx.createImageData(mw, mh);
      const px = img.data;
      for (let i = 0; i < data.length; i++) {
        const a = data[i];
        px[i * 4 + 3] = a > 0.15 ? Math.min(255, a * 300) : 0;
      }
      mCtx.putImageData(img, 0, 0);
      // videoと同じcover写像+ミラーで重ねる
      const vw = video.videoWidth, vh = video.videoHeight;
      const cs = Math.max(W / vw, H / vh);
      const dx = (W - vw * cs) / 2, dy = (H - vh * cs) / 2;
      fctx.save();
      if (apiRef.current.mirror) { fctx.translate(W, 0); fctx.scale(-1, 1); }
      fctx.filter = 'blur(10px)';
      fctx.drawImage(mCan, dx, dy, vw * cs, vh * cs);
      fctx.drawImage(mCan, dx, dy, vw * cs, vh * cs);  // 2度描き=濃度を上げ実効的に拡張
      fctx.filter = 'none';
      fctx.globalCompositeOperation = 'source-in';
      fctx.filter = 'brightness(0.22) saturate(0.25)';
      fctx.drawImage(video, dx, dy, vw * cs, vh * cs);
      fctx.restore();
    };

    // 実写モードの切替: カメラ映像を背景に出し、WebGLを透過させる。
    // 実写ARでは「実写の体が素体」— VRMの素体は隠し、蒸着したら鎧だけ重ねる
    apiRef.current.applyAr = () => {
      const ar = apiRef.current.ar;
      scene.background = ar ? null : new THREE.Color(0x9aa3ac);
      grid.visible = !ar;
      if (video) {
        video.style.display = ar ? 'block' : 'none';
        video.style.transform = apiRef.current.mirror ? 'scaleX(-1)' : 'none';
      }
      if (vrm) {
        vrm.scene.visible = true;   // AR計測トグルで消していても復帰
        setBodyVisible(vrm.scene, !ar || wornFlag);  // AR素体待機=モデル全隠し、蒸着後=素体+鎧
        setArmorVisible(vrm.scene, wornFlag);
        if (!ar) {
          // 点群モードに戻す時は定位置へ(ARが動かした配置・向きを破棄)
          vrm.scene.position.set(0, 0, 0);
          vrm.scene.rotation.set(0, 0, 0);
          vrm.scene.scale.setScalar(1);
        }
        bones = null;
        euro = null;
        euro2d = null;
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
        const devFlag = new URLSearchParams(window.location.search).has('dev');
        const mkPose = (delegate) => vision.PoseLandmarker.createFromOptions(files, {
          baseOptions: {
            modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task',
            delegate,
          },
          runningMode: 'VIDEO', numPoses: 1,
          outputSegmentationMasks: devFlag,   // マスク合成のコストはdev(AR)時のみ負担
        });
        try { pose = await mkPose('GPU'); }
        catch { pose = await mkPose('CPU'); }  // WebGL不調端末はCPU推論で続行
        if (!video) {
          video = document.createElement('video');
          video.muted = true; video.playsInline = true;
          Object.assign(video.style, {
            position: 'absolute', inset: '0', width: '100%', height: '100%',
            objectFit: 'cover', display: 'none', zIndex: '0',
          });
          mount.insertBefore(video, renderer.domElement);
        }
        const stream = await navigator.mediaDevices.getUserMedia(
          { video: { width: 640, height: 480 }, audio: false });
        video.srcObject = stream;
        await video.play();
        run = true; bones = null; euro = null; euro2d = null;
        setRunning(true);
        apiRef.current.applyAr();
        setStatus(apiRef.current.ar
          ? '実写合成 — 素体は君自身。「蒸着!」で体に鎧が装着される'
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
        apiRef.current.applyAr();  // AR中に読み込み完了した場合の素体非表示も反映
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
      mount.removeChild(fxCan);
      if (video && video.parentNode === mount) mount.removeChild(video);
    };
  }, [code]);

  useEffect(() => { apiRef.current.mirror = mirrorMode; apiRef.current.applyAr && apiRef.current.applyAr(); }, [mirrorMode]);
  useEffect(() => { apiRef.current.ar = arMode; apiRef.current.applyAr && apiRef.current.applyAr(); }, [arMode]);
  useEffect(() => { apiRef.current.debugCanvas = (devMode && arMode) ? debugRef.current : null; }, [devMode, arMode]);
  useEffect(() => {   // 計測トグルと表示先は毎レンダ同期(条件マウントの取りこぼし防止)
    apiRef.current.dbgOpts = { skel: dbgSkel, resid: dbgResid, model: dbgModel, mask: dbgMask };
    apiRef.current.devInfo = devInfoRef.current;
  });

  return (
    <main style={{ position: 'fixed', inset: 0 }}>
      <div ref={mountRef} style={{ position: 'absolute', inset: 0 }} />
      {devMode && (
        <canvas ref={debugRef} style={{
          position: 'absolute', inset: 0, width: '100%', height: '100%',
          pointerEvents: 'none', zIndex: 3,
        }} />
      )}
      {devMode && arMode && (
        <div style={{
          position: 'absolute', top: 64, left: 18, zIndex: 7, maxWidth: 330,
          background: 'rgba(4,9,14,0.82)', border: '1px solid #24425a',
          borderRadius: 8, padding: '10px 12px', fontSize: 11, color: '#dce8f2',
        }}>
          <div style={{ color: '#d9b45f', letterSpacing: '0.25em', marginBottom: 6 }}>AR計測 / dev</div>
          <label style={{ display: 'block', cursor: 'pointer', lineHeight: 1.9 }}>
            <input type="checkbox" checked={dbgSkel} onChange={(e) => setDbgSkel(e.target.checked)} />
            {' '}骨格オーバーレイ — ①体を撮れているか(実写に乗ればOK)
          </label>
          <label style={{ display: 'block', cursor: 'pointer', lineHeight: 1.9 }}>
            <input type="checkbox" checked={dbgResid} onChange={(e) => setDbgResid(e.target.checked)} />
            {' '}モデル残差 — ②追従できているか(○が骨格に重なればOK)
          </label>
          <label style={{ display: 'block', cursor: 'pointer', lineHeight: 1.9 }}>
            <input type="checkbox" checked={dbgModel} onChange={(e) => setDbgModel(e.target.checked)} />
            {' '}モデル表示(OFFで骨格だけを検証)
          </label>
          <label style={{ display: 'block', cursor: 'pointer', lineHeight: 1.9 }}>
            <input type="checkbox" checked={dbgMask} onChange={(e) => setDbgMask(e.target.checked)} />
            {' '}実写マスク — ③蒸着後、素の自分をシルエットに沈める
          </label>
          <div ref={devInfoRef} style={{
            marginTop: 6, color: '#8fa7b8', fontFamily: 'ui-monospace, monospace',
            whiteSpace: 'pre-wrap', lineHeight: 1.7,
          }}>計測待機 — カメラを開始せよ</div>
        </div>
      )}
      {flashKey > 0 && <div key={flashKey} className="henshin-flash" />}
      <div style={{ position: 'absolute', top: 14, left: 18, textShadow: '0 1px 6px #000', zIndex: 5 }}>
        <div style={{ fontSize: 11, letterSpacing: '0.4em', color: '#5fc7e8' }}>蒸着執行録 / MIRROR</div>
        <div style={{ fontSize: 20, letterSpacing: '0.12em' }}>{code}</div>
      </div>
      <div style={{
        position: 'absolute', bottom: 18, left: 18, display: 'flex', gap: 10, zIndex: 5,
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
        {devMode && (
          <label style={{ fontSize: 12, color: '#d9b45f', cursor: 'pointer' }}>
            <input type="checkbox" checked={arMode}
              onChange={(e) => {
                setArMode(e.target.checked);
                setFlashKey((k) => k + 1);  // モード切替の瞬間を閃光で包む
              }} /> 実写に重ねる(AR/dev)
          </label>
        )}
        <canvas ref={canvasRef} width={192} height={144}
          style={{ border: '1px solid #24425a', background: '#04080d', borderRadius: 4 }} />
        <span style={{ fontSize: 12, color: '#8fa7b8', maxWidth: 380 }}>{status}</span>
      </div>
      <nav className="topnav">
        <a href="/">⌂ 扉へ</a>
        <a href={`/s/${code}`}>← 蒸着室</a>
      </nav>

      {!running && (
        <div style={{
          position: 'absolute', left: '50%', top: '50%', zIndex: 6,
          transform: 'translate(-50%, -50%)', textAlign: 'center',
          display: 'flex', flexDirection: 'column', gap: 14, alignItems: 'center',
          background: 'rgba(7,14,22,0.82)', border: '1px solid #24425a',
          borderRadius: 12, padding: '26px 30px',
        }}>
          <div style={{ fontSize: 13, color: '#8fa7b8', lineHeight: 2 }}>
            素体が待機している。カメラを開始し、<br />
            <b style={{ color: '#9fdcff' }}>「蒸着!」</b>と唱えれば君の動きと共に鎧が装着される。
          </div>
          <button className="btn-main" style={{ fontSize: 16, padding: '13px 30px' }}
            onClick={() => apiRef.current.toggle && apiRef.current.toggle()}>
            カメラを開始する
          </button>
          <div style={{ fontSize: 11, color: '#5a7284' }}>
            映像は表示・保存しません(点群のみ)
          </div>
        </div>
      )}
    </main>
  );
}
