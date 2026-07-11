'use client';
// /ar/<code> — 蒸着チャンバー(VR埋め込み体験 v2, 2026-07-11作り直し)。
// 核: 「自分の体に鎧が蒸着する」。
//  * 3点トラッキング: ヘッドセット=頭+体の向き/位置、コントローラ=両腕(Two-Bone IK)
//  * 首から上は自分には見えない(three-vrm firstPerson: 頭ウェイトでメッシュ自動分割)
//  * 正面の「鏡」には頭も含む全身が映る(全身クローンのミラー配置 — Questで軽い)
//  * 右トリガー=蒸着の儀(「蒸着!」と唱える) / 左トリガー=解除。案内は空間内パネル
// 参考: viewer/quest-iw-demo(IWSDK展示版)のトリガー→発声→照合の儀式構成
import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { VRButton } from 'three/examples/jsm/webxr/VRButton.js';
import { XRControllerModelFactory } from 'three/examples/jsm/webxr/XRControllerModelFactory.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import { VRMAnimationLoaderPlugin, createVRMAnimationClip } from '@pixiv/three-vrm-animation';
import { fetchManifest, fileUrl, setArmorVisible } from '../../../lib/suit';
import { TRIGGER_LOOSE_RE, announce, pickAudioMime, recordChunk, transcribe, sttEnabled } from '../../../lib/stt';

const MIRROR_Z = -2.1; // 鏡の位置(目の前 2.1m)
const AVATAR_EYE = 1.58; // default.vrm の目の高さ(身長キャリブレーション基準)

export default function VrChamber() {
  const { code } = useParams();
  const mountRef = useRef(null);
  const [status, setStatus] = useState('転送装置を起動中…');
  const [inVr, setInVr] = useState(false);

  useEffect(() => {
    if (!mountRef.current || !code) return;
    let disposed = false;
    const mount = mountRef.current;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.xr.enabled = true;
    renderer.localClippingEnabled = true;  // 一人称の首クリッピングに使う
    renderer.xr.addEventListener('sessionstart', () => setInVr(true));
    renderer.xr.addEventListener('sessionend', () => setInVr(false));
    mount.appendChild(renderer.domElement);

    // 一人称の見え方(T9, 2026-07-11作り替え): three-vrmのfirstPersonレイヤ方式は
    // 実機で全身不可視になった — 代わりに自分のアバターだけ「首から上」を
    // クリッピング平面で刈る。素体ごと残るので指先も見える。鏡クローンは無加工=全身
    const selfClip = new THREE.Plane(new THREE.Vector3(0, -1, 0), 999);  // y<=定数 を表示

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x9aa3ac);  // チャンバー内も明るいグレー(黒素体の視認性)
    scene.fog = new THREE.Fog(0x9aa3ac, 5, 16);
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    const camera = new THREE.PerspectiveCamera(50, mount.clientWidth / mount.clientHeight, 0.01, 60);
    camera.position.set(0, 1.5, 1.2);
    camera.lookAt(0, 1.2, MIRROR_Z);

    // --- チャンバーの空間 ---
    scene.add(new THREE.GridHelper(10, 40, 0x7b8790, 0x8d97a0));
    const key = new THREE.DirectionalLight(0xffffff, 1.1);
    key.position.set(1.5, 3, 1.5);
    scene.add(key);
    scene.add(new THREE.AmbientLight(0x88aacc, 0.45));
    // 鏡を挟む光柱
    for (const x of [-1.1, 1.1]) {
      const pillar = new THREE.Mesh(
        new THREE.CylinderGeometry(0.03, 0.03, 2.6, 8),
        new THREE.MeshBasicMaterial({ color: 0x2c8fbf }));
      pillar.position.set(x, 1.3, MIRROR_Z + 0.02);
      scene.add(pillar);
    }
    // 「鏡」= 暗いガラス面 + 発光縁(反射は全身クローンで作る)
    const glass = new THREE.Mesh(
      new THREE.PlaneGeometry(2.0, 2.5),
      new THREE.MeshStandardMaterial({
        color: 0x0a1622, metalness: 0.9, roughness: 0.25,
        transparent: true, opacity: 0.55,
      }));
    glass.position.set(0, 1.25, MIRROR_Z);
    scene.add(glass);
    // 鏡像はこのグループに入れる: 平面 z=MIRROR_Z に対する反射変換
    const mirrorGroup = new THREE.Group();
    mirrorGroup.position.z = 2 * MIRROR_Z;
    mirrorGroup.scale.z = -1;
    scene.add(mirrorGroup);

    // 蒸着の閃光(シーン内ライト — VRではDOMのフラッシュは見えない)
    const flashLight = new THREE.PointLight(0x9fdcff, 0, 8);
    flashLight.position.set(0, 1.2, -0.5);
    scene.add(flashLight);
    let flashT = -1;

    // --- 空間内の案内パネル ---
    const panelCanvas = document.createElement('canvas');
    panelCanvas.width = 768; panelCanvas.height = 384;
    const panelTex = new THREE.CanvasTexture(panelCanvas);
    const panel = new THREE.Mesh(
      new THREE.PlaneGeometry(1.15, 0.575),
      new THREE.MeshBasicMaterial({ map: panelTex, transparent: true }));
    panel.position.set(1.45, 1.35, MIRROR_Z + 0.35);
    panel.rotation.y = -0.45;
    scene.add(panel);
    const drawPanel = (title, lines, accent = '#5fc7e8') => {
      const ctx = panelCanvas.getContext('2d');
      ctx.clearRect(0, 0, 768, 384);
      ctx.fillStyle = 'rgba(5, 13, 22, 0.92)';
      ctx.fillRect(0, 0, 768, 384);
      ctx.strokeStyle = accent; ctx.lineWidth = 3;
      ctx.strokeRect(6, 6, 756, 372);
      ctx.fillStyle = accent;
      ctx.font = 'bold 44px "Hiragino Sans", "Noto Sans JP", sans-serif';
      ctx.fillText(title, 32, 76);
      ctx.fillStyle = '#dce8f2';
      ctx.font = '30px "Hiragino Sans", "Noto Sans JP", sans-serif';
      lines.forEach((l, i) => ctx.fillText(l, 32, 148 + i * 52));
      panelTex.needsUpdate = true;
    };

    // --- 状態 ---
    let vrm = null, mirrorVrm = null, vrmaData = null, mixer = null;
    let bones = null, bonePairs = [], hipsPair = null;
    let worn = false, phase = 'boot';  // boot|ready|listening|thinking|motion
    let voiceMode = false, micStream = null;
    let bodyYaw = 0, calibScale = 0;
    let particles = null, listenLeft = 0;
    const hands = { left: null, right: null };

    const updatePanel = () => {
      if (phase === 'listening') {
        drawPanel('唱えよ —「蒸着!」', [`残り ${Math.ceil(listenLeft)} 秒`, '', 'マイクが君の声を聞いている'], '#d9b45f');
      } else if (phase === 'thinking') {
        drawPanel('音声解析中…', ['Sakura Whisper 照合中', 'そのまま待て'], '#d9b45f');
      } else if (phase === 'motion') {
        drawPanel('蒸 着', ['スーツ装着シーケンス実行中'], '#7ee2a8');
      } else if (worn) {
        drawPanel('蒸着完了', ['鏡で姿を確認せよ',
          '右トリガー: 見得(モーション再演)',
          '左トリガー: 蒸着解除(素体に戻る)'], '#7ee2a8');
      } else {
        drawPanel('素体待機', [
          voiceMode ? '右トリガーを引いて「蒸着!」と唱えよ' : '右トリガーで蒸着',
          '左トリガー: (蒸着後に)解除',
          '体を動かすと鎧も動く — 鏡を見よ'], '#5fc7e8');
      }
    };

    // --- ボーン制御(トラッキングv4の移植) ---
    const grabBones = () => {
      if (!vrm) return null;
      const h = vrm.humanoid;
      const g = (n) => h.getNormalizedBoneNode(n);
      const b = {
        head: g('head'), hips: g('hips'),
        lUp: g('leftUpperArm'), lLo: g('leftLowerArm'), lHand: g('leftHand'),
        rUp: g('rightUpperArm'), rLo: g('rightLowerArm'), rHand: g('rightHand'),
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
      b.rest = { lUp: seg(b.lUp, b.lLo), lLo: seg(b.lLo, b.lHand),
                 rUp: seg(b.rUp, b.rLo), rLo: seg(b.rLo, b.rHand),
                 lUpLeg: seg(b.lUpLeg, b.lLoLeg), lLoLeg: seg(b.lLoLeg, b.lFoot),
                 rUpLeg: seg(b.rUpLeg, b.rLoLeg), rLoLeg: seg(b.rLoLeg, b.rFoot) };
      b.len = { lUp: len(b.lUp, b.lLo), lLo: len(b.lLo, b.lHand),
                rUp: len(b.rUp, b.rLo), rLo: len(b.rLo, b.rHand),
                lUpLeg: len(b.lUpLeg, b.lLoLeg), lLoLeg: len(b.lLoLeg, b.lFoot),
                rUpLeg: len(b.rUpLeg, b.rLoLeg), rLoLeg: len(b.rLoLeg, b.rFoot) };
      // しゃがみ追従の基準: バインド時の腰高さと、足のルート相対位置(足はここに残す)
      if (b.hips) b.hips.userData.bindY = b.hips.position.y;
      const inv = vrm.scene.matrixWorld.clone().invert();
      b.footLocal = {
        l: b.lFoot ? wp(b.lFoot).applyMatrix4(inv) : null,
        r: b.rFoot ? wp(b.rFoot).applyMatrix4(inv) : null,
      };
      return b;
    };
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
    // 汎用 Two-Bone IK(腕=肘は下向きポール、脚=膝は前向きポール)
    const solveArmWorld = (up, lo, rest, lenUp, lenLo, T, s, poleHint) => {
      if (!up || !lo || !rest || !(lenUp > 1e-4) || !(lenLo > 1e-4)) return;
      const S = up.getWorldPosition(new THREE.Vector3());
      const d = THREE.MathUtils.clamp(S.distanceTo(T),
        Math.abs(lenUp - lenLo) + 1e-3, lenUp + lenLo - 1e-3);
      const n = T.clone().sub(S).normalize();
      let pole = poleHint ? poleHint.clone() : new THREE.Vector3(0, -1, 0);
      pole.sub(n.clone().multiplyScalar(pole.dot(n)));
      if (pole.lengthSq() < 1e-6) pole.set(0, 0, -1);
      pole.normalize();
      const cosA = THREE.MathUtils.clamp(
        (lenUp * lenUp + d * d - lenLo * lenLo) / (2 * lenUp * d), -1, 1);
      const sinA = Math.sqrt(1 - cosA * cosA);
      const E = S.clone().add(n.clone().multiplyScalar(lenUp * cosA))
        .add(pole.clone().multiplyScalar(lenUp * sinA));
      driveDir(up, rest.up, E.clone().sub(S), s);
      driveDir(lo, rest.lo, T.clone().sub(E), s);
    };

    // 鏡像クローンへ骨姿勢を毎フレーム転写
    const buildPairs = () => {
      bonePairs = [];
      const names = ['hips', 'spine', 'chest', 'upperChest', 'neck', 'head',
        'leftShoulder', 'leftUpperArm', 'leftLowerArm', 'leftHand',
        'rightShoulder', 'rightUpperArm', 'rightLowerArm', 'rightHand',
        'leftUpperLeg', 'leftLowerLeg', 'leftFoot',
        'rightUpperLeg', 'rightLowerLeg', 'rightFoot'];
      for (const n of names) {
        const a = vrm.humanoid.getNormalizedBoneNode(n);
        const b = mirrorVrm.humanoid.getNormalizedBoneNode(n);
        if (a && b) bonePairs.push([a, b]);
        if (n === 'hips' && a && b) hipsPair = [a, b];
      }
    };
    const syncMirror = () => {
      if (!vrm || !mirrorVrm) return;
      mirrorVrm.scene.position.copy(vrm.scene.position);
      mirrorVrm.scene.rotation.copy(vrm.scene.rotation);
      mirrorVrm.scene.scale.copy(vrm.scene.scale);
      for (const [a, b] of bonePairs) b.quaternion.copy(a.quaternion);
      if (hipsPair) hipsPair[1].position.copy(hipsPair[0].position);
    };

    const burst = () => {
      const N = 1800;
      const pos = new Float32Array(N * 3);
      const base = vrm ? vrm.scene.position : new THREE.Vector3();
      for (let i = 0; i < N; i++) {
        const r = 0.8 + Math.random() * 1.5, a = Math.random() * 6.283;
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
    };

    const henshin = () => {
      if (!vrm || phase === 'motion') return;
      phase = 'motion';
      try { new Audio('/se/henshin.mp3').play().catch(() => {}); } catch {}
      setArmorVisible(vrm.scene, true);
      if (mirrorVrm) setArmorVisible(mirrorVrm.scene, true);
      flashT = 0;
      burst();
      updatePanel();
      const finish = () => {
        phase = 'ready';
        worn = true;
        bones = null;  // 追跡再開時に姿勢を実測し直す
        announce('蒸着、完了。');
        updatePanel();
      };
      if (vrmaData) {
        const clip = createVRMAnimationClip(vrmaData, vrm);
        mixer = new THREE.AnimationMixer(vrm.scene);
        const action = mixer.clipAction(clip);
        action.setLoop(THREE.LoopOnce);
        action.clampWhenFinished = true;
        mixer.addEventListener('finished', () => { mixer.stopAllAction(); mixer = null; finish(); });
        action.play();
      } else {
        setTimeout(finish, 2400);
      }
    };
    const release = () => {
      if (!vrm || phase === 'motion' || !worn) return;
      setArmorVisible(vrm.scene, false);
      if (mirrorVrm) setArmorVisible(mirrorVrm.scene, false);
      worn = false;
      flashT = 0;
      announce('蒸着解除。');
      updatePanel();
    };

    // 蒸着の儀: 右トリガー → 3秒唱える → 照合 → 蒸着。
    // 「必ず唱えさせる」が原則(2026-07-11 T4/T6)。マイク取得はトリガーの
    // 瞬間に行う — ページ読込時の要求はQuestが無言拒否する(音声なしモード化の真因)。
    // 音声系がどうしても使えない時だけ「もう一度トリガーで強行」の明示2段階
    let overrideArm = false;
    const ritual = async () => {
      if (phase !== 'ready') return;
      if (worn) { henshin(); return; }   // 装着中の右トリガー=見得の再演
      if (!voiceMode) { henshin(); return; }  // STT未設定の環境のみ直行
      if (overrideArm) { overrideArm = false; henshin(); return; }
      if (!micStream) {
        try {
          micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch {
          overrideArm = true;
          drawPanel('マイクが使えない', ['Quest設定のマイク許可を確認せよ',
            'それでも蒸着するなら もう一度トリガー'], '#ff9a8a');
          return;
        }
      }
      phase = 'listening';
      listenLeft = 3;
      updatePanel();
      try {
        const blob = await recordChunk(micStream, 3000, pickAudioMime());
        phase = 'thinking';
        updatePanel();
        const text = await transcribe(blob);
        // VRは押して唱える方式なので外れ値許容(それっぽければ通す)
        if (TRIGGER_LOOSE_RE.test(text)) {
          announce('音声認証、成立。');
          phase = 'ready';
          henshin();
        } else {
          phase = 'ready';
          drawPanel('合言葉 未検出', [`「${(text || '…').slice(0, 14)}」`,
            'もう一度右トリガーで唱え直せ'], '#ff9a8a');
          setTimeout(updatePanel, 2600);
        }
      } catch {
        phase = 'ready';
        overrideArm = true;  // 恒久降格はしない — 次回も儀式から
        drawPanel('音声解析に失敗', ['もう一度トリガーで唱え直すか',
          '続けて2度引きで強行蒸着'], '#ff9a8a');
        setTimeout(updatePanel, 2600);
      }
    };

    // コントローラ(handednessは connected イベントで判明)。
    // 実機モデルを表示し、手元からレイを出す — 「トリガーがそこにある」ことが
    // 見えるだけで操作の迷いが消える
    const cmf = new XRControllerModelFactory();
    const rayGeo = new THREE.BufferGeometry().setFromPoints(
      [new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, -1)]);
    for (const i of [0, 1]) {
      const c = renderer.xr.getController(i);
      const ray = new THREE.Line(rayGeo, new THREE.LineBasicMaterial({
        color: 0x5fc7e8, transparent: true, opacity: 0.5,
      }));
      ray.scale.z = 1.6;
      c.add(ray);
      c.addEventListener('connected', (e) => {
        c.userData.hand = e.data && e.data.handedness;
        if (c.userData.hand === 'left') hands.left = c;
        if (c.userData.hand === 'right') hands.right = c;
        // 左=解除(赤系) / 右=蒸着(シアン)でレイを色分け
        ray.material.color.set(c.userData.hand === 'left' ? 0xd97a5f : 0x5fc7e8);
      });
      c.addEventListener('select', () => {
        if (c.userData.hand === 'left') release();
        else ritual();
      });
      scene.add(c);
      const grip = renderer.xr.getControllerGrip(i);
      grip.add(cmf.createControllerModel(grip));
      scene.add(grip);
    }

    const clock = new THREE.Clock();
    const camPos = new THREE.Vector3();
    const camEuler = new THREE.Euler(0, 0, 0, 'YXZ');
    const wrapPi = (a) => Math.atan2(Math.sin(a), Math.cos(a));
    renderer.setAnimationLoop((_time, frame) => {
      if (disposed) return;
      const dt = clock.getDelta();
      if (mixer) mixer.update(dt);
      if (flashT >= 0) {
        flashT += dt;
        flashLight.intensity = Math.max(0, 26 * (1 - flashT / 0.8));
        if (flashT > 0.8) flashT = -1;
      }
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
      if (phase === 'listening' && listenLeft > 0) {
        listenLeft = Math.max(0, listenLeft - dt);
        updatePanel();
      }

      const presenting = renderer.xr.isPresenting;
      const xrCam = renderer.xr.getCamera();
      // 一人称の首クリッピング: VR中だけ、頭のすぐ下から上を刈る。
      // 非VRのプレビューでは無効(999 = 全身表示)
      if (presenting && bones && bones.head) {
        const hy = bones.head.getWorldPosition(new THREE.Vector3()).y;
        selfClip.constant = hy - 0.04;
      } else {
        selfClip.constant = 999;
      }

      // --- 体の埋め込み(3点トラッキング) ---
      if (presenting && vrm && phase !== 'motion') {
        if (!bones) bones = grabBones();
        xrCam.getWorldPosition(camPos);
        camEuler.setFromQuaternion(xrCam.quaternion, 'YXZ');
        // 身長キャリブレーション(入場後、最初に頭の高さが取れた時に1回)
        if (!calibScale && camPos.y > 0.6) {
          calibScale = THREE.MathUtils.clamp(camPos.y / AVATAR_EYE, 0.75, 1.35);
          vrm.scene.scale.setScalar(calibScale);
          bones = null;  // 骨長が変わったので実測し直す
          updatePanel();
          return;
        }
        // 体の向きは頭の向きへゆっくり追従(首だけ振った時に体が回らない)
        bodyYaw += wrapPi(camEuler.y - bodyYaw) * Math.min(1, dt * 4);
        vrm.scene.rotation.y = bodyYaw;
        vrm.scene.position.set(camPos.x, 0, camPos.z);
        vrm.scene.updateMatrixWorld(true);
        if (bones) {
          // 頭: ヘッドセットの向き(体の向きとの差分)
          if (bones.head) {
            const qh = new THREE.Quaternion().setFromEuler(new THREE.Euler(
              THREE.MathUtils.clamp(camEuler.x, -0.7, 0.7),
              wrapPi(camEuler.y - bodyYaw),
              THREE.MathUtils.clamp(camEuler.z, -0.5, 0.5), 'YXZ'));
            worldToLocal(bones.head, qh.multiply(bones.head.userData.bindWorldQ), 0.6);
          }
          // 腕: コントローラ位置へ Two-Bone IK
          const t = new THREE.Vector3();
          if (hands.left) {
            hands.left.getWorldPosition(t);
            solveArmWorld(bones.lUp, bones.lLo,
              { up: bones.rest.lUp, lo: bones.rest.lLo },
              bones.len.lUp, bones.len.lLo, t.clone(), 0.6);
          }
          if (hands.right) {
            hands.right.getWorldPosition(t);
            solveArmWorld(bones.rUp, bones.rLo,
              { up: bones.rest.rUp, lo: bones.rest.rLo },
              bones.len.rUp, bones.len.rLo, t.clone(), 0.6);
          }
          // 下半身(T8): WebXR Body Tracking(Quest実験API)があれば実関節、
          // 無ければ手続き式(しゃがみ追従+膝IK)
          let bodyApi = false;
          if (frame && frame.body) {
            try {
              const ref = renderer.xr.getReferenceSpace();
              const jp = (n) => {
                const sp = frame.body.get(n);
                const pose = sp && frame.getPose(sp, ref);
                return pose ? new THREE.Vector3(
                  pose.transform.position.x, pose.transform.position.y,
                  pose.transform.position.z) : null;
              };
              const hp = jp('hips');
              const fwd = new THREE.Vector3(Math.sin(bodyYaw), 0, Math.cos(bodyYaw));
              if (hp && bones.hips && calibScale) {
                bones.hips.position.y = THREE.MathUtils.clamp(
                  hp.y / calibScale, bones.hips.userData.bindY - 0.6,
                  bones.hips.userData.bindY + 0.15);
                vrm.scene.updateMatrixWorld(true);
                bodyApi = true;
              }
              for (const [side, joint] of [['l', 'left-foot'], ['r', 'right-foot']]) {
                const fp = jp(joint);
                if (!fp) continue;
                solveArmWorld(bones[`${side}UpLeg`], bones[`${side}LoLeg`],
                  { up: bones.rest[`${side}UpLeg`], lo: bones.rest[`${side}LoLeg`] },
                  bones.len[`${side}UpLeg`], bones.len[`${side}LoLeg`],
                  fp, 0.6, fwd);
                bodyApi = true;
              }
            } catch { bodyApi = false; }
          }
          // 下半身 v1(手続き式): しゃがみ追従 — 腰が頭の高さに連動して沈み、
          // 足はバインド時の場所(ルート相対)に残して膝二骨IKで曲げる
          if (!bodyApi && bones.hips && calibScale) {
            const eye = AVATAR_EYE * calibScale;
            const crouch = THREE.MathUtils.clamp(camPos.y - eye, -0.55, 0.1);
            bones.hips.position.y = bones.hips.userData.bindY + crouch / calibScale;
            vrm.scene.updateMatrixWorld(true);
            const fwd = new THREE.Vector3(Math.sin(bodyYaw), 0, Math.cos(bodyYaw));
            for (const side of ['l', 'r']) {
              const fl = bones.footLocal[side];
              if (!fl) continue;
              const target = fl.clone().applyMatrix4(vrm.scene.matrixWorld);
              solveArmWorld(bones[`${side}UpLeg`], bones[`${side}LoLeg`],
                { up: bones.rest[`${side}UpLeg`], lo: bones.rest[`${side}LoLeg`] },
                bones.len[`${side}UpLeg`], bones.len[`${side}LoLeg`],
                target, 0.6, fwd);   // 膝は体の前へ折れる
            }
          }
        }
      }

      syncMirror();
      if (vrm) vrm.update(dt);
      if (mirrorVrm) mirrorVrm.update(dt);
      renderer.render(scene, camera);
    });

    (async () => {
      try {
        const m = await fetchManifest(code);
        if (disposed) return;
        if (!m.files.vrm) { setStatus('このパッケージにはVRMがありません'); return; }
        setStatus('鎧データを転送中…');
        const mkLoader = () => {
          const l = new GLTFLoader();
          l.register((p) => new VRMLoaderPlugin(p));
          l.register((p) => new VRMAnimationLoaderPlugin(p));
          return l;
        };
        const url = fileUrl(code, m.files.vrm);
        const g1 = await mkLoader().loadAsync(url);
        vrm = g1.userData.vrm;
        VRMUtils.rotateVRM0(vrm);
        scene.add(vrm.scene);
        setArmorVisible(vrm.scene, false);
        // 自分のアバターの全マテリアルに首クリッピングを適用(鏡クローンは対象外)
        vrm.scene.traverse((o) => {
          if (o.isMesh && o.material) {
            (Array.isArray(o.material) ? o.material : [o.material])
              .forEach((mat) => { mat.clippingPlanes = [selfClip]; });
          }
        });
        // 鏡像クローン(2体目のロード — キャッシュ済みなので軽い)
        const g2 = await mkLoader().loadAsync(url);
        mirrorVrm = g2.userData.vrm;
        VRMUtils.rotateVRM0(mirrorVrm);
        mirrorVrm.scene.traverse((o) => {
          if (o.isMesh && o.material) {
            (Array.isArray(o.material) ? o.material : [o.material])
              .forEach((mat) => { mat.side = THREE.DoubleSide; });  // scale.z=-1 対策
          }
        });
        mirrorGroup.add(mirrorVrm.scene);
        setArmorVisible(mirrorVrm.scene, false);
        buildPairs();
        if (m.files.vrma) {
          try {
            const ag = await mkLoader().loadAsync(fileUrl(code, m.files.vrma));
            vrmaData = (ag.userData.vrmAnimations || [])[0] || null;
          } catch { vrmaData = null; }
        }
        // 音声認証の可否だけ確認(マイク取得はしない — トリガーの瞬間に行う。
        // ページ読込時のgetUserMediaはQuestが無言拒否し「音声なしモード」化していた)
        voiceMode = (await sttEnabled()) && !!pickAudioMime();

        const xr = navigator.xr;
        const vrOK = xr && await xr.isSessionSupported('immersive-vr').catch(() => false);
        if (vrOK) {
          // body-tracking はQuestの実験的WebXR機能 — あれば下半身を実関節で駆動
          document.body.appendChild(VRButton.createButton(renderer, {
            optionalFeatures: ['body-tracking'],
          }));
          setStatus('READY — 「ENTER VR」で蒸着チャンバーへ');
        } else {
          setStatus('この端末はWebXR(VR)非対応です。Quest Browserで開いてください');
        }
        phase = 'ready';
        updatePanel();
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
      document.querySelectorAll('#VRButton, #ARButton').forEach((b) => b.remove());
    };
  }, [code]);

  return (
    <main style={{ position: 'fixed', inset: 0 }}>
      <div ref={mountRef} style={{ position: 'absolute', inset: 0 }} />

      {!inVr && (
        <>
          <div style={{ position: 'absolute', top: 14, left: 18, textShadow: '0 1px 6px #000' }}>
            <div style={{ fontSize: 11, letterSpacing: '0.4em', color: '#5fc7e8' }}>蒸着執行録 / VR</div>
            <div style={{ fontSize: 20, letterSpacing: '0.12em' }}>{code}</div>
          </div>
          <nav className="topnav">
            <a href="/">⌂ 扉へ</a>
            <a href={`/s/${code}`}>← 蒸着室</a>
          </nav>

          {/* チャンバー入口(DOMはVR外の窓口 — VR内の案内は空間パネルが担う) */}
          <section className="rise" style={{
            position: 'absolute', left: '50%', top: '46%',
            transform: 'translate(-50%, -50%)',
            width: 'min(460px, 92vw)', border: '1px solid #24425a', borderRadius: 12,
            padding: '24px 22px', background: 'rgba(7,14,22,0.9)',
            display: 'flex', flexDirection: 'column', gap: 16,
          }}>
            <div>
              <div style={{ fontSize: 11, letterSpacing: '0.45em', color: '#5fc7e8' }}>CHAMBER GATE</div>
              <h1 style={{ fontSize: 22, margin: '6px 0 0', letterSpacing: '0.14em' }}>蒸着チャンバー 入場手順</h1>
            </div>
            <div className="entry-steps">
              <div className="st"><span className="n">1</span>
                <span className="t">Quest の Browser でこのページを開く
                  <small>PCブラウザでは空間の下見のみ(VR入場はQuest)</small></span></div>
              <div className="st"><span className="n">2</span>
                <span className="t">初回トリガー時にマイクを許可する
                  <small>蒸着の儀は音声認証 — 君の「蒸着!」が鍵になる</small></span></div>
              <div className="st"><span className="n">3</span>
                <span className="t">下の ENTER VR で入場
                  <small>鎧は君の体に重なる。身長は自動調整</small></span></div>
              <div className="st"><span className="n">4</span>
                <span className="t">右トリガー → 「蒸着!」と唱える
                  <small>正面の鏡に全身が映る(自分の視界に兜は出ない)/ 左トリガーで解除</small></span></div>
            </div>
            <div style={{
              fontSize: 12, color: status.includes('READY') ? '#7ee2a8' : '#8fa7b8',
              letterSpacing: '0.08em', borderTop: '1px solid #16283a', paddingTop: 12,
            }}>
              {status}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
