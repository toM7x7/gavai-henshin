import * as THREE from "../body-fit/vendor/three/build/three.module.js";

const PARTS = [
  ["helmet", "ヘルメット", true],
  ["chest", "胸部装甲", true],
  ["back", "背面ユニット", true],
  ["waist", "ベルト", true],
  ["left_shoulder", "左肩", true],
  ["right_shoulder", "右肩", true],
  ["left_forearm", "左腕甲", true],
  ["right_forearm", "右腕甲", true],
  ["left_shin", "左すね", true],
  ["right_shin", "右すね", true],
  ["left_boot", "左ブーツ", true],
  ["right_boot", "右ブーツ", true],
  ["left_upperarm", "左上腕", false],
  ["right_upperarm", "右上腕", false],
  ["left_thigh", "左太腿", false],
  ["right_thigh", "右太腿", false],
  ["left_hand", "左手甲", false],
  ["right_hand", "右手甲", false],
];

const PART_POSES = {
  helmet: { p: [0, 1.68, 0.02], s: [0.22, 0.22, 0.22] },
  chest: { p: [0, 1.22, 0.02], s: [0.42, 0.42, 0.42] },
  back: { p: [0, 1.18, -0.16], s: [0.36, 0.36, 0.36] },
  waist: { p: [0, 0.78, 0.02], s: [0.3, 0.3, 0.3] },
  left_shoulder: { p: [-0.43, 1.28, 0], s: [0.26, 0.26, 0.26] },
  right_shoulder: { p: [0.43, 1.28, 0], s: [0.26, 0.26, 0.26] },
  left_upperarm: { p: [-0.66, 1.02, 0], s: [0.24, 0.3, 0.24] },
  right_upperarm: { p: [0.66, 1.02, 0], s: [0.24, 0.3, 0.24] },
  left_forearm: { p: [-0.82, 0.68, 0], s: [0.24, 0.32, 0.24] },
  right_forearm: { p: [0.82, 0.68, 0], s: [0.24, 0.32, 0.24] },
  left_hand: { p: [-0.9, 0.38, 0.02], s: [0.18, 0.18, 0.18] },
  right_hand: { p: [0.9, 0.38, 0.02], s: [0.18, 0.18, 0.18] },
  left_thigh: { p: [-0.18, 0.42, 0], s: [0.25, 0.34, 0.25] },
  right_thigh: { p: [0.18, 0.42, 0], s: [0.25, 0.34, 0.25] },
  left_shin: { p: [-0.18, 0.04, 0], s: [0.25, 0.34, 0.25] },
  right_shin: { p: [0.18, 0.04, 0], s: [0.25, 0.34, 0.25] },
  left_boot: { p: [-0.18, -0.26, 0.06], s: [0.22, 0.22, 0.22] },
  right_boot: { p: [0.18, -0.26, 0.06], s: [0.22, 0.22, 0.22] },
};

const UI = {
  form: document.getElementById("forgeForm"),
  button: document.getElementById("forgeButton"),
  partGrid: document.getElementById("partGrid"),
  canvas: document.getElementById("armorCanvas"),
  emptyStand: document.getElementById("emptyStand"),
  recallCode: document.getElementById("recallCode"),
  suitId: document.getElementById("suitId"),
  manifestId: document.getElementById("manifestId"),
  status: document.getElementById("forgeStatus"),
  questLink: document.getElementById("questLink"),
  displayName: document.getElementById("displayName"),
  archetype: document.getElementById("archetype"),
  temperament: document.getElementById("temperament"),
  primaryColor: document.getElementById("primaryColor"),
  secondaryColor: document.getElementById("secondaryColor"),
  emissiveColor: document.getElementById("emissiveColor"),
  brief: document.getElementById("brief"),
};

function normalizePath(path) {
  const raw = String(path || "").replace(/\\/g, "/");
  if (/^(https?:|data:|blob:)/i.test(raw) || raw.startsWith("/")) return raw;
  return `/${raw}`;
}

async function fetchJson(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `${path} failed with ${response.status}`);
  }
  return data;
}

function setStatus(text, state = "pending") {
  UI.status.classList.remove("pending", "complete", "error");
  UI.status.classList.add(state);
  UI.status.textContent = text;
}

function selectedParts() {
  return Array.from(UI.partGrid.querySelectorAll("input[type='checkbox']:checked")).map((input) => input.value);
}

function renderPartGrid() {
  UI.partGrid.innerHTML = "";
  for (const [id, label, checked] of PARTS) {
    const item = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = id;
    input.checked = checked;
    item.append(input, document.createTextNode(label));
    UI.partGrid.append(item);
  }
}

function formPayload() {
  return {
    display_name: UI.displayName.value.trim(),
    archetype: UI.archetype.value,
    temperament: UI.temperament.value,
    palette: {
      primary: UI.primaryColor.value,
      secondary: UI.secondaryColor.value,
      emissive: UI.emissiveColor.value,
    },
    brief: UI.brief.value.trim(),
    parts: selectedParts(),
  };
}

function materialForPart(part, palette) {
  const primary = new THREE.Color(palette?.primary || "#F4F1E8");
  const secondary = new THREE.Color(palette?.secondary || "#8C96A3");
  const emissive = new THREE.Color(palette?.emissive || "#43D8FF");
  const color = part.includes("shin") || part.includes("boot") || part.includes("forearm") || part.includes("shoulder")
    ? secondary
    : primary;
  return new THREE.MeshStandardMaterial({
    color,
    emissive,
    emissiveIntensity: part === "chest" || part === "helmet" ? 0.22 : 0.12,
    metalness: 0.45,
    roughness: 0.38,
  });
}

function meshGeometryFromPayload(payload) {
  if (!payload || payload.format !== "mesh.v1") {
    throw new Error("Unsupported mesh asset format.");
  }
  const positions = (payload.positions || []).flat();
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  const normals = Array.isArray(payload.normals) ? payload.normals.flat() : [];
  if (normals.length === positions.length) {
    geometry.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  } else {
    geometry.computeVertexNormals();
  }
  const uvs = Array.isArray(payload.uv) ? payload.uv.flat() : [];
  if (uvs.length === (positions.length / 3) * 2) {
    geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  }
  if (Array.isArray(payload.indices)) {
    geometry.setIndex(payload.indices.flat());
  }
  geometry.computeBoundingBox();
  geometry.center();
  return geometry;
}

async function createArmorMesh(part, module, palette) {
  const asset = normalizePath(module?.asset_ref || `viewer/assets/meshes/${part}.mesh.json`);
  const payload = await fetchJson(asset);
  const mesh = new THREE.Mesh(meshGeometryFromPayload(payload), materialForPart(part, palette));
  const pose = PART_POSES[part] || { p: [0, 0.8, 0], s: [0.24, 0.24, 0.24] };
  mesh.name = part;
  mesh.position.set(...pose.p);
  mesh.rotation.set(Math.PI / 2, 0, 0);
  mesh.scale.set(...pose.s);
  return mesh;
}

class ArmorStand {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x080b0b);
    this.camera = new THREE.PerspectiveCamera(38, 1, 0.05, 40);
    this.camera.position.set(0, 0.95, 4.1);
    this.group = new THREE.Group();
    this.scene.add(this.group);
    this.scene.add(new THREE.HemisphereLight(0xeef9ff, 0x222018, 2.1));
    const key = new THREE.DirectionalLight(0xfff2cc, 2.6);
    key.position.set(2.4, 3.4, 3);
    this.scene.add(key);
    this.buildBaseSuit();
    this.animate();
    window.addEventListener("resize", () => this.resize());
  }

  buildBaseSuit() {
    const ghost = new THREE.MeshBasicMaterial({
      color: 0x5ad8ff,
      transparent: true,
      opacity: 0.16,
      depthWrite: false,
    });
    const standMat = new THREE.MeshBasicMaterial({ color: 0xf4c766, transparent: true, opacity: 0.45 });
    const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.24, 0.82, 32), ghost);
    torso.position.y = 0.98;
    this.group.add(torso);
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.19, 32, 20), ghost);
    head.position.y = 1.58;
    this.group.add(head);
    for (const [x, y, h, r] of [
      [-0.58, 0.86, 0.82, -0.2],
      [0.58, 0.86, 0.82, 0.2],
      [-0.17, 0.18, 0.78, 0],
      [0.17, 0.18, 0.78, 0],
    ]) {
      const limb = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.07, h, 20), ghost);
      limb.position.set(x, y, -0.03);
      limb.rotation.z = r;
      this.group.add(limb);
    }
    const base = new THREE.Mesh(new THREE.TorusGeometry(0.72, 0.01, 8, 96), standMat);
    base.rotation.x = Math.PI / 2;
    base.position.y = -0.43;
    this.group.add(base);
    const spine = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 2.1, 12), standMat);
    spine.position.set(0, 0.62, -0.28);
    this.group.add(spine);
  }

  clearArmor() {
    const removable = this.group.children.filter((child) => child.userData?.armorPart);
    for (const child of removable) {
      child.removeFromParent();
      child.geometry?.dispose?.();
      child.material?.dispose?.();
    }
  }

  async renderSuit(suitspec) {
    this.clearArmor();
    const modules = suitspec?.modules || {};
    const palette = suitspec?.palette || {};
    const records = Object.entries(modules).filter(([, module]) => module?.enabled);
    const meshes = await Promise.all(records.map(([part, module]) => createArmorMesh(part, module, palette)));
    for (const mesh of meshes) {
      mesh.userData.armorPart = true;
      this.group.add(mesh);
    }
  }

  resize() {
    const width = this.canvas.clientWidth || 640;
    const height = this.canvas.clientHeight || 640;
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  animate() {
    this.resize();
    this.group.rotation.y = Math.sin(performance.now() * 0.00028) * 0.18;
    this.renderer.render(this.scene, this.camera);
    requestAnimationFrame(() => this.animate());
  }
}

const armorStand = new ArmorStand(UI.canvas);

function applyResult(data) {
  UI.recallCode.textContent = data.recall_code || "----";
  UI.suitId.textContent = data.suit_id || "未発行";
  UI.manifestId.textContent = data.manifest_id || "未発行";
  UI.questLink.href = `/viewer/quest-iw-demo/?code=${encodeURIComponent(data.recall_code)}&newRoute=1`;
  UI.questLink.classList.remove("disabled");
  UI.questLink.setAttribute("aria-disabled", "false");
  UI.emptyStand.classList.add("hidden");
}

async function submitForge(event) {
  event.preventDefault();
  UI.button.disabled = true;
  setStatus("生成条件を送信中...", "pending");
  try {
    const data = await fetchJson("/v1/suits/forge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formPayload()),
    });
    setStatus("鎧立てを構築中...", "pending");
    await armorStand.renderSuit(data.suitspec);
    applyResult(data);
    setStatus("生成完了 / Quest呼び出し準備OK", "complete");
  } catch (error) {
    setStatus(String(error?.message || error), "error");
  } finally {
    UI.button.disabled = false;
  }
}

renderPartGrid();
UI.form.addEventListener("submit", submitForge);
