import * as THREE from "../body-fit/vendor/three/build/three.module.js";
import { OrbitControls } from "../body-fit/vendor/three/examples/jsm/controls/OrbitControls.js";

const UI = {
  suitPath: document.getElementById("suitPath"),
  fallbackDir: document.getElementById("fallbackDir"),
  textureMode: document.getElementById("textureMode"),
  simPath: document.getElementById("simPath"),
  preferFallback: document.getElementById("preferFallback"),
  updateSuitspec: document.getElementById("updateSuitspec"),
  partChecks: document.getElementById("partChecks"),
  reliefSlider: document.getElementById("reliefSlider"),
  status: document.getElementById("status"),
  cards: document.getElementById("cards"),
  btnRefreshSuits: document.getElementById("btnRefreshSuits"),
  btnLoadSuit: document.getElementById("btnLoadSuit"),
  btnGenerate: document.getElementById("btnGenerate"),
  btnOpenBodyFit: document.getElementById("btnOpenBodyFit"),
  tabButtons: Array.from(document.querySelectorAll(".tab-btn")),
  panelParts: document.getElementById("panelParts"),
  panelBody: document.getElementById("panelBody"),
  bodyFrontCanvas: document.getElementById("bodyFrontCanvas"),
  bodyFrontMeta: document.getElementById("bodyFrontMeta"),
};

const textureLoader = new THREE.TextureLoader();
const meshGeometryCache = new Map();

const previewCards = [];
let currentSuitPath = "";
let currentSuit = null;

const BODY_FRONT_LAYOUT = {
  helmet: { pos: [0.0, 1.30, 0.08], scale: [0.66, 0.66, 0.66] },
  chest: { pos: [0.0, 0.72, 0.14], scale: [1.18, 1.22, 1.08] },
  back: { pos: [0.0, 0.72, -0.14], scale: [1.08, 1.18, 1.05] },
  waist: { pos: [0.0, 0.22, 0.06], scale: [1.0, 1.02, 1.02] },
  left_shoulder: { pos: [-0.55, 0.98, 0.02], scale: [0.68, 0.68, 0.68] },
  right_shoulder: { pos: [0.55, 0.98, 0.02], scale: [0.68, 0.68, 0.68] },
  left_upperarm: { pos: [-0.72, 0.66, 0.01], scale: [0.78, 0.96, 0.78] },
  right_upperarm: { pos: [0.72, 0.66, 0.01], scale: [0.78, 0.96, 0.78] },
  left_forearm: { pos: [-0.76, 0.22, 0.03], scale: [0.80, 1.02, 0.80] },
  right_forearm: { pos: [0.76, 0.22, 0.03], scale: [0.80, 1.02, 0.80] },
  left_hand: { pos: [-0.78, -0.24, 0.08], scale: [0.74, 0.74, 0.74] },
  right_hand: { pos: [0.78, -0.24, 0.08], scale: [0.74, 0.74, 0.74] },
  left_thigh: { pos: [-0.28, -0.42, 0.03], scale: [0.90, 1.18, 0.90] },
  right_thigh: { pos: [0.28, -0.42, 0.03], scale: [0.90, 1.18, 0.90] },
  left_shin: { pos: [-0.28, -1.02, 0.05], scale: [0.88, 1.20, 0.88] },
  right_shin: { pos: [0.28, -1.02, 0.05], scale: [0.88, 1.20, 0.88] },
  left_boot: { pos: [-0.28, -1.62, 0.20], scale: [0.92, 0.95, 1.18] },
  right_boot: { pos: [0.28, -1.62, 0.20], scale: [0.92, 0.95, 1.18] },
};

function setStatus(text, isError = false) {
  UI.status.textContent = text;
  UI.status.style.color = isError ? "#9c1b2f" : "#17335f";
}

function normPath(path) {
  let p = String(path || "").replace(/\\/g, "/").trim();
  if (!p) return p;
  if (/^https?:\/\//i.test(p)) return p;
  if (p.startsWith("/")) return p;
  if (p.startsWith("./")) p = p.slice(2);
  return `/${p}`;
}

function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
}

function readEnabledModules(suitspec) {
  const modules = suitspec?.modules || {};
  return Object.entries(modules).filter(([, mod]) => mod && mod.enabled);
}

function resolveMeshAssetPath(partName, module) {
  const ref = String(module?.asset_ref || "").replace(/\\/g, "/").trim();
  if (ref.toLowerCase().endsWith(".mesh.json")) return ref;
  return `viewer/assets/meshes/${partName}.mesh.json`;
}

function meshGeometryFromPayload(payload) {
  if (!payload || payload.format !== "mesh.v1") {
    throw new Error("Unsupported mesh format.");
  }
  const positions = new Float32Array(payload.positions || []);
  const normals = new Float32Array(payload.normals || []);
  const uv = new Float32Array(payload.uv || []);
  const indices = Array.isArray(payload.indices) ? payload.indices : [];

  if (positions.length < 9 || positions.length % 3 !== 0) {
    throw new Error("Invalid mesh positions.");
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  if (uv.length === (positions.length / 3) * 2) {
    geometry.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  }
  if (normals.length === positions.length) {
    geometry.setAttribute("normal", new THREE.BufferAttribute(normals, 3));
  }
  if (indices.length > 0) {
    geometry.setIndex(indices);
  }
  if (geometry.index) {
    const expanded = geometry.toNonIndexed();
    expanded.computeVertexNormals();
    return expanded;
  }
  if (!geometry.getAttribute("normal")) {
    geometry.computeVertexNormals();
  }
  return geometry;
}

async function loadMeshGeometryFromAsset(assetPath) {
  const key = normPath(assetPath);
  if (meshGeometryCache.has(key)) {
    return meshGeometryCache.get(key).clone();
  }
  const res = await fetch(key);
  if (!res.ok) {
    throw new Error(`mesh load failed: ${key} (${res.status})`);
  }
  const payload = await res.json();
  const geometry = meshGeometryFromPayload(payload);
  meshGeometryCache.set(key, geometry);
  return geometry.clone();
}

function restoreBase(mesh) {
  const pos = mesh.geometry.attributes.position;
  const base = mesh.userData.basePositions;
  if (!pos || !base || base.length !== pos.array.length) return;
  for (let i = 0; i < pos.count; i++) {
    pos.setXYZ(i, base[i * 3], base[i * 3 + 1], base[i * 3 + 2]);
  }
  pos.needsUpdate = true;
  mesh.geometry.computeVertexNormals();
}

function applyRelief(mesh, texture, amplitude) {
  const image = texture?.image;
  if (!image || amplitude <= 0) {
    restoreBase(mesh);
    return;
  }

  const geo = mesh.geometry;
  const pos = geo.attributes.position;
  const norm = geo.attributes.normal;
  const uv = geo.attributes.uv;
  const base = mesh.userData.basePositions;
  if (!pos || !norm || !uv || !base || base.length !== pos.array.length) return;

  const size = 256;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.drawImage(image, 0, 0, size, size);
  const data = ctx.getImageData(0, 0, size, size).data;

  for (let i = 0; i < pos.count; i++) {
    const u = clamp(uv.getX(i), 0, 1);
    const v = clamp(uv.getY(i), 0, 1);
    const x = Math.floor(u * (size - 1));
    const y = Math.floor((1 - v) * (size - 1));
    const idx = (y * size + x) * 4;

    const r = data[idx + 0];
    const g = data[idx + 1];
    const b = data[idx + 2];

    const lum = (r + g + b) / (3 * 255);
    const minCh = Math.min(r, g, b) / 255;
    const maxCh = Math.max(r, g, b) / 255;
    const satLike = maxCh - minCh;
    const mask = clamp((0.95 - minCh) * 8 + satLike * 2, 0, 1);
    const disp = (lum - 0.5) * amplitude * mask;

    const nx = norm.getX(i);
    const ny = norm.getY(i);
    const nz = norm.getZ(i);
    const invLen = 1 / (Math.hypot(nx, ny, nz) || 1);

    pos.setXYZ(
      i,
      base[i * 3] + nx * invLen * disp,
      base[i * 3 + 1] + ny * invLen * disp,
      base[i * 3 + 2] + nz * invLen * disp
    );
  }
  pos.needsUpdate = true;
  geo.computeVertexNormals();
}

function loadTexture(path) {
  if (!path) return Promise.resolve(null);
  return new Promise((resolve) => {
    textureLoader.load(
      normPath(path),
      (tex) => {
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.wrapS = THREE.RepeatWrapping;
        tex.wrapT = THREE.RepeatWrapping;
        tex.anisotropy = 4;
        resolve(tex);
      },
      undefined,
      () => resolve(null)
    );
  });
}

function fitCameraToObject(camera, controls, object3d, distanceFactor = 2.35) {
  const box = new THREE.Box3().setFromObject(object3d);
  if (box.isEmpty()) return;
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  const radius = Math.max(sphere.radius, 0.05);
  const fov = (camera.fov * Math.PI) / 180;
  const distance = (radius / Math.sin(fov / 2)) * distanceFactor;
  camera.position.set(sphere.center.x, sphere.center.y + radius * 0.15, sphere.center.z + distance);
  controls.target.copy(sphere.center);
  controls.update();
}

function prepareCanvas(canvas) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = Math.max(2, Math.floor((canvas.clientWidth || 320) * dpr));
  const h = Math.max(2, Math.floor((canvas.clientHeight || 210) * dpr));
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }
  return { w, h };
}

function computeUvAreaRatio(geometry) {
  const uv = geometry?.getAttribute("uv");
  if (!uv || uv.count < 3) return 0;

  let area = 0;
  if (geometry.index) {
    const idx = geometry.index.array;
    for (let i = 0; i < idx.length; i += 3) {
      const a = idx[i];
      const b = idx[i + 1];
      const c = idx[i + 2];
      const ax = uv.getX(a);
      const ay = uv.getY(a);
      const bx = uv.getX(b);
      const by = uv.getY(b);
      const cx = uv.getX(c);
      const cy = uv.getY(c);
      area += Math.abs((ax * (by - cy) + bx * (cy - ay) + cx * (ay - by)) * 0.5);
    }
  } else {
    for (let i = 0; i < uv.count; i += 3) {
      const ax = uv.getX(i);
      const ay = uv.getY(i);
      const bx = uv.getX(i + 1);
      const by = uv.getY(i + 1);
      const cx = uv.getX(i + 2);
      const cy = uv.getY(i + 2);
      area += Math.abs((ax * (by - cy) + bx * (cy - ay) + cx * (ay - by)) * 0.5);
    }
  }
  return clamp(area, 0, 1);
}

function analyzeTextureCoverage(image) {
  if (!image) {
    return { fillRatio: 0, borderFillRatio: 0 };
  }

  const size = 256;
  const edge = Math.max(2, Math.floor(size * 0.04));
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) return { fillRatio: 0, borderFillRatio: 0 };

  ctx.drawImage(image, 0, 0, size, size);
  const data = ctx.getImageData(0, 0, size, size).data;

  let ink = 0;
  let borderInk = 0;
  let borderTotal = 0;

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;
      const r = data[i + 0];
      const g = data[i + 1];
      const b = data[i + 2];
      const lum = (r + g + b) / 3;
      const sat = Math.max(r, g, b) - Math.min(r, g, b);
      const isInk = lum < 245 || sat > 22;
      if (isInk) ink += 1;

      const isBorder = x < edge || x >= size - edge || y < edge || y >= size - edge;
      if (isBorder) {
        borderTotal += 1;
        if (isInk) borderInk += 1;
      }
    }
  }

  const total = size * size;
  return {
    fillRatio: ink / total,
    borderFillRatio: borderTotal ? borderInk / borderTotal : 0,
  };
}

function drawUvWire(ctx, geometry, width, height) {
  const uv = geometry?.getAttribute("uv");
  if (!uv || uv.count < 3) return;

  ctx.strokeStyle = "rgba(14, 52, 112, 0.72)";
  ctx.lineWidth = 1;

  const drawTri = (a, b, c) => {
    const ax = uv.getX(a) * width;
    const ay = (1 - uv.getY(a)) * height;
    const bx = uv.getX(b) * width;
    const by = (1 - uv.getY(b)) * height;
    const cx = uv.getX(c) * width;
    const cy = (1 - uv.getY(c)) * height;

    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(bx, by);
    ctx.lineTo(cx, cy);
    ctx.closePath();
    ctx.stroke();
  };

  if (geometry.index) {
    const idx = geometry.index.array;
    for (let i = 0; i < idx.length; i += 3) {
      drawTri(idx[i], idx[i + 1], idx[i + 2]);
    }
  } else {
    for (let i = 0; i < uv.count; i += 3) {
      drawTri(i, i + 1, i + 2);
    }
  }
}

class PartCardPreview {
  constructor({ meshCanvas, uvCanvas, statsNode, partName, module }) {
    this.meshCanvas = meshCanvas;
    this.uvCanvas = uvCanvas;
    this.statsNode = statsNode;
    this.partName = partName;
    this.module = module || {};
    this.texturePath = this.module.texture_path || null;
    this.assetPath = resolveMeshAssetPath(this.partName, this.module);
    this.texture = null;
    this.textureImage = null;

    this.renderer = new THREE.WebGLRenderer({ canvas: meshCanvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xffffff);

    this.camera = new THREE.PerspectiveCamera(44, 1, 0.01, 50);
    this.camera.position.set(0, 0.2, 2.2);

    this.controls = new OrbitControls(this.camera, meshCanvas);
    this.controls.enablePan = false;
    this.controls.enableDamping = true;
    this.controls.autoRotate = true;
    this.controls.autoRotateSpeed = 1.5;
    this.controls.target.set(0, 0, 0);

    this.scene.add(new THREE.AmbientLight(0xffffff, 0.78));
    const dir = new THREE.DirectionalLight(0xffffff, 0.86);
    dir.position.set(1.2, 1.8, 1.4);
    this.scene.add(dir);

    const geometry = new THREE.SphereGeometry(0.5, 24, 16).toNonIndexed();
    const material = new THREE.MeshStandardMaterial({
      color: 0xe6eefb,
      metalness: 0.68,
      roughness: 0.3,
    });

    this.mesh = new THREE.Mesh(geometry, material);
    this.mesh.userData.basePositions = new Float32Array(geometry.attributes.position.array);
    this.scene.add(this.mesh);

    this.tick = this.tick.bind(this);
    requestAnimationFrame(this.tick);

    this.loadAssetGeometry().then(() => this.updateUvDebug());
    this.loadTextureAndRelief(Number(UI.reliefSlider.value || "0.05"));
  }

  async loadAssetGeometry() {
    try {
      const geometry = await loadMeshGeometryFromAsset(this.assetPath);
      this.mesh.geometry.dispose();
      this.mesh.geometry = geometry;
      this.mesh.userData.basePositions = new Float32Array(geometry.attributes.position.array);
      fitCameraToObject(this.camera, this.controls, this.mesh, 2.15);
    } catch (error) {
      console.warn(`asset mesh fallback for ${this.partName}`, error);
    }
  }

  async loadTextureAndRelief(amplitude) {
    if (!this.texturePath) {
      restoreBase(this.mesh);
      this.mesh.material.map = null;
      this.mesh.material.color.setHex(0xdfe8f8);
      this.mesh.material.needsUpdate = true;
      this.texture = null;
      this.textureImage = null;
      this.updateUvDebug();
      return;
    }

    const tex = await loadTexture(this.texturePath);
    this.texture = tex;
    this.textureImage = tex?.image || null;

    if (tex) {
      this.mesh.material.map = tex;
      this.mesh.material.color.setHex(0xffffff);
      this.mesh.material.needsUpdate = true;
      applyRelief(this.mesh, tex, amplitude);
    } else {
      this.mesh.material.map = null;
      this.mesh.material.color.setHex(0xdfe8f8);
      this.mesh.material.needsUpdate = true;
      restoreBase(this.mesh);
    }

    this.updateUvDebug();
  }

  updateRelief(amplitude) {
    applyRelief(this.mesh, this.texture, amplitude);
  }

  updateUvDebug() {
    const { w, h } = prepareCanvas(this.uvCanvas);
    const ctx = this.uvCanvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, w, h);

    if (this.textureImage) {
      ctx.drawImage(this.textureImage, 0, 0, w, h);
    } else {
      ctx.fillStyle = "#f5f8ff";
      for (let y = 0; y < h; y += 24) {
        for (let x = 0; x < w; x += 24) {
          if (((x + y) / 24) % 2 === 0) {
            ctx.fillRect(x, y, 24, 24);
          }
        }
      }
    }

    drawUvWire(ctx, this.mesh.geometry, w, h);

    const uvAreaRatio = computeUvAreaRatio(this.mesh.geometry);
    const coverage = analyzeTextureCoverage(this.textureImage);
    const fitScore = clamp(1 - Math.abs(coverage.fillRatio - uvAreaRatio), 0, 1);

    const text = [
      `UV占有: ${(uvAreaRatio * 100).toFixed(1)}%`,
      `テクスチャ充填: ${(coverage.fillRatio * 100).toFixed(1)}%`,
      `外周充填: ${(coverage.borderFillRatio * 100).toFixed(1)}%`,
      `一致度: ${(fitScore * 100).toFixed(1)}%`,
    ].join(" | ");

    this.statsNode.textContent = text;
    this.statsNode.style.color = fitScore < 0.7 ? "#9c1b2f" : "#35567f";
  }

  tick() {
    const w = this.meshCanvas.clientWidth || 320;
    const h = this.meshCanvas.clientHeight || 210;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    requestAnimationFrame(this.tick);
  }
}

class BodyFrontPreview {
  constructor(canvas, metaNode) {
    this.canvas = canvas;
    this.metaNode = metaNode;
    this.records = [];

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xffffff);

    this.camera = new THREE.PerspectiveCamera(38, 1, 0.01, 60);
    this.camera.position.set(0, 0.4, 4.0);

    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.enablePan = false;
    this.controls.maxPolarAngle = Math.PI * 0.65;
    this.controls.target.set(0, 0.1, 0);

    this.root = new THREE.Group();
    this.scene.add(this.root);

    this.scene.add(new THREE.AmbientLight(0xffffff, 0.68));
    const key = new THREE.DirectionalLight(0xffffff, 1.0);
    key.position.set(2.2, 3.0, 3.8);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0xffffff, 0.56);
    fill.position.set(-2.0, 1.4, 2.0);
    this.scene.add(fill);

    this.tick = this.tick.bind(this);
    requestAnimationFrame(this.tick);
  }

  clear() {
    for (const rec of this.records) {
      this.root.remove(rec.group);
      rec.mesh.geometry.dispose();
      rec.mesh.material.dispose();
      rec.wire.geometry.dispose();
      rec.wire.material.dispose();
    }
    this.records = [];
  }

  async loadSuit(suitspec) {
    this.clear();

    const modules = readEnabledModules(suitspec);
    const relief = Number(UI.reliefSlider.value || "0.05");

    for (const [name, mod] of modules) {
      const assetPath = resolveMeshAssetPath(name, mod);
      let geometry;
      try {
        geometry = await loadMeshGeometryFromAsset(assetPath);
      } catch {
        geometry = new THREE.BoxGeometry(1, 1, 1, 8, 8, 8).toNonIndexed();
      }

      const material = new THREE.MeshStandardMaterial({
        color: 0xeaf1fb,
        metalness: 0.6,
        roughness: 0.34,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.userData.basePositions = new Float32Array(geometry.attributes.position.array);

      const layout = BODY_FRONT_LAYOUT[name] || { pos: [0, 0, 0], scale: [1, 1, 1] };
      mesh.position.set(layout.pos[0], layout.pos[1], layout.pos[2]);
      mesh.scale.set(layout.scale[0], layout.scale[1], layout.scale[2]);

      const wire = new THREE.LineSegments(
        new THREE.EdgesGeometry(geometry, 16),
        new THREE.LineBasicMaterial({ color: 0x244c86, transparent: true, opacity: 0.48 })
      );
      wire.position.copy(mesh.position);
      wire.scale.copy(mesh.scale);

      const group = new THREE.Group();
      group.add(mesh);
      group.add(wire);
      this.root.add(group);

      const tex = await loadTexture(mod.texture_path || null);
      if (tex) {
        mesh.material.map = tex;
        mesh.material.color.setHex(0xffffff);
        mesh.material.needsUpdate = true;
        applyRelief(mesh, tex, relief);
      }

      this.records.push({ partName: name, group, mesh, wire, texture: tex });
    }

    fitCameraToObject(this.camera, this.controls, this.root, 2.6);
    this.metaNode.textContent = [
      `パーツ数: ${this.records.length}`,
      `表示: ボディ前景 + 頂点線`,
      `背景: 白固定`,
      `用途: パーツの接続・密度・前景バランス確認`,
    ].join("\n");
  }

  updateRelief(amplitude) {
    for (const rec of this.records) {
      applyRelief(rec.mesh, rec.texture, amplitude);
    }
  }

  tick() {
    const w = this.canvas.clientWidth || 720;
    const h = this.canvas.clientHeight || 520;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    requestAnimationFrame(this.tick);
  }
}

const bodyFrontPreview = new BodyFrontPreview(UI.bodyFrontCanvas, UI.bodyFrontMeta);

function renderPartChecks(parts) {
  UI.partChecks.innerHTML = "";
  for (const [name] of parts) {
    const label = document.createElement("label");
    const checked = document.createElement("input");
    checked.type = "checkbox";
    checked.value = name;
    checked.checked = true;
    label.appendChild(checked);
    label.append(` ${name}`);
    UI.partChecks.appendChild(label);
  }
}

function selectedParts() {
  return Array.from(UI.partChecks.querySelectorAll("input[type='checkbox']:checked")).map((el) => el.value);
}

function clearPreviews() {
  previewCards.splice(0, previewCards.length);
  UI.cards.innerHTML = "";
}

function switchCardView(card, view) {
  const panes = card.querySelectorAll(".view-pane");
  const buttons = card.querySelectorAll(".view-btn");
  panes.forEach((pane) => pane.classList.toggle("active", pane.dataset.view === view));
  buttons.forEach((btn) => btn.classList.toggle("active", btn.dataset.view === view));
}

function renderPartCards(suitspec) {
  clearPreviews();
  const parts = readEnabledModules(suitspec);

  for (const [name, mod] of parts) {
    const card = document.createElement("article");
    card.className = "card";
    card.innerHTML = `
      <div class="card-head">
        <h3>${name}</h3>
        <small>${mod.texture_path ? "texture ok" : "texture missing"}</small>
      </div>
      <div class="view-tabs">
        <button class="view-btn active" data-view="mesh">3D</button>
        <button class="view-btn" data-view="uv">UV</button>
      </div>
      <canvas class="part-canvas view-pane active" data-view="mesh"></canvas>
      <canvas class="uv-canvas view-pane" data-view="uv"></canvas>
      <div class="uv-stats">UV解析待機中...</div>
      <div class="card-meta">${mod.texture_path || "(texture_path 未設定)"}</div>
    `;
    UI.cards.appendChild(card);

    const preview = new PartCardPreview({
      meshCanvas: card.querySelector(".part-canvas"),
      uvCanvas: card.querySelector(".uv-canvas"),
      statsNode: card.querySelector(".uv-stats"),
      partName: name,
      module: mod,
    });
    previewCards.push(preview);

    for (const btn of card.querySelectorAll(".view-btn")) {
      btn.onclick = () => {
        switchCardView(card, btn.dataset.view);
        if (btn.dataset.view === "uv") {
          preview.updateUvDebug();
        }
      };
    }
  }
}

function activateTab(tab) {
  const isParts = tab === "parts";
  UI.panelParts.classList.toggle("active", isParts);
  UI.panelBody.classList.toggle("active", !isParts);
  for (const btn of UI.tabButtons) {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  }
}

async function loadSuitList() {
  const res = await fetch("/api/suitspecs");
  const data = await res.json();
  if (!data.ok) throw new Error(data.error || "SuitSpec一覧の取得に失敗しました。");

  const options = data.items || [];
  UI.suitPath.innerHTML = "";
  for (const item of options) {
    const op = document.createElement("option");
    op.value = item;
    op.textContent = item;
    UI.suitPath.appendChild(op);
  }

  if (options.length === 0) {
    setStatus("SuitSpec が見つかりません。", true);
    return;
  }

  if (!currentSuitPath || !options.includes(currentSuitPath)) {
    currentSuitPath = options[0];
    UI.suitPath.value = currentSuitPath;
  }
}

async function loadSuit(path) {
  const res = await fetch(`/api/suitspec?path=${encodeURIComponent(path)}`);
  const data = await res.json();
  if (!data.ok) throw new Error(data.error || "SuitSpec読込に失敗しました。");

  currentSuitPath = path;
  currentSuit = data.suitspec;

  const enabled = readEnabledModules(currentSuit);
  renderPartChecks(enabled);
  renderPartCards(currentSuit);
  await bodyFrontPreview.loadSuit(currentSuit);

  setStatus(`読込完了: ${path}\n有効パーツ: ${enabled.length}`);
}

async function runGenerate() {
  if (!currentSuitPath) {
    setStatus("先に SuitSpec を読み込んでください。", true);
    return;
  }

  const body = {
    suitspec: currentSuitPath,
    parts: selectedParts(),
    texture_mode: UI.textureMode.value,
    fallback_dir: UI.fallbackDir.value.trim() || null,
    prefer_fallback: UI.preferFallback.checked,
    update_suitspec: UI.updateSuitspec.checked,
  };

  setStatus("生成中...");

  const res = await fetch("/api/generate-parts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();

  if (!data.ok) {
    setStatus(`生成失敗\n${data.stderr || data.error || "unknown"}`, true);
    return;
  }

  const parsed = data.parsed || {};
  setStatus(
    [
      `生成完了`,
      `session_id=${parsed.session_id || "-"}`,
      `generated=${parsed.generated_count || 0}`,
      `errors=${parsed.error_count || 0}`,
      `fallback=${parsed.fallback_used_count || 0}`,
      `mode=${UI.textureMode.value}`,
    ].join("\n")
  );

  await loadSuit(currentSuitPath);
}

function openBodyFit() {
  const suit = encodeURIComponent(currentSuitPath || UI.suitPath.value);
  const sim = encodeURIComponent(UI.simPath.value.trim() || "sessions/body-sim.json");
  window.open(`/viewer/body-fit/?suitspec=${suit}&sim=${sim}`, "_blank");
}

function bindEvents() {
  UI.btnRefreshSuits.onclick = async () => {
    try {
      await loadSuitList();
      setStatus("SuitSpec一覧を更新しました。");
    } catch (err) {
      setStatus(String(err), true);
    }
  };

  UI.btnLoadSuit.onclick = async () => {
    try {
      await loadSuit(UI.suitPath.value);
    } catch (err) {
      setStatus(String(err), true);
    }
  };

  UI.btnGenerate.onclick = async () => {
    try {
      await runGenerate();
    } catch (err) {
      setStatus(String(err), true);
    }
  };

  UI.btnOpenBodyFit.onclick = openBodyFit;

  UI.reliefSlider.oninput = () => {
    const amp = Number(UI.reliefSlider.value || "0.05");
    for (const preview of previewCards) {
      preview.updateRelief(amp);
    }
    bodyFrontPreview.updateRelief(amp);
  };

  for (const btn of UI.tabButtons) {
    btn.onclick = () => activateTab(btn.dataset.tab || "parts");
  }
}

async function init() {
  bindEvents();
  activateTab("parts");

  try {
    await loadSuitList();
    await loadSuit(UI.suitPath.value);
  } catch (err) {
    setStatus(String(err), true);
  }
}

init();
