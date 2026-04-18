import * as THREE from "three";
import {
  buildVrmBodySurfaceModelFromSamples,
  collectVrmSurfaceSamples,
} from "./auto-fit-engine.js?v=20260412g";

const REGION_COLORS = Object.freeze({
  head: 0x6eb7ff,
  torso: 0x5de3d8,
  left_upperarm: 0xffb54a,
  right_upperarm: 0xffb54a,
  left_forearm: 0xff8f4f,
  right_forearm: 0xff8f4f,
  left_thigh: 0xae87ff,
  right_thigh: 0xae87ff,
  left_shin: 0xc09dff,
  right_shin: 0xc09dff,
  left_foot: 0xff739c,
  right_foot: 0xff739c,
});

const SURFACE_FIRST_DEFAULTS = Object.freeze({
  maxSamplesPerMesh: 72,
  shellOffset: 0.018,
  graphPointSize: 0.019,
  shellPointSize: 0.028,
  shellOpacity: 0.72,
  graphOpacity: 0.9,
  graphLinkOpacity: 0.32,
  maxGraphNodesPerRegion: 20,
});

const MOUNT_DEFS = Object.freeze([
  { name: "head_crown", region: "head" },
  { name: "chest_front", region: "torso" },
  { name: "upper_back", region: "torso" },
  { name: "waist_front", region: "torso" },
  { name: "left_shoulder_mount", region: "left_upperarm" },
  { name: "right_shoulder_mount", region: "right_upperarm" },
  { name: "left_forearm_mount", region: "left_forearm" },
  { name: "right_forearm_mount", region: "right_forearm" },
  { name: "left_shin_mount", region: "left_shin" },
  { name: "right_shin_mount", region: "right_shin" },
  { name: "left_boot_mount", region: "left_foot" },
  { name: "right_boot_mount", region: "right_foot" },
]);

const _tmpVecA = new THREE.Vector3();
const _tmpVecB = new THREE.Vector3();
const _tmpVecC = new THREE.Vector3();
const _tmpVecD = new THREE.Vector3();

let sharedPointSpriteTexture = null;

function numberOr(value, fallback = 0) {
  return Number.isFinite(value) ? value : fallback;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function round3(value) {
  return Math.round(numberOr(value, 0) * 1000) / 1000;
}

function samplePoint(sample) {
  if (sample instanceof THREE.Vector3) return sample;
  if (sample?.position instanceof THREE.Vector3) return sample.position;
  if (
    sample &&
    Number.isFinite(sample.x) &&
    Number.isFinite(sample.y) &&
    Number.isFinite(numberOr(sample.z, 0))
  ) {
    return new THREE.Vector3(sample.x, sample.y, numberOr(sample.z, 0));
  }
  return new THREE.Vector3();
}

function stableSampleId(sample, index) {
  return String(sample?.id || sample?.sampleId || `surface:${index}`);
}

function sampleSource(sample) {
  if (!sample || sample instanceof THREE.Vector3) return null;
  return {
    meshKey: String(sample.meshKey || ""),
    meshName: String(sample.meshName || ""),
    vertexIndex: Number.isFinite(sample.vertexIndex) ? sample.vertexIndex : null,
    skinned: Boolean(sample.skinned),
  };
}

function normalizeVector(vector, fallback = new THREE.Vector3(0, 0, 1)) {
  if (vector?.lengthSq?.() > 1e-6) return vector.normalize();
  return fallback.clone();
}

function regionColor(region) {
  return REGION_COLORS[region] || 0xd3ebff;
}

function tintColor(hex, factor = 1) {
  const color = new THREE.Color(hex);
  const hsl = {};
  color.getHSL(hsl);
  color.setHSL(hsl.h, clamp(hsl.s * 0.96, 0, 1), clamp(hsl.l * factor, 0, 1));
  return color;
}

function createPointSpriteTexture() {
  if (sharedPointSpriteTexture) return sharedPointSpriteTexture;
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  const gradient = ctx.createRadialGradient(32, 32, 4, 32, 32, 28);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.45, "rgba(255,255,255,0.92)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(32, 32, 28, 0, Math.PI * 2);
  ctx.fill();
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.userData.surfaceFirstShared = true;
  sharedPointSpriteTexture = texture;
  return sharedPointSpriteTexture;
}

function closestPointOnSegment(point, start, end, target = new THREE.Vector3()) {
  const ab = _tmpVecA.copy(end).sub(start);
  const denom = ab.lengthSq();
  if (denom < 1e-6) {
    target.copy(start);
    return { point: target, t: 0 };
  }
  const t = clamp(_tmpVecB.copy(point).sub(start).dot(ab) / denom, 0, 1);
  target.copy(start).addScaledVector(ab, t);
  return { point: target, t };
}

function evaluateSphereProjection(point, proxy) {
  const center = proxy?.center?.clone?.() || new THREE.Vector3();
  const normal = normalizeVector(point.clone().sub(center));
  const surfacePoint = center.clone().addScaledVector(normal, numberOr(proxy?.radius, 0.12));
  return {
    region: "head",
    normal,
    surfacePoint,
    surfaceDelta: point.distanceTo(surfacePoint),
  };
}

function evaluateCapsuleProjection(point, proxy, region) {
  const start = proxy?.start?.clone?.() || new THREE.Vector3();
  const end = proxy?.end?.clone?.() || start.clone().add(new THREE.Vector3(0, -0.2, 0));
  const closest = closestPointOnSegment(point, start, end, _tmpVecC).point.clone();
  const normal = normalizeVector(point.clone().sub(closest), new THREE.Vector3(0, 0, 1));
  const surfacePoint = closest.clone().addScaledVector(normal, numberOr(proxy?.radius, 0.08));
  return {
    region,
    normal,
    surfacePoint,
    surfaceDelta: point.distanceTo(surfacePoint),
  };
}

function obbLocal(point, proxy) {
  const delta = point.clone().sub(proxy?.center || new THREE.Vector3());
  return new THREE.Vector3(
    delta.dot(proxy?.axes?.x || new THREE.Vector3(1, 0, 0)),
    delta.dot(proxy?.axes?.y || new THREE.Vector3(0, 1, 0)),
    delta.dot(proxy?.axes?.z || new THREE.Vector3(0, 0, 1))
  );
}

function evaluateTorsoProjection(point, proxy) {
  const local = obbLocal(point, proxy);
  const half = proxy?.halfSize || new THREE.Vector3(0.2, 0.32, 0.12);
  const dx = Math.abs(Math.abs(local.x) - half.x);
  const dy = Math.abs(Math.abs(local.y) - half.y);
  const dz = Math.abs(Math.abs(local.z) - half.z);
  let axis = "z";
  let sign = Math.sign(local.z) || 1;
  let minDelta = dz;
  if (dx < minDelta) {
    axis = "x";
    sign = Math.sign(local.x) || 1;
    minDelta = dx;
  }
  if (dy < minDelta) {
    axis = "y";
    sign = Math.sign(local.y) || 1;
    minDelta = dy;
  }
  const normal =
    axis === "x"
      ? proxy.axes.x.clone().multiplyScalar(sign)
      : axis === "y"
        ? proxy.axes.y.clone().multiplyScalar(sign)
        : proxy.axes.z.clone().multiplyScalar(sign);
  const surfacePoint = proxy.center
    .clone()
    .addScaledVector(proxy.axes.x, axis === "x" ? half.x * sign : clamp(local.x, -half.x, half.x))
    .addScaledVector(proxy.axes.y, axis === "y" ? half.y * sign : clamp(local.y, -half.y, half.y))
    .addScaledVector(proxy.axes.z, axis === "z" ? half.z * sign : clamp(local.z, -half.z, half.z));
  return {
    region: "torso",
    normal: normalizeVector(normal),
    surfacePoint,
    surfaceDelta: point.distanceTo(surfacePoint),
  };
}

function evaluateFootProjection(point, proxy, region) {
  const center = proxy?.center?.clone?.() || new THREE.Vector3();
  const half = proxy?.halfSize || new THREE.Vector3(0.08, 0.04, 0.12);
  const local = point.clone().sub(center);
  const dx = Math.abs(Math.abs(local.x) - half.x);
  const dy = Math.abs(Math.abs(local.y) - half.y);
  const dz = Math.abs(Math.abs(local.z) - half.z);
  let axis = "z";
  let sign = Math.sign(local.z) || 1;
  let minDelta = dz;
  if (dx < minDelta) {
    axis = "x";
    sign = Math.sign(local.x) || 1;
    minDelta = dx;
  }
  if (dy < minDelta) {
    axis = "y";
    sign = Math.sign(local.y) || 1;
  }
  const normal =
    axis === "x"
      ? new THREE.Vector3(sign, 0, 0)
      : axis === "y"
        ? new THREE.Vector3(0, sign, 0)
        : new THREE.Vector3(0, 0, sign);
  const surfacePoint = center.clone().add(
    new THREE.Vector3(
      axis === "x" ? half.x * sign : clamp(local.x, -half.x, half.x),
      axis === "y" ? half.y * sign : clamp(local.y, -half.y, half.y),
      axis === "z" ? half.z * sign : clamp(local.z, -half.z, half.z)
    )
  );
  return {
    region,
    normal,
    surfacePoint,
    surfaceDelta: point.distanceTo(surfacePoint),
  };
}

function classifyPointAgainstProxies(point, proxies = {}) {
  const candidates = [];
  if (proxies.head) candidates.push(evaluateSphereProjection(point, proxies.head));
  if (proxies.torso) candidates.push(evaluateTorsoProjection(point, proxies.torso));
  for (const region of [
    "left_upperarm",
    "right_upperarm",
    "left_forearm",
    "right_forearm",
    "left_thigh",
    "right_thigh",
    "left_shin",
    "right_shin",
  ]) {
    if (proxies[region]) candidates.push(evaluateCapsuleProjection(point, proxies[region], region));
  }
  for (const region of ["left_foot", "right_foot"]) {
    if (proxies[region]) candidates.push(evaluateFootProjection(point, proxies[region], region));
  }
  if (!candidates.length) {
    return {
      region: "torso",
      normal: new THREE.Vector3(0, 0, 1),
      surfacePoint: point.clone(),
      surfaceDelta: 0,
    };
  }
  candidates.sort((a, b) => a.surfaceDelta - b.surfaceDelta);
  return candidates[0];
}

function axisFrame(axis, fallbackForward = new THREE.Vector3(0, 0, 1)) {
  const safeAxis = normalizeVector(axis.clone(), new THREE.Vector3(0, 1, 0));
  let tangent = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), safeAxis);
  if (tangent.lengthSq() < 1e-6) {
    tangent = new THREE.Vector3().crossVectors(fallbackForward, safeAxis);
  }
  tangent = normalizeVector(tangent, new THREE.Vector3(1, 0, 0));
  const bitangent = normalizeVector(new THREE.Vector3().crossVectors(safeAxis, tangent), new THREE.Vector3(0, 0, 1));
  return { axis: safeAxis, tangent, bitangent };
}

function proxyForRegion(region, proxies = {}) {
  return proxies?.[region] || null;
}

function createSurfaceBinding(point, projection, proxies = {}) {
  const proxy = proxyForRegion(projection.region, proxies);
  if (!proxy) {
    return {
      region: projection.region,
      proxyType: null,
    };
  }
  if (proxy.type === "head_sphere") {
    const center = proxy.center?.clone?.() || new THREE.Vector3();
    const dir = normalizeVector(point.clone().sub(center), new THREE.Vector3(0, 0, 1));
    const distance = Math.max(point.distanceTo(center), 1e-5);
    return {
      region: projection.region,
      proxyType: proxy.type,
      sphere: {
        direction: { x: round3(dir.x), y: round3(dir.y), z: round3(dir.z) },
        radiusScale: round3(distance / Math.max(numberOr(proxy.radius, 0.12), 1e-5)),
      },
    };
  }
  if (proxy.type === "capsule") {
    const start = proxy.start?.clone?.() || new THREE.Vector3();
    const end = proxy.end?.clone?.() || start.clone().add(new THREE.Vector3(0, -0.2, 0));
    const closest = closestPointOnSegment(point, start, end, _tmpVecD).point.clone();
    const { axis, tangent, bitangent } = axisFrame(end.clone().sub(start));
    const radius = Math.max(numberOr(proxy.radius, 0.08), 1e-5);
    const radial = point.clone().sub(closest);
    return {
      region: projection.region,
      proxyType: proxy.type,
      capsule: {
        t: round3(closestPointOnSegment(point, start, end).t),
        radialX: round3(radial.dot(tangent) / radius),
        radialY: round3(radial.dot(bitangent) / radius),
        radialScale: round3(radial.length() / radius),
        axis: { x: round3(axis.x), y: round3(axis.y), z: round3(axis.z) },
      },
    };
  }
  if (proxy.type === "torso_obb" || proxy.type === "foot_obb") {
    const local = obbLocal(point, proxy);
    const half = proxy?.halfSize || new THREE.Vector3(0.2, 0.2, 0.2);
    const xNorm = round3(local.x / Math.max(half.x, 1e-5));
    const yNorm = round3(local.y / Math.max(half.y, 1e-5));
    const zNorm = round3(local.z / Math.max(half.z, 1e-5));
    let faceAxis = "z";
    let faceSign = Math.sign(zNorm) || 1;
    let maxAbs = Math.abs(zNorm);
    if (Math.abs(xNorm) > maxAbs) {
      faceAxis = "x";
      faceSign = Math.sign(xNorm) || 1;
      maxAbs = Math.abs(xNorm);
    }
    if (Math.abs(yNorm) > maxAbs) {
      faceAxis = "y";
      faceSign = Math.sign(yNorm) || 1;
    }
    return {
      region: projection.region,
      proxyType: proxy.type,
      obb: {
        xNorm,
        yNorm,
        zNorm,
        faceAxis,
        faceSign,
      },
    };
  }
  return {
    region: projection.region,
    proxyType: proxy.type,
  };
}

function applySurfaceBinding(node, proxies = {}) {
  const binding = node?.binding || {};
  const region = binding.region || node?.region || "torso";
  const proxy = proxyForRegion(region, proxies);
  if (!proxy) {
    const fallbackPoint = samplePoint(node?.surfacePoint || node?.position || null);
    return {
      region,
      normal: new THREE.Vector3(0, 0, 1),
      surfacePoint: fallbackPoint.clone(),
      position: fallbackPoint.clone(),
      surfaceDelta: 0,
    };
  }

  if (proxy.type === "head_sphere") {
    const dir = normalizeVector(
      new THREE.Vector3(
        numberOr(binding?.sphere?.direction?.x, 0),
        numberOr(binding?.sphere?.direction?.y, 0),
        numberOr(binding?.sphere?.direction?.z, 1)
      ),
      new THREE.Vector3(0, 0, 1)
    );
    const radius = Math.max(numberOr(proxy.radius, 0.12), 1e-5);
    const scale = Math.max(numberOr(binding?.sphere?.radiusScale, 1), 0.25);
    const surfacePoint = (proxy.center?.clone?.() || new THREE.Vector3()).addScaledVector(dir, radius * scale);
    return {
      region,
      normal: dir.clone(),
      surfacePoint,
      position: surfacePoint.clone(),
      surfaceDelta: 0,
    };
  }

  if (proxy.type === "capsule") {
    const start = proxy.start?.clone?.() || new THREE.Vector3();
    const end = proxy.end?.clone?.() || start.clone().add(new THREE.Vector3(0, -0.2, 0));
    const t = clamp(numberOr(binding?.capsule?.t, 0.5), 0, 1);
    const closest = start.clone().lerp(end, t);
    const radius = Math.max(numberOr(proxy.radius, 0.08), 1e-5);
    const { tangent, bitangent } = axisFrame(end.clone().sub(start));
    const radial = tangent
      .clone()
      .multiplyScalar(numberOr(binding?.capsule?.radialX, 0))
      .addScaledVector(bitangent, numberOr(binding?.capsule?.radialY, 0));
    const radialNormal = normalizeVector(radial, tangent.clone());
    const radialScale = Math.max(numberOr(binding?.capsule?.radialScale, 1), 0.2);
    const surfacePoint = closest.clone().addScaledVector(radialNormal, radius * radialScale);
    return {
      region,
      normal: radialNormal,
      surfacePoint,
      position: surfacePoint.clone(),
      surfaceDelta: 0,
    };
  }

  if (proxy.type === "torso_obb" || proxy.type === "foot_obb") {
    const half = proxy?.halfSize || new THREE.Vector3(0.2, 0.2, 0.2);
    const xNorm = numberOr(binding?.obb?.xNorm, 0);
    const yNorm = numberOr(binding?.obb?.yNorm, 0);
    const zNorm = numberOr(binding?.obb?.zNorm, 1);
    const surfacePoint = (proxy.center?.clone?.() || new THREE.Vector3())
      .addScaledVector(proxy.axes?.x || new THREE.Vector3(1, 0, 0), half.x * xNorm)
      .addScaledVector(proxy.axes?.y || new THREE.Vector3(0, 1, 0), half.y * yNorm)
      .addScaledVector(proxy.axes?.z || new THREE.Vector3(0, 0, 1), half.z * zNorm);
    const axis = binding?.obb?.faceAxis || "z";
    const sign = Math.sign(numberOr(binding?.obb?.faceSign, 1)) || 1;
    const normal =
      axis === "x"
        ? (proxy.axes?.x || new THREE.Vector3(1, 0, 0)).clone().multiplyScalar(sign)
        : axis === "y"
          ? (proxy.axes?.y || new THREE.Vector3(0, 1, 0)).clone().multiplyScalar(sign)
          : (proxy.axes?.z || new THREE.Vector3(0, 0, 1)).clone().multiplyScalar(sign);
    return {
      region,
      normal: normalizeVector(normal),
      surfacePoint,
      position: surfacePoint.clone(),
      surfaceDelta: 0,
    };
  }

  const fallbackPoint = samplePoint(node?.surfacePoint || node?.position || null);
  return {
    region,
    normal: new THREE.Vector3(0, 0, 1),
    surfacePoint: fallbackPoint.clone(),
    position: fallbackPoint.clone(),
    surfaceDelta: 0,
  };
}

function resampleNodes(nodes, maxCount) {
  if (!Array.isArray(nodes) || nodes.length <= maxCount) return nodes.slice();
  const step = Math.max(1, Math.floor(nodes.length / maxCount));
  const result = [];
  for (let index = 0; index < nodes.length; index += step) {
    result.push(nodes[index]);
  }
  return result.slice(0, maxCount);
}

function buildGraphLinks(nodes, options = {}) {
  const byRegion = new Map();
  for (const node of nodes) {
    if (!byRegion.has(node.region)) byRegion.set(node.region, []);
    byRegion.get(node.region).push(node);
  }
  const links = [];
  const maxPerRegion = Math.max(6, numberOr(options.maxGraphNodesPerRegion, SURFACE_FIRST_DEFAULTS.maxGraphNodesPerRegion));
  for (const [region, regionNodes] of byRegion.entries()) {
    const subset = resampleNodes(
      regionNodes
        .slice()
        .sort((a, b) => {
          if (Math.abs(a.position.y - b.position.y) > 0.01) return b.position.y - a.position.y;
          if (Math.abs(a.position.z - b.position.z) > 0.01) return a.position.z - b.position.z;
          return a.position.x - b.position.x;
        }),
      maxPerRegion
    );
    for (let index = 0; index < subset.length - 1; index += 1) {
      links.push({
        region,
        start: subset[index].position.clone(),
        end: subset[index + 1].position.clone(),
      });
      if (index + 2 < subset.length && index % 2 === 0) {
        links.push({
          region,
          start: subset[index].position.clone(),
          end: subset[index + 2].position.clone(),
        });
      }
    }
  }
  return links;
}

function buildGraphNodes(surfacePoints, proxies = {}) {
  const nodes = [];
  const regionCounts = {};
  surfacePoints.forEach((sample, index) => {
    const point = samplePoint(sample).clone();
    const projection = classifyPointAgainstProxies(point, proxies);
    const stripe = 0.82 + Math.sin(point.y * 18 + point.z * 14) * 0.18;
    const color = tintColor(regionColor(projection.region), stripe);
    regionCounts[projection.region] = (regionCounts[projection.region] || 0) + 1;
    nodes.push({
      id: stableSampleId(sample, index),
      source: sampleSource(sample),
      region: projection.region,
      position: point.clone(),
      normal: projection.normal.clone(),
      surfacePoint: projection.surfacePoint.clone(),
      surfaceDelta: projection.surfaceDelta,
      color,
      binding: createSurfaceBinding(projection.surfacePoint.clone(), projection, proxies),
    });
  });
  return { nodes, regionCounts };
}

function buildMounts(proxies = {}) {
  const mounts = [];
  const torso = proxies.torso;
  const head = proxies.head;
  const pushMount = (name, region, position, normal) => {
    if (!position || !normal) return;
    mounts.push({
      name,
      region,
      position: position.clone(),
      normal: normalizeVector(normal.clone()),
      color: tintColor(regionColor(region), 1.12),
    });
  };

  if (head?.center) {
    pushMount(
      "head_crown",
      "head",
      head.center.clone().add(new THREE.Vector3(0, numberOr(head.radius, 0.12) * 0.82, 0)),
      new THREE.Vector3(0, 1, 0)
    );
  }
  if (torso?.center && torso?.axes && torso?.halfSize) {
    pushMount(
      "chest_front",
      "torso",
      torso.center.clone()
        .addScaledVector(torso.axes.y, torso.halfSize.y * 0.14)
        .addScaledVector(torso.axes.z, torso.halfSize.z + 0.014),
      torso.axes.z
    );
    pushMount(
      "upper_back",
      "torso",
      torso.center.clone()
        .addScaledVector(torso.axes.y, torso.halfSize.y * 0.12)
        .addScaledVector(torso.axes.z, -(torso.halfSize.z + 0.016)),
      torso.axes.z.clone().multiplyScalar(-1)
    );
    pushMount(
      "waist_front",
      "torso",
      torso.center.clone()
        .addScaledVector(torso.axes.y, -torso.halfSize.y * 0.42)
        .addScaledVector(torso.axes.z, torso.halfSize.z + 0.012),
      torso.axes.z
    );
  }

  const capsuleMount = (name, region, proxy, t = 0.2) => {
    if (!proxy?.start || !proxy?.end) return;
    const axis = proxy.end.clone().sub(proxy.start);
    const along = proxy.start.clone().addScaledVector(axis, t);
    const side = normalizeVector(new THREE.Vector3(axis.z, 0, -axis.x), new THREE.Vector3(0, 0, 1));
    pushMount(name, region, along.clone().addScaledVector(side, numberOr(proxy.radius, 0.06) + 0.01), side);
  };

  capsuleMount("left_shoulder_mount", "left_upperarm", proxies.left_upperarm, 0.08);
  capsuleMount("right_shoulder_mount", "right_upperarm", proxies.right_upperarm, 0.08);
  capsuleMount("left_forearm_mount", "left_forearm", proxies.left_forearm, 0.68);
  capsuleMount("right_forearm_mount", "right_forearm", proxies.right_forearm, 0.68);
  capsuleMount("left_shin_mount", "left_shin", proxies.left_shin, 0.62);
  capsuleMount("right_shin_mount", "right_shin", proxies.right_shin, 0.62);

  if (proxies.left_foot?.center && proxies.left_foot?.halfSize) {
    pushMount(
      "left_boot_mount",
      "left_foot",
      proxies.left_foot.center.clone().add(new THREE.Vector3(0, 0, proxies.left_foot.halfSize.z + 0.016)),
      new THREE.Vector3(0, 0, 1)
    );
  }
  if (proxies.right_foot?.center && proxies.right_foot?.halfSize) {
    pushMount(
      "right_boot_mount",
      "right_foot",
      proxies.right_foot.center.clone().add(new THREE.Vector3(0, 0, proxies.right_foot.halfSize.z + 0.016)),
      new THREE.Vector3(0, 0, 1)
    );
  }

  return mounts.filter((mount) => MOUNT_DEFS.some((definition) => definition.name === mount.name));
}

function buildPointGeometry(nodes, { shellOffset = 0, shellJitter = 0 } = {}) {
  const positions = new Float32Array(nodes.length * 3);
  const colors = new Float32Array(nodes.length * 3);
  nodes.forEach((node, index) => {
    const point = node.position
      .clone()
      .addScaledVector(node.normal, shellOffset)
      .addScaledVector(node.normal, shellJitter * Math.sin(index * 0.7 + node.position.y * 6));
    positions[index * 3 + 0] = point.x;
    positions[index * 3 + 1] = point.y;
    positions[index * 3 + 2] = point.z;
    colors[index * 3 + 0] = node.color.r;
    colors[index * 3 + 1] = node.color.g;
    colors[index * 3 + 2] = node.color.b;
  });
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geometry.computeBoundingSphere();
  return geometry;
}

function createPointLayer(nodes, options = {}) {
  const geometry = buildPointGeometry(nodes, {
    shellOffset: numberOr(options.shellOffset, 0),
    shellJitter: numberOr(options.shellJitter, 0),
  });
  const material = new THREE.PointsMaterial({
    size: numberOr(options.size, SURFACE_FIRST_DEFAULTS.graphPointSize),
    map: createPointSpriteTexture(),
    transparent: true,
    opacity: clamp(numberOr(options.opacity, 1), 0.05, 1),
    depthWrite: false,
    depthTest: false,
    vertexColors: true,
    sizeAttenuation: true,
    blending: options.additive ? THREE.AdditiveBlending : THREE.NormalBlending,
  });
  const points = new THREE.Points(geometry, material);
  points.renderOrder = numberOr(options.renderOrder, 4);
  return points;
}

export function createSurfacePointLayer(nodes, options = {}) {
  return createPointLayer(nodes, options);
}

function createLinkLayer(links, options = {}) {
  const positions = new Float32Array(links.length * 6);
  const colors = new Float32Array(links.length * 6);
  links.forEach((link, index) => {
    const color = tintColor(regionColor(link.region), 0.92);
    positions[index * 6 + 0] = link.start.x;
    positions[index * 6 + 1] = link.start.y;
    positions[index * 6 + 2] = link.start.z;
    positions[index * 6 + 3] = link.end.x;
    positions[index * 6 + 4] = link.end.y;
    positions[index * 6 + 5] = link.end.z;
    for (let cursor = 0; cursor < 2; cursor += 1) {
      colors[index * 6 + cursor * 3 + 0] = color.r;
      colors[index * 6 + cursor * 3 + 1] = color.g;
      colors[index * 6 + cursor * 3 + 2] = color.b;
    }
  });
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  const material = new THREE.LineBasicMaterial({
    transparent: true,
    opacity: clamp(numberOr(options.opacity, SURFACE_FIRST_DEFAULTS.graphLinkOpacity), 0.05, 1),
    depthWrite: false,
    depthTest: false,
    vertexColors: true,
  });
  const lineSegments = new THREE.LineSegments(geometry, material);
  lineSegments.renderOrder = numberOr(options.renderOrder, 3);
  return lineSegments;
}

function createMountLayer(mounts) {
  const group = new THREE.Group();
  const sphereGeometry = new THREE.SphereGeometry(0.015, 14, 10);
  mounts.forEach((mount) => {
    const sphereMaterial = new THREE.MeshBasicMaterial({
      color: mount.color,
      transparent: true,
      opacity: 0.92,
      depthTest: false,
    });
    const sphere = new THREE.Mesh(sphereGeometry, sphereMaterial);
    sphere.position.copy(mount.position);
    sphere.name = `surfaceMount:${mount.name}`;
    group.add(sphere);

    const lineGeometry = new THREE.BufferGeometry().setFromPoints([
      mount.position,
      mount.position.clone().addScaledVector(mount.normal, 0.06),
    ]);
    const lineMaterial = new THREE.LineBasicMaterial({
      color: mount.color,
      transparent: true,
      opacity: 0.8,
      depthWrite: false,
      depthTest: false,
    });
    const line = new THREE.Line(lineGeometry, lineMaterial);
    line.name = `surfaceMountNormal:${mount.name}`;
    group.add(line);
  });
  group.renderOrder = 6;
  return group;
}

export function buildSurfaceFirstSnapshot({ vrmModel, resolveBone, bodyInference, options = {} }) {
  if (!vrmModel || !bodyInference?.joints || !bodyInference?.metrics) return null;
  const maxSamplesPerMesh = clamp(
    Math.round(numberOr(options.maxSamplesPerMesh, SURFACE_FIRST_DEFAULTS.maxSamplesPerMesh)),
    24,
    240
  );
  const surfacePoints = collectVrmSurfaceSamples(vrmModel, { maxSamplesPerMesh });
  const surfaceModel = buildVrmBodySurfaceModelFromSamples(
    surfacePoints,
    resolveBone,
    bodyInference.joints,
    bodyInference.metrics
  );
  const { nodes, regionCounts } = buildGraphNodes(surfacePoints, surfaceModel.proxies);
  const links = buildGraphLinks(nodes, options);
  const mounts = buildMounts(surfaceModel.proxies);
  return {
    sampleCount: surfacePoints.length,
    density: maxSamplesPerMesh,
    shellOffset: round3(numberOr(options.shellOffset, SURFACE_FIRST_DEFAULTS.shellOffset)),
    nodes,
    links,
    mounts,
    proxies: surfaceModel.proxies,
    buckets: surfaceModel.buckets,
    regionCounts,
  };
}

export function reprojectSurfaceFirstSnapshot(snapshot, { bodyInference, resolveBone, surfaceSamples = [], options = {} } = {}) {
  if (!snapshot?.nodes?.length || !bodyInference?.joints || !bodyInference?.metrics) return null;
  const surfaceModel = buildVrmBodySurfaceModelFromSamples(
    Array.isArray(surfaceSamples) ? surfaceSamples : [],
    resolveBone,
    bodyInference.joints,
    bodyInference.metrics
  );
  const nodes = snapshot.nodes.map((node) => {
    const projected = applySurfaceBinding(node, surfaceModel.proxies);
    return {
      ...node,
      region: projected.region,
      normal: projected.normal,
      surfacePoint: projected.surfacePoint,
      position: projected.position,
      surfaceDelta: projected.surfaceDelta,
    };
  });
  const regionCounts = nodes.reduce((acc, node) => {
    acc[node.region] = (acc[node.region] || 0) + 1;
    return acc;
  }, {});
  return {
    ...snapshot,
    nodes,
    links: buildGraphLinks(nodes, options),
    mounts: buildMounts(surfaceModel.proxies),
    proxies: surfaceModel.proxies,
    buckets: surfaceModel.buckets,
    regionCounts,
    trackingSource: String(options.trackingSource || snapshot.trackingSource || "vrm"),
  };
}

export function summarizeSurfaceFirstSnapshot(snapshot, options = {}) {
  if (!snapshot) return null;
  return {
    sample_count: snapshot.sampleCount,
    density: snapshot.density,
    shell_offset: round3(numberOr(options.shellOffset, snapshot.shellOffset)),
    link_count: snapshot.links.length,
    mount_count: snapshot.mounts.length,
    region_counts: snapshot.regionCounts,
    graph_visible: Boolean(options.graphVisible),
    shell_visible: Boolean(options.shellVisible),
    mounts_visible: Boolean(options.mountsVisible),
  };
}

export function createSurfaceFirstDemoRig(snapshot, options = {}) {
  if (!snapshot) return null;
  const graphGroup = new THREE.Group();
  graphGroup.name = "surfaceFirst:graph";
  graphGroup.add(
    createLinkLayer(snapshot.links, {
      opacity: numberOr(options.graphLinkOpacity, SURFACE_FIRST_DEFAULTS.graphLinkOpacity),
      renderOrder: 3,
    })
  );
  graphGroup.add(
    createPointLayer(snapshot.nodes, {
      size: numberOr(options.graphPointSize, SURFACE_FIRST_DEFAULTS.graphPointSize),
      opacity: numberOr(options.graphOpacity, SURFACE_FIRST_DEFAULTS.graphOpacity),
      renderOrder: 4,
    })
  );

  const shellGroup = new THREE.Group();
  shellGroup.name = "surfaceFirst:shell";
  shellGroup.add(
    createPointLayer(snapshot.nodes, {
      size: numberOr(options.shellPointSize, SURFACE_FIRST_DEFAULTS.shellPointSize),
      opacity: numberOr(options.shellOpacity, SURFACE_FIRST_DEFAULTS.shellOpacity),
      shellOffset: numberOr(options.shellOffset, snapshot.shellOffset),
      shellJitter: 0.0025,
      additive: true,
      renderOrder: 5,
    })
  );

  const mountGroup = createMountLayer(snapshot.mounts);
  mountGroup.name = "surfaceFirst:mounts";

  const group = new THREE.Group();
  group.name = "surfaceFirst:root";
  group.add(graphGroup);
  group.add(shellGroup);
  group.add(mountGroup);
  graphGroup.visible = Boolean(options.graphVisible);
  shellGroup.visible = Boolean(options.shellVisible);
  mountGroup.visible = Boolean(options.mountsVisible);
  return { group, graphGroup, shellGroup, mountGroup, snapshot };
}

export function disposeSurfaceFirstDemoRig(rig) {
  if (!rig?.group) return;
  rig.group.traverse((object) => {
    object.geometry?.dispose?.();
    const material = object.material;
    if (Array.isArray(material)) {
      material.forEach((entry) => entry?.dispose?.());
    } else {
      material?.dispose?.();
    }
  });
}
