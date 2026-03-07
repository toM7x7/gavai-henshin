import * as THREE from "three";
import {
  FIT_CONTACT_PAIRS,
  VRM_BONE_ALIASES,
  VRM_PART_BONE_FALLBACKS,
  effectiveFitFor,
  effectiveVrmAnchorFor,
  normalizeAttachmentSlot,
  normalizeBoneName,
  normalizeVec3,
} from "./armor-canon.js";

const DEFAULT_SEGMENT_POSE = Object.freeze({
  chest_core: { position_x: 0.55, position_y: -0.25, position_z: 0.22, rotation_z: 0, scale_x: 1, scale_y: 1, scale_z: 1 },
  left_upperarm: { position_x: 0.22, position_y: -0.02, position_z: 0.22, rotation_z: 0.2, scale_x: 0.9, scale_y: 0.95, scale_z: 0.9 },
  right_upperarm: { position_x: 0.88, position_y: -0.02, position_z: 0.22, rotation_z: -0.2, scale_x: 0.9, scale_y: 0.95, scale_z: 0.9 },
  left_forearm: { position_x: 0.16, position_y: -0.42, position_z: 0.22, rotation_z: 0.18, scale_x: 0.88, scale_y: 0.95, scale_z: 0.88 },
  right_forearm: { position_x: 0.94, position_y: -0.42, position_z: 0.22, rotation_z: -0.18, scale_x: 0.88, scale_y: 0.95, scale_z: 0.88 },
  left_thigh: { position_x: 0.42, position_y: -0.72, position_z: 0.22, rotation_z: 0.04, scale_x: 0.95, scale_y: 1.05, scale_z: 0.95 },
  right_thigh: { position_x: 0.68, position_y: -0.72, position_z: 0.22, rotation_z: -0.04, scale_x: 0.95, scale_y: 1.05, scale_z: 0.95 },
  left_shin: { position_x: 0.42, position_y: -1.18, position_z: 0.22, rotation_z: 0.02, scale_x: 0.92, scale_y: 1.05, scale_z: 0.92 },
  right_shin: { position_x: 0.68, position_y: -1.18, position_z: 0.22, rotation_z: -0.02, scale_x: 0.92, scale_y: 1.05, scale_z: 0.92 },
});

const SEGMENT_SPECS = Object.freeze([
  { name: "right_upperarm", startJoint: "right_shoulder", endJoint: "right_elbow", radiusFactor: 0.22, radiusMin: 0.05, radiusMax: 0.22, z: 0.22 },
  { name: "right_forearm", startJoint: "right_elbow", endJoint: "right_wrist", radiusFactor: 0.22, radiusMin: 0.05, radiusMax: 0.22, z: 0.22 },
  { name: "left_upperarm", startJoint: "left_shoulder", endJoint: "left_elbow", radiusFactor: 0.22, radiusMin: 0.05, radiusMax: 0.22, z: 0.22 },
  { name: "left_forearm", startJoint: "left_elbow", endJoint: "left_wrist", radiusFactor: 0.22, radiusMin: 0.05, radiusMax: 0.22, z: 0.22 },
  { name: "right_thigh", startJoint: "right_hip", endJoint: "right_knee", radiusFactor: 0.22, radiusMin: 0.05, radiusMax: 0.22, z: 0.22 },
  { name: "right_shin", startJoint: "right_knee", endJoint: "right_ankle", radiusFactor: 0.22, radiusMin: 0.05, radiusMax: 0.22, z: 0.22 },
  { name: "left_thigh", startJoint: "left_hip", endJoint: "left_knee", radiusFactor: 0.22, radiusMin: 0.05, radiusMax: 0.22, z: 0.22 },
  { name: "left_shin", startJoint: "left_knee", endJoint: "left_ankle", radiusFactor: 0.22, radiusMin: 0.05, radiusMax: 0.22, z: 0.22 },
  { name: "chest_core", startJoint: "hips_center", endJoint: "shoulders_center", radiusFactor: 0.38, radiusMin: 0.05, radiusMax: 0.35, z: 0.22 },
]);

const TPOSE_BONE_CHAINS = Object.freeze([
  { bone: "leftUpperArm", childBone: "leftLowerArm", target: [-1, 0, 0], strength: 1.0 },
  { bone: "leftLowerArm", childBone: "leftHand", target: [-1, 0, 0], strength: 1.0 },
  { bone: "rightUpperArm", childBone: "rightLowerArm", target: [1, 0, 0], strength: 1.0 },
  { bone: "rightLowerArm", childBone: "rightHand", target: [1, 0, 0], strength: 1.0 },
  { bone: "leftUpperLeg", childBone: "leftLowerLeg", target: [0, -1, 0], strength: 0.8 },
  { bone: "leftLowerLeg", childBone: "leftFoot", target: [0, -1, 0], strength: 0.8 },
  { bone: "rightUpperLeg", childBone: "rightLowerLeg", target: [0, -1, 0], strength: 0.8 },
  { bone: "rightLowerLeg", childBone: "rightFoot", target: [0, -1, 0], strength: 0.8 },
  { bone: "spine", childBone: "chest", target: [0, 1, 0], strength: 0.6 },
  { bone: "chest", childBone: "neck", target: [0, 1, 0], strength: 0.6 },
  { bone: "neck", childBone: "head", target: [0, 1, 0], strength: 0.5 },
]);

const MIRROR_PART_PAIRS = Object.freeze([
  ["left_shoulder", "right_shoulder"],
  ["left_upperarm", "right_upperarm"],
  ["left_forearm", "right_forearm"],
  ["left_hand", "right_hand"],
  ["left_thigh", "right_thigh"],
  ["left_shin", "right_shin"],
  ["left_boot", "right_boot"],
]);

const SUMMARY_PAIR_WEIGHTS = Object.freeze({
  "chest-back": 0.35,
});

export const AUTO_FIT_CRITICAL_PARTS = Object.freeze(["chest", "left_upperarm", "right_upperarm", "left_forearm", "right_forearm"]);
export const AUTO_FIT_SCORE_MIN = 70;
export const AUTO_FIT_CRITICAL_PART_MIN = 58;

function clamp(value, low, high) { return Math.max(low, Math.min(high, value)); }
function round3(value) { return Math.round(Number(value || 0) * 1000) / 1000; }
function numberOr(value, fallback) { const n = Number(value); return Number.isFinite(n) ? n : fallback; }
function meanFinite(values, fallback = 0) { const filtered = (values || []).filter((value) => Number.isFinite(value) && value > 0); if (!filtered.length) return fallback; return filtered.reduce((sum, value) => sum + value, 0) / filtered.length; }
function midpoint3(a, b) { if (!a || !b) return null; return { x: (a.x + b.x) * 0.5, y: (a.y + b.y) * 0.5, z: (numberOr(a.z, 0.22) + numberOr(b.z, 0.22)) * 0.5 }; }
function localYAxis(rotationZ) { return { x: -Math.sin(rotationZ), y: Math.cos(rotationZ) }; }
function distance3(a, b) { if (!a || !b) return 0; return Math.hypot(a.x - b.x, a.y - b.y, numberOr(a.z, 0.22) - numberOr(b.z, 0.22)); }

function aabbGapAndPenetration(a, b) {
  const gapX = Math.max(0, Math.max(a.min.x - b.max.x, b.min.x - a.max.x));
  const gapY = Math.max(0, Math.max(a.min.y - b.max.y, b.min.y - a.max.y));
  const gapZ = Math.max(0, Math.max(a.min.z - b.max.z, b.min.z - a.max.z));
  const gap = Math.hypot(gapX, gapY, gapZ);
  const overlapX = Math.min(a.max.x, b.max.x) - Math.max(a.min.x, b.min.x);
  const overlapY = Math.min(a.max.y, b.max.y) - Math.max(a.min.y, b.min.y);
  const overlapZ = Math.min(a.max.z, b.max.z) - Math.max(a.min.z, b.min.z);
  const penetration = overlapX > 0 && overlapY > 0 && overlapZ > 0 ? Math.min(overlapX, overlapY, overlapZ) : 0;
  return { gap, penetration };
}

function fitPairScore(gap, penetration) {
  const gapPenalty = clamp(gap / 0.09, 0, 1);
  const penetrationPenalty = clamp(penetration / 0.05, 0, 1);
  return clamp(1 - gapPenalty * 0.65 - penetrationPenalty * 0.35, 0, 1);
}

function saveGatePairScore(gap, penetration) {
  const gapPenalty = clamp(gap / 0.14, 0, 1);
  const penetrationPenalty = clamp(penetration / 0.32, 0, 1);
  return clamp(1 - gapPenalty * 0.5 - penetrationPenalty * 0.5, 0, 1);
}

function pairWeight(pairName) {
  return SUMMARY_PAIR_WEIGHTS[pairName] ?? 1;
}

function cloneFit(fit) {
  return { shape: String(fit.shape || "box"), source: String(fit.source || "chest_core"), attach: String(fit.attach || "center"), offsetY: numberOr(fit.offsetY, 0), zOffset: numberOr(fit.zOffset, 0), scale: normalizeVec3(fit.scale, [1, 1, 1]), follow: normalizeVec3(fit.follow, [1, 1, 1]), minScale: normalizeVec3(fit.minScale, [0.2, 0.2, 0.2]) };
}

function cloneAnchor(anchor) {
  return { bone: String(anchor.bone || "chest"), offset: normalizeVec3(anchor.offset, [0, 0, 0]), rotation: normalizeVec3(anchor.rotation, [0, 0, 0]), scale: normalizeVec3(anchor.scale, [1, 1, 1]).map((value) => Math.max(0.01, numberOr(value, 1))) };
}

function listEnabledParts(suitspec) { return Object.entries(suitspec?.modules || {}).filter(([, module]) => module?.enabled).map(([partName]) => partName); }

function normalizeMeshMap(meshes) {
  if (meshes instanceof Map) {
    return new Map(Array.from(meshes.entries()).map(([partName, rec]) => [partName, rec?.group || rec?.mesh || rec?.object || rec]).filter(([, object]) => object && typeof object.updateMatrixWorld === "function"));
  }
  if (Array.isArray(meshes)) {
    return new Map(meshes.map((entry) => [entry?.partName || entry?.name, entry?.group || entry?.mesh || entry?.object || entry]).filter(([partName, object]) => partName && object && typeof object.updateMatrixWorld === "function"));
  }
  return new Map();
}
function createFallbackBoneResolver(vrmModel) {
  const map = new Map();
  vrmModel?.traverse?.((obj) => {
    if (!obj?.isBone || !obj.name) return;
    map.set(normalizeBoneName(obj.name), obj);
  });
  return (boneName) => {
    const aliases = VRM_BONE_ALIASES[boneName] || [boneName];
    for (const alias of aliases) {
      const found = map.get(normalizeBoneName(alias));
      if (found) return found;
    }
    return null;
  };
}

function createBoneResolver(vrmModel, options = {}) {
  if (typeof options.resolveBone === "function") return options.resolveBone;
  return createFallbackBoneResolver(vrmModel);
}

function resolveBoneForPart(resolveBone, partName, module, primaryBone) {
  const slot = normalizeAttachmentSlot(partName, module);
  const tried = new Set();
  const candidates = [primaryBone, ...(VRM_PART_BONE_FALLBACKS[slot] || [])];
  for (const candidate of candidates) {
    const key = String(candidate || "").trim();
    if (!key) continue;
    const normalized = normalizeBoneName(key);
    if (tried.has(normalized)) continue;
    tried.add(normalized);
    const bone = resolveBone(key);
    if (bone) return bone;
  }
  return null;
}

function getBoneWorldPosition(resolveBone, boneName) {
  const bone = resolveBone(boneName);
  return bone ? bone.getWorldPosition(new THREE.Vector3()) : null;
}

function collectVrmJoints(resolveBone) {
  const pick = (...names) => {
    for (const name of names) {
      const pos = getBoneWorldPosition(resolveBone, name);
      if (pos) return { x: pos.x, y: pos.y, z: pos.z };
    }
    return null;
  };
  return {
    left_shoulder: pick("leftShoulder", "leftUpperArm"),
    right_shoulder: pick("rightShoulder", "rightUpperArm"),
    left_elbow: pick("leftLowerArm"),
    right_elbow: pick("rightLowerArm"),
    left_wrist: pick("leftHand"),
    right_wrist: pick("rightHand"),
    left_hip: pick("leftUpperLeg"),
    right_hip: pick("rightUpperLeg"),
    left_knee: pick("leftLowerLeg"),
    right_knee: pick("rightLowerLeg"),
    left_ankle: pick("leftFoot"),
    right_ankle: pick("rightFoot"),
    nose: pick("head"),
  };
}

function completeUpperBodyJoints(joints, metrics) {
  const out = { ...(joints || {}) };
  const shouldersCenter = out.shoulders_center || midpoint3(out.left_shoulder, out.right_shoulder);
  if (!shouldersCenter) return out;
  out.shoulders_center = shouldersCenter;

  const shoulderWidth = distance3(out.left_shoulder, out.right_shoulder) || Math.max(numberOr(metrics.shoulderWidth, 0.32), 0.32);
  const torsoBasis = Math.max(numberOr(metrics.torsoLen, 0.62), shoulderWidth, 0.28);
  const torsoDrop = clamp(torsoBasis * 1.05, 0.28, 0.84);
  const hipHalfWidth = clamp((numberOr(metrics.hipWidth, shoulderWidth * 0.74) || shoulderWidth * 0.74) * 0.5, 0.08, 0.28);

  if (!out.hips_center) {
    if (out.left_hip && out.right_hip) {
      out.hips_center = midpoint3(out.left_hip, out.right_hip);
    } else if (out.left_hip) {
      out.hips_center = { x: out.left_hip.x + hipHalfWidth, y: out.left_hip.y, z: numberOr(out.left_hip.z, 0.22) };
    } else if (out.right_hip) {
      out.hips_center = { x: out.right_hip.x - hipHalfWidth, y: out.right_hip.y, z: numberOr(out.right_hip.z, 0.22) };
    } else {
      out.hips_center = { x: shouldersCenter.x, y: shouldersCenter.y - torsoDrop, z: numberOr(shouldersCenter.z, 0.22) - 0.02 };
    }
  }

  if (out.hips_center) {
    const hipsCenter = out.hips_center;
    if (!out.left_hip) out.left_hip = { x: hipsCenter.x - hipHalfWidth, y: hipsCenter.y, z: numberOr(hipsCenter.z, 0.22) };
    if (!out.right_hip) out.right_hip = { x: hipsCenter.x + hipHalfWidth, y: hipsCenter.y, z: numberOr(hipsCenter.z, 0.22) };
  }

  if (!out.nose) {
    out.nose = { x: shouldersCenter.x, y: shouldersCenter.y + torsoDrop * 0.58, z: numberOr(shouldersCenter.z, 0.22) + 0.02 };
  }
  return out;
}

function buildSegmentPoseFromEndpoints(spec, start, end, prev, lengthScale = 1) {
  if (!start || !end) return { ...prev };
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const dz = numberOr(end.z, spec.z) - numberOr(start.z, spec.z);
  const length = Math.hypot(dx, dy, dz) * lengthScale;
  const radius = clamp(length * spec.radiusFactor, spec.radiusMin, spec.radiusMax);
  const angle = Math.atan2(dy, dx);
  return {
    position_x: (start.x + end.x) * 0.5,
    position_y: (start.y + end.y) * 0.5,
    position_z: (numberOr(start.z, spec.z) + numberOr(end.z, spec.z)) * 0.5,
    rotation_z: angle - Math.PI / 2,
    scale_x: radius,
    scale_y: length,
    scale_z: radius,
  };
}

function buildSegmentsFromJoints(joints, lengthScale = 1) {
  const segments = { ...DEFAULT_SEGMENT_POSE };
  for (const spec of SEGMENT_SPECS) {
    const prev = DEFAULT_SEGMENT_POSE[spec.name] || { position_x: 0, position_y: 0, position_z: spec.z, rotation_z: 0, scale_x: 1, scale_y: 1, scale_z: 1 };
    segments[spec.name] = buildSegmentPoseFromEndpoints(spec, joints?.[spec.startJoint], joints?.[spec.endJoint], prev, lengthScale);
  }
  return segments;
}

function snapshotObjects(meshMap) {
  return new Map(Array.from(meshMap.entries()).map(([partName, object]) => [partName, { object, position: object.position.clone(), quaternion: object.quaternion.clone(), scale: object.scale.clone(), visible: object.visible }]));
}

function restoreObjects(snapshot) {
  for (const entry of snapshot.values()) {
    entry.object.position.copy(entry.position);
    entry.object.quaternion.copy(entry.quaternion);
    entry.object.scale.copy(entry.scale);
    entry.object.visible = entry.visible;
    entry.object.updateMatrixWorld(true);
  }
}

function applyTransformToObject(object, transform) {
  if (!object) return false;
  if (!transform) {
    object.visible = false;
    object.updateMatrixWorld(true);
    return false;
  }
  object.visible = true;
  object.position.set(transform.position_x, transform.position_y, transform.position_z);
  object.rotation.set(0, 0, transform.rotation_z);
  object.scale.set(transform.scale_x, transform.scale_y, transform.scale_z);
  object.updateMatrixWorld(true);
  return true;
}
function resolveTransform(config, segments) {
  const source = config.source;
  const base = segments[source] || null;
  if (!base) return null;

  const offset = numberOr(config.offsetY, 0);
  const attach = String(config.attach || "center");
  let anchor = 0;
  if (attach === "start") anchor = 0.5;
  if (attach === "end") anchor = -0.5;

  const axis = localYAxis(base.rotation_z);
  const along = base.scale_y * (anchor + offset);
  const fitScale = normalizeVec3(config.scale, [1, 1, 1]);
  const follow = normalizeVec3(config.follow, [1, 1, 1]);
  const minScale = normalizeVec3(config.minScale, [0.2, 0.2, 0.2]);
  const baseScaleX = Math.max(numberOr(base.scale_x, 1), 0.2);
  const baseScaleY = Math.max(numberOr(base.scale_y, 1), 0.2);
  const baseScaleZ = Math.max(numberOr(base.scale_z, 1), 0.2);

  const followScaleX = 1 + (baseScaleX - 1) * numberOr(follow[0], 1);
  const followScaleY = 1 + (baseScaleY - 1) * numberOr(follow[1], 1);
  const followScaleZ = 1 + (baseScaleZ - 1) * numberOr(follow[2], 1);

  return {
    position_x: base.position_x + axis.x * along,
    position_y: base.position_y + axis.y * along,
    position_z: base.position_z + numberOr(config.zOffset, 0),
    rotation_z: base.rotation_z,
    scale_x: Math.max(followScaleX * fitScale[0], numberOr(minScale[0], 0.2)),
    scale_y: Math.max(followScaleY * fitScale[1], numberOr(minScale[1], 0.2)),
    scale_z: Math.max(followScaleZ * fitScale[2], numberOr(minScale[2], 0.2)),
  };
}

function measureObjectWorldSize(object) {
  if (!object) return new THREE.Vector3(0.22, 0.22, 0.22);
  object.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(object);
  if (box.isEmpty()) return new THREE.Vector3(0.22, 0.22, 0.22);
  const size = box.getSize(new THREE.Vector3());
  return new THREE.Vector3(Math.max(size.x, 0.02), Math.max(size.y, 0.02), Math.max(size.z, 0.02));
}

function estimateAutoFitTargetSize(partName, metrics, fallbackSize) {
  const fb = fallbackSize || new THREE.Vector3(0.22, 0.22, 0.22);
  const target = fb.clone();
  const shoulderWidth = Math.max(numberOr(metrics.shoulderWidth, 0.44), 0.2);
  const hipWidth = Math.max(numberOr(metrics.hipWidth, shoulderWidth * 0.75), 0.16);
  const torsoLen = Math.max(numberOr(metrics.torsoLen, 0.62), 0.2);
  const headLen = Math.max(numberOr(metrics.headLen, torsoLen * 0.3), 0.12);
  const upperArmLen = Math.max(numberOr(metrics.upperArmLen, 0.36), 0.12);
  const foreArmLen = Math.max(numberOr(metrics.foreArmLen, upperArmLen * 0.92), 0.1);
  const thighLen = Math.max(numberOr(metrics.thighLen, 0.5), 0.14);
  const shinLen = Math.max(numberOr(metrics.shinLen, thighLen * 0.92), 0.14);
  const handLen = Math.max(numberOr(metrics.handLen, foreArmLen * 0.34), 0.06);
  const footLen = Math.max(numberOr(metrics.footLen, shinLen * 0.4), 0.08);

  switch (partName) {
    case "helmet":
      target.set(headLen * 0.9, headLen * 1.0, headLen * 0.92);
      break;
    case "chest":
      target.set(shoulderWidth * 0.88, torsoLen * 0.44, (shoulderWidth + hipWidth) * 0.36);
      break;
    case "back":
      target.set(shoulderWidth * 0.84, torsoLen * 0.42, (shoulderWidth + hipWidth) * 0.32);
      break;
    case "waist":
      target.set(hipWidth * 0.95, torsoLen * 0.24, hipWidth * 0.58);
      break;
    case "left_shoulder":
    case "right_shoulder":
      target.set(upperArmLen * 0.26, upperArmLen * 0.26, upperArmLen * 0.26);
      break;
    case "left_upperarm":
    case "right_upperarm":
      target.set(upperArmLen * 0.22, upperArmLen * 0.94, upperArmLen * 0.22);
      break;
    case "left_forearm":
    case "right_forearm":
      target.set(foreArmLen * 0.2, foreArmLen * 0.98, foreArmLen * 0.2);
      break;
    case "left_hand":
    case "right_hand":
      target.set(handLen * 0.62, handLen * 0.48, handLen * 0.82);
      break;
    case "left_thigh":
    case "right_thigh":
      target.set(thighLen * 0.24, thighLen * 1.0, thighLen * 0.24);
      break;
    case "left_shin":
    case "right_shin":
      target.set(shinLen * 0.2, shinLen * 1.0, shinLen * 0.2);
      break;
    case "left_boot":
    case "right_boot":
      target.set(footLen * 0.44, footLen * 0.28, footLen * 0.95);
      break;
    default:
      break;
  }
  return target;
}

function estimateVrmBodyMetrics(resolveBone) {
  const p = (name) => getBoneWorldPosition(resolveBone, name);
  const dist = (a, b, fallback = 0) => (a && b ? a.distanceTo(b) : fallback);
  const leftShoulder = p("leftShoulder") || p("leftUpperArm");
  const rightShoulder = p("rightShoulder") || p("rightUpperArm");
  const leftHip = p("leftUpperLeg");
  const rightHip = p("rightUpperLeg");
  const hips = p("hips");
  const upperChest = p("upperChest");
  const chest = p("chest");
  const neck = p("neck");
  const head = p("head");

  const shouldersCenter = leftShoulder && rightShoulder ? leftShoulder.clone().lerp(rightShoulder, 0.5) : upperChest || chest || neck || null;
  const hipsCenter = leftHip && rightHip ? leftHip.clone().lerp(rightHip, 0.5) : hips || null;
  const torsoTop = upperChest || chest || neck || shouldersCenter || null;

  const shoulderWidth = dist(leftShoulder, rightShoulder, 0.44);
  const hipWidth = dist(leftHip, rightHip, shoulderWidth * 0.75);
  const torsoLen = dist(hipsCenter, torsoTop, 0.62);
  const headLen = dist(neck, head, torsoLen * 0.3);
  const upperArmLen = meanFinite([dist(p("leftUpperArm"), p("leftLowerArm"), 0), dist(p("rightUpperArm"), p("rightLowerArm"), 0)], 0.36);
  const foreArmLen = meanFinite([dist(p("leftLowerArm"), p("leftHand"), 0), dist(p("rightLowerArm"), p("rightHand"), 0)], upperArmLen * 0.92);
  const thighLen = meanFinite([dist(p("leftUpperLeg"), p("leftLowerLeg"), 0), dist(p("rightUpperLeg"), p("rightLowerLeg"), 0)], 0.5);
  const shinLen = meanFinite([dist(p("leftLowerLeg"), p("leftFoot"), 0), dist(p("rightLowerLeg"), p("rightFoot"), 0)], thighLen * 0.92);
  const handLen = meanFinite([dist(p("leftHand"), p("leftMiddleProximal"), 0), dist(p("rightHand"), p("rightMiddleProximal"), 0)], foreArmLen * 0.34);
  const footLen = meanFinite([dist(p("leftFoot"), p("leftToes"), 0), dist(p("rightFoot"), p("rightToes"), 0)], shinLen * 0.4);

  return { shoulderWidth, hipWidth, torsoLen, torsoLenRatio: clamp(torsoLen / 0.62, 0.6, 1.6), headLen, upperArmLen, foreArmLen, thighLen, shinLen, handLen, footLen };
}
function enforceFitSymmetry(fitByPart) {
  for (const [leftPart, rightPart] of MIRROR_PART_PAIRS) {
    const leftFit = fitByPart[leftPart];
    const rightFit = fitByPart[rightPart];
    if (!leftFit || !rightFit) continue;
    const avgScale = [0, 1, 2].map((index) => round3((numberOr(leftFit.scale[index], 1) + numberOr(rightFit.scale[index], 1)) * 0.5));
    const avgOffsetY = round3((numberOr(leftFit.offsetY, 0) + numberOr(rightFit.offsetY, 0)) * 0.5);
    const avgZOffset = round3((numberOr(leftFit.zOffset, 0) + numberOr(rightFit.zOffset, 0)) * 0.5);
    leftFit.scale = [...avgScale];
    rightFit.scale = [...avgScale];
    leftFit.offsetY = avgOffsetY;
    rightFit.offsetY = avgOffsetY;
    leftFit.zOffset = avgZOffset;
    rightFit.zOffset = avgZOffset;
  }
}

function applyFitTransforms(meshMap, modules, fitByPart, segments) {
  for (const [partName, object] of meshMap.entries()) {
    const module = modules?.[partName];
    if (!module?.enabled) {
      object.visible = false;
      object.updateMatrixWorld(true);
      continue;
    }
    const fit = fitByPart[partName] || effectiveFitFor(partName, module);
    applyTransformToObject(object, resolveTransform(fit, segments));
  }
}

function calculateFitStats(meshMap) {
  const boxes = new Map();
  for (const [partName, object] of meshMap.entries()) {
    if (!object.visible) continue;
    object.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(object);
    if (!box.isEmpty()) boxes.set(partName, box);
  }

  let totalGap = 0;
  let totalPenetration = 0;
  let totalScore = 0;
  let count = 0;
  const pairs = [];

  for (const [aName, bName] of FIT_CONTACT_PAIRS) {
    const a = boxes.get(aName);
    const b = boxes.get(bName);
    if (!a || !b) continue;
    const { gap, penetration } = aabbGapAndPenetration(a, b);
    const score = fitPairScore(gap, penetration);
    totalGap += gap;
    totalPenetration += penetration;
    totalScore += score;
    count += 1;
    pairs.push({ a: aName, b: bName, pair: `${aName}-${bName}`, gap, penetration, score });
  }

  pairs.sort((left, right) => left.score - right.score);
  return { pairCount: count, meanGap: count ? totalGap / count : 0, meanPenetration: count ? totalPenetration / count : 0, score: count ? totalScore / count : 0, pairs, weakest: pairs.slice(0, 5) };
}

function refineFitCandidates(fitByPart, pairStats) {
  const worstByPart = new Map();
  for (const pair of pairStats.pairs || []) {
    for (const partName of [pair.a, pair.b]) {
      const current = worstByPart.get(partName);
      if (!current || pair.score < current.score) {
        worstByPart.set(partName, { score: pair.score, gap: pair.gap, penetration: pair.penetration, towardSign: pair.b === partName ? 1 : -1 });
      }
    }
  }

  let changed = false;
  for (const [partName, info] of worstByPart.entries()) {
    if (info.score >= 0.88) continue;
    const fit = fitByPart[partName];
    if (!fit) continue;
    const scaleAllFactor = clamp(1 + clamp(info.gap * 1.9, 0, 0.12) - clamp(info.penetration * 2.0, 0, 0.14), 0.9, 1.12);
    const scaleYFactor = clamp(1 + clamp((info.gap - info.penetration) * 1.8, -0.1, 0.1), 0.9, 1.12);
    const offsetAdjust = clamp((info.gap - info.penetration) * 0.22, -0.03, 0.03) * info.towardSign;
    fit.scale = [
      round3(clamp(numberOr(fit.scale[0], 1) * scaleAllFactor, 0.05, 3.0)),
      round3(clamp(numberOr(fit.scale[1], 1) * scaleYFactor, 0.05, 3.0)),
      round3(clamp(numberOr(fit.scale[2], 1) * scaleAllFactor, 0.05, 3.0)),
    ];
    fit.offsetY = round3(clamp(numberOr(fit.offsetY, 0) + offsetAdjust, -1.2, 1.2));
    changed = true;
  }
  return changed;
}

function buildPartScores(fitByPart, stats) {
  const scoreMap = new Map();
  for (const partName of Object.keys(fitByPart)) {
    scoreMap.set(partName, { scoreSum: 0, gapSum: 0, penetrationSum: 0, count: 0, symmetryPenalty: 0 });
  }

  for (const pair of stats.pairs || []) {
    const weight = pairWeight(pair.pair);
    const score = saveGatePairScore(pair.gap, pair.penetration);
    for (const partName of [pair.a, pair.b]) {
      const entry = scoreMap.get(partName);
      if (!entry) continue;
      entry.scoreSum += score * weight;
      entry.gapSum += pair.gap * weight;
      entry.penetrationSum += pair.penetration * weight;
      entry.count += weight;
    }
  }

  for (const [leftPart, rightPart] of MIRROR_PART_PAIRS) {
    const leftFit = fitByPart[leftPart];
    const rightFit = fitByPart[rightPart];
    if (!leftFit || !rightFit) continue;
    const diff =
      Math.abs(numberOr(leftFit.offsetY, 0) - numberOr(rightFit.offsetY, 0)) * 2.2 +
      Math.abs(numberOr(leftFit.zOffset, 0) - numberOr(rightFit.zOffset, 0)) * 1.8 +
      Math.abs(numberOr(leftFit.scale[0], 1) - numberOr(rightFit.scale[0], 1)) * 0.6 +
      Math.abs(numberOr(leftFit.scale[1], 1) - numberOr(rightFit.scale[1], 1)) * 0.8 +
      Math.abs(numberOr(leftFit.scale[2], 1) - numberOr(rightFit.scale[2], 1)) * 0.6;
    const penalty = clamp(diff, 0, 0.22);
    if (scoreMap.has(leftPart)) scoreMap.get(leftPart).symmetryPenalty = penalty;
    if (scoreMap.has(rightPart)) scoreMap.get(rightPart).symmetryPenalty = penalty;
  }

  return Array.from(scoreMap.entries())
    .map(([partName, entry]) => {
      const baseScore = entry.count ? entry.scoreSum / entry.count : 1;
      const score = clamp(baseScore - entry.symmetryPenalty, 0, 1);
      return {
        part: partName,
        score: round3(score * 100),
        gap: round3(entry.count ? entry.gapSum / entry.count : 0),
        penetration: round3(entry.count ? entry.penetrationSum / entry.count : 0),
        symmetryPenalty: round3(entry.symmetryPenalty * 100),
        critical: AUTO_FIT_CRITICAL_PARTS.includes(partName),
      };
    })
    .sort((left, right) => left.score - right.score);
}

function solveAnchorForPart(partName, module, object, resolveBone) {
  const effective = effectiveVrmAnchorFor(partName, module);
  const bone = resolveBoneForPart(resolveBone, partName, module, effective.bone);
  if (!bone) return null;
  object.updateMatrixWorld(true);
  bone.updateMatrixWorld(true);
  const bodyPos = object.getWorldPosition(new THREE.Vector3());
  const bodyQuat = object.getWorldQuaternion(new THREE.Quaternion());
  const bonePos = bone.getWorldPosition(new THREE.Vector3());
  const boneQuat = bone.getWorldQuaternion(new THREE.Quaternion());
  const invBoneQuat = boneQuat.clone().invert();
  const localOffset = bodyPos.sub(bonePos).applyQuaternion(invBoneQuat);
  const localQuat = invBoneQuat.multiply(bodyQuat).normalize();
  const euler = new THREE.Euler().setFromQuaternion(localQuat, "XYZ");
  return cloneAnchor({
    bone: String(effective.bone || "chest"),
    offset: [round3(localOffset.x), round3(localOffset.y), round3(localOffset.z)],
    rotation: [round3(THREE.MathUtils.radToDeg(euler.x)), round3(THREE.MathUtils.radToDeg(euler.y)), round3(THREE.MathUtils.radToDeg(euler.z))],
    scale: effective.scale,
  });
}

function rotateBoneChainTowardWorldDir(resolveBone, boneName, childBoneName, targetDirArr, strength = 1) {
  const bone = resolveBone(boneName);
  const childBone = resolveBone(childBoneName);
  if (!bone || !childBone) return false;

  const bonePos = bone.getWorldPosition(new THREE.Vector3());
  const childPos = childBone.getWorldPosition(new THREE.Vector3());
  const currentDir = childPos.sub(bonePos);
  if (!Number.isFinite(currentDir.lengthSq()) || currentDir.lengthSq() < 1e-8) return false;
  currentDir.normalize();

  const targetDir = new THREE.Vector3(numberOr(targetDirArr?.[0], 0), numberOr(targetDirArr?.[1], 0), numberOr(targetDirArr?.[2], 0));
  if (!Number.isFinite(targetDir.lengthSq()) || targetDir.lengthSq() < 1e-8) return false;
  targetDir.normalize();

  const deltaWorld = new THREE.Quaternion().setFromUnitVectors(currentDir, targetDir);
  const parentWorldQuat = bone.parent ? bone.parent.getWorldQuaternion(new THREE.Quaternion()) : new THREE.Quaternion();
  const boneWorldQuat = bone.getWorldQuaternion(new THREE.Quaternion());
  const desiredWorldQuat = deltaWorld.multiply(boneWorldQuat);
  const desiredLocalQuat = parentWorldQuat.clone().invert().multiply(desiredWorldQuat);
  bone.quaternion.slerp(desiredLocalQuat, clamp(strength, 0, 1));
  bone.updateMatrixWorld(true);
  return true;
}

export function applyApproximateVrmTPose({ vrmModel, options = {} }) {
  if (!vrmModel) return { appliedChains: 0, attemptedChains: TPOSE_BONE_CHAINS.length };
  vrmModel.updateMatrixWorld(true);
  const resolveBone = createBoneResolver(vrmModel, options);
  let appliedChains = 0;
  for (const chain of TPOSE_BONE_CHAINS) {
    if (rotateBoneChainTowardWorldDir(resolveBone, chain.bone, chain.childBone, chain.target, chain.strength)) appliedChains += 1;
  }
  vrmModel.updateMatrixWorld(true);
  return { appliedChains, attemptedChains: TPOSE_BONE_CHAINS.length };
}
export function applyAutoFitResultToSuitSpec(suitspec, result) {
  const modules = suitspec?.modules || {};
  for (const [partName, fit] of Object.entries(result?.fitByPart || {})) {
    const module = modules[partName];
    if (!module) continue;
    module.fit = cloneFit(fit);
  }
  for (const [partName, anchor] of Object.entries(result?.anchorByPart || {})) {
    const module = modules[partName];
    if (!module) continue;
    module.attachment_slot = normalizeAttachmentSlot(partName, module);
    module.vrm_anchor = cloneAnchor(anchor);
  }
  return suitspec;
}

export function formatAutoFitSummary(summary) {
  if (!summary) return "Auto-fit: unavailable";
  const parts = [
    `FitScore ${numberOr(summary.fitScore, 0).toFixed(1)}`,
    `Anchors ${Array.isArray(summary.missingAnchors) ? summary.missingAnchors.length : 0} missing`,
    summary.canSave ? "Ready to save" : "Preview only",
  ];
  if (Array.isArray(summary.reasons) && summary.reasons.length) {
    parts.push(summary.reasons.join(" | "));
  }
  return parts.join(" | ");
}

export function fitArmorToVrm({ vrmModel, meshes, suitspec, options = {} }) {
  if (!vrmModel) throw new Error("VRM model is required.");
  if (!suitspec?.modules || typeof suitspec.modules !== "object") throw new Error("SuitSpec.modules is required.");

  const meshMap = normalizeMeshMap(meshes);
  const enabledParts = listEnabledParts(suitspec).filter((partName) => meshMap.has(partName));
  if (!enabledParts.length) throw new Error("No enabled armor meshes available for auto-fit.");

  const snapshot = snapshotObjects(meshMap);
  const resolveBone = createBoneResolver(vrmModel, options);
  const forceTPose = options.forceTPose !== false;
  const tPose = forceTPose ? applyApproximateVrmTPose({ vrmModel, options: { resolveBone } }) : { appliedChains: 0, attemptedChains: TPOSE_BONE_CHAINS.length };
  const metrics = estimateVrmBodyMetrics(resolveBone);
  const joints = completeUpperBodyJoints(collectVrmJoints(resolveBone), metrics);
  const segments = buildSegmentsFromJoints(joints, 1);
  const fitByPart = {};
  let stats = { pairCount: 0, meanGap: 0, meanPenetration: 0, score: 0, pairs: [], weakest: [] };

  try {
    for (const partName of enabledParts) {
      const module = suitspec.modules[partName];
      const object = meshMap.get(partName);
      const effective = cloneFit(effectiveFitFor(partName, module));
      applyTransformToObject(object, resolveTransform(effective, segments));
      const currentSize = measureObjectWorldSize(object);
      const targetSize = estimateAutoFitTargetSize(partName, metrics, currentSize);
      const ratioX = clamp(targetSize.x / Math.max(currentSize.x, 0.001), 0.65, 1.55);
      const ratioY = clamp(targetSize.y / Math.max(currentSize.y, 0.001), 0.65, 1.55);
      const ratioZ = clamp(targetSize.z / Math.max(currentSize.z, 0.001), 0.65, 1.55);
      fitByPart[partName] = cloneFit({
        ...effective,
        offsetY:
          partName === "chest" || partName === "back"
            ? round3(numberOr(effective.offsetY, 0) + clamp((numberOr(metrics.torsoLenRatio, 1) - 1) * 0.05, -0.08, 0.08))
            : partName === "waist"
              ? round3(numberOr(effective.offsetY, 0) + clamp((1 - numberOr(metrics.torsoLenRatio, 1)) * 0.04, -0.07, 0.07))
              : round3(numberOr(effective.offsetY, 0)),
        scale: [
          round3(clamp(numberOr(effective.scale[0], 1) * ratioX, 0.05, 3.0)),
          round3(clamp(numberOr(effective.scale[1], 1) * ratioY, 0.05, 3.0)),
          round3(clamp(numberOr(effective.scale[2], 1) * ratioZ, 0.05, 3.0)),
        ],
      });
    }

    enforceFitSymmetry(fitByPart);
    for (let pass = 0; pass < numberOr(options.refinePasses, 2); pass += 1) {
      applyFitTransforms(meshMap, suitspec.modules, fitByPart, segments);
      stats = calculateFitStats(meshMap);
      if (!refineFitCandidates(fitByPart, stats)) break;
      enforceFitSymmetry(fitByPart);
    }

    applyFitTransforms(meshMap, suitspec.modules, fitByPart, segments);
    stats = calculateFitStats(meshMap);

    const anchorByPart = {};
    const missingAnchors = [];
    for (const partName of enabledParts) {
      const module = { ...suitspec.modules[partName], fit: fitByPart[partName] };
      const object = meshMap.get(partName);
      const anchor = solveAnchorForPart(partName, module, object, resolveBone);
      if (!anchor) {
        missingAnchors.push(partName);
        continue;
      }
      anchorByPart[partName] = anchor;
    }

    const weakParts = buildPartScores(fitByPart, stats);
    const reasons = [];
    const weightedScore = (() => {
      let scoreSum = 0;
      let weightSum = 0;
      for (const pair of stats.pairs || []) {
        const weight = pairWeight(pair.pair);
        scoreSum += saveGatePairScore(pair.gap, pair.penetration) * weight;
        weightSum += weight;
      }
      return weightSum > 0 ? scoreSum / weightSum : 0;
    })();
    const fitScore = round3(weightedScore * 100);
    if (missingAnchors.length) reasons.push(`Missing anchors: ${missingAnchors.join(", ")}`);
    if (fitScore < AUTO_FIT_SCORE_MIN) reasons.push(`FitScore ${fitScore.toFixed(1)} < ${AUTO_FIT_SCORE_MIN}`);
    const failedCriticalParts = weakParts.filter((part) => part.critical && numberOr(part.score, 0) < AUTO_FIT_CRITICAL_PART_MIN);
    if (failedCriticalParts.length) {
      reasons.push(`Critical parts below threshold: ${failedCriticalParts.map((part) => `${part.part}=${part.score.toFixed(1)}`).join(", ")}`);
    }

    return {
      fitByPart,
      anchorByPart,
      metrics: Object.fromEntries(Object.entries(metrics).map(([key, value]) => [key, round3(value)])),
      summary: {
        fitScore,
        weakParts: weakParts.slice(0, 8),
        missingAnchors,
        canSave: reasons.length === 0,
        reasons,
        pairCount: stats.pairCount,
        meanGap: round3(stats.meanGap),
        meanPenetration: round3(stats.meanPenetration),
        tPoseChainsApplied: tPose.appliedChains,
        tPoseChainsAttempted: tPose.attemptedChains,
      },
    };
  } finally {
    restoreObjects(snapshot);
  }
}
