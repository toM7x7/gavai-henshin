import * as THREE from "three";
import { VRM_BONE_ALIASES, normalizeBoneName } from "./armor-canon.js";

export const CANONICAL_JOINT_ORDER = Object.freeze([
  "nose",
  "neck",
  "head",
  "left_shoulder",
  "right_shoulder",
  "left_elbow",
  "right_elbow",
  "left_wrist",
  "right_wrist",
  "left_hip",
  "right_hip",
  "left_knee",
  "right_knee",
  "left_ankle",
  "right_ankle",
  "left_toes",
  "right_toes",
  "left_middle_proximal",
  "right_middle_proximal",
  "shoulders_center",
  "hips_center",
]);

export const RELIABLE_JOINT_NAMES = Object.freeze([
  "nose",
  "left_shoulder",
  "right_shoulder",
  "left_elbow",
  "right_elbow",
  "left_wrist",
  "right_wrist",
  "left_hip",
  "right_hip",
  "left_knee",
  "right_knee",
  "left_ankle",
  "right_ankle",
]);

export const POSE_LANDMARK_IDX = Object.freeze({
  NOSE: 0,
  LEFT_SHOULDER: 11,
  RIGHT_SHOULDER: 12,
  LEFT_ELBOW: 13,
  RIGHT_ELBOW: 14,
  LEFT_WRIST: 15,
  RIGHT_WRIST: 16,
  LEFT_HIP: 23,
  RIGHT_HIP: 24,
  LEFT_KNEE: 25,
  RIGHT_KNEE: 26,
  LEFT_ANKLE: 27,
  RIGHT_ANKLE: 28,
});

const CANONICAL_BONE_CANDIDATES = Object.freeze({
  hips: ["hips", "pelvis"],
  spine: ["spine"],
  chest: ["upperChest", "chest", "spine"],
  neck: ["neck", "upperChest", "chest"],
  head: ["head", "neck"],
  left_shoulder: ["leftShoulder", "leftUpperArm"],
  right_shoulder: ["rightShoulder", "rightUpperArm"],
  left_elbow: ["leftLowerArm"],
  right_elbow: ["rightLowerArm"],
  left_wrist: ["leftHand"],
  right_wrist: ["rightHand"],
  left_hip: ["leftUpperLeg"],
  right_hip: ["rightUpperLeg"],
  left_knee: ["leftLowerLeg"],
  right_knee: ["rightLowerLeg"],
  left_ankle: ["leftFoot"],
  right_ankle: ["rightFoot"],
  left_toes: ["leftToes", "leftToeBase", "leftToesEnd"],
  right_toes: ["rightToes", "rightToeBase", "rightToesEnd"],
  left_middle_proximal: ["leftMiddleProximal", "leftMiddle1", "leftIndexProximal"],
  right_middle_proximal: ["rightMiddleProximal", "rightMiddle1", "rightIndexProximal"],
});

const GENERIC_BONE_ALIASES = Object.freeze({
  leftToes: ["lefttoes", "lefttoebase", "l_toe", "toe_l", "lefttoesend"],
  rightToes: ["righttoes", "righttoebase", "r_toe", "toe_r", "righttoesend"],
  leftMiddleProximal: ["leftmiddleproximal", "leftmiddle1", "leftindexproximal"],
  rightMiddleProximal: ["rightmiddleproximal", "rightmiddle1", "rightindexproximal"],
});

const QUALITY_JOINT_WEIGHTS = Object.freeze({
  left_shoulder: 1.2,
  right_shoulder: 1.2,
  left_elbow: 1.0,
  right_elbow: 1.0,
  left_wrist: 0.9,
  right_wrist: 0.9,
  left_hip: 1.2,
  right_hip: 1.2,
  left_knee: 0.9,
  right_knee: 0.9,
  left_ankle: 0.8,
  right_ankle: 0.8,
  nose: 0.6,
});

function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
}

function numberOr(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function midpoint3(a, b) {
  if (!a || !b) return null;
  return {
    x: (a.x + b.x) * 0.5,
    y: (a.y + b.y) * 0.5,
    z: (numberOr(a.z, 0.22) + numberOr(b.z, 0.22)) * 0.5,
  };
}

function lerpPoint3(a, b, t = 0.5) {
  if (a && b) {
    const alpha = clamp(numberOr(t, 0.5), 0, 1);
    return {
      x: a.x + (b.x - a.x) * alpha,
      y: a.y + (b.y - a.y) * alpha,
      z: numberOr(a.z, 0.22) + (numberOr(b.z, 0.22) - numberOr(a.z, 0.22)) * alpha,
    };
  }
  return a || b || null;
}

function socketPoint(primary, secondary, bias = 0.5) {
  return lerpPoint3(primary, secondary, bias);
}

function distance3(a, b) {
  if (!a || !b) return 0;
  return Math.hypot(
    a.x - b.x,
    a.y - b.y,
    numberOr(a.z, 0.22) - numberOr(b.z, 0.22)
  );
}

function meanFinite(values, fallback = 0) {
  const filtered = (values || []).filter((value) => Number.isFinite(value) && value > 0);
  if (!filtered.length) return fallback;
  return filtered.reduce((sum, value) => sum + value, 0) / filtered.length;
}

function normToWorld(x01, y01, mirror = true) {
  const xNorm = mirror ? 1 - x01 : x01;
  return { x: xNorm * 2 - 1, y: -(y01 * 2 - 1) };
}

function normToWorld3(x01, y01, zRaw = 0, mirror = true) {
  const p2 = normToWorld(x01, y01, mirror);
  return {
    x: p2.x,
    y: p2.y,
    z: clamp(numberOr(zRaw, 0), -1.2, 1.2) * 0.45 + 0.22,
  };
}

function isFinitePoint(point) {
  return Boolean(
    point &&
      Number.isFinite(point.x) &&
      Number.isFinite(point.y) &&
      Number.isFinite(numberOr(point.z, 0.22))
  );
}

function normalizePoint(point) {
  if (!point) return null;
  if (Array.isArray(point) && point.length >= 2) {
    return {
      x: numberOr(point[0], 0),
      y: numberOr(point[1], 0),
      z: numberOr(point[2], 0.22),
    };
  }
  if (point.position && typeof point.position === "object") {
    return normalizePoint(point.position);
  }
  if (Number.isFinite(point.x) && Number.isFinite(point.y)) {
    return {
      x: numberOr(point.x, 0),
      y: numberOr(point.y, 0),
      z: numberOr(point.z, 0.22),
    };
  }
  return null;
}

function isReliableLandmark(landmark, minVisibility, minPresence) {
  if (!landmark) return false;
  if (!Number.isFinite(landmark.x) || !Number.isFinite(landmark.y)) return false;
  if (Number.isFinite(landmark.visibility) && landmark.visibility < minVisibility) return false;
  if (Number.isFinite(landmark.presence) && landmark.presence < minPresence) return false;
  return true;
}

function resolveBonePosition(boneLike) {
  if (!boneLike) return null;
  if (typeof boneLike.getWorldPosition === "function") {
    const target = boneLike.getWorldPosition(new THREE.Vector3());
    return normalizePoint(target);
  }
  const direct = normalizePoint(boneLike);
  if (direct) return direct;
  return null;
}

function aliasesForBoneName(boneName, extraAliases = {}) {
  return [
    ...(VRM_BONE_ALIASES[boneName] || []),
    ...(GENERIC_BONE_ALIASES[boneName] || []),
    ...(extraAliases[boneName] || []),
    boneName,
  ];
}

export function createNamedBoneResolver(namedBones, options = {}) {
  const entries =
    namedBones instanceof Map
      ? Array.from(namedBones.entries())
      : Object.entries(namedBones || {});
  const lookup = new Map();
  for (const [name, boneLike] of entries) {
    const key = normalizeBoneName(name);
    if (!key || lookup.has(key)) continue;
    lookup.set(key, boneLike);
  }
  const extraAliases = options.extraAliases || {};
  return (boneName) => {
    for (const alias of aliasesForBoneName(boneName, extraAliases)) {
      const found = lookup.get(normalizeBoneName(alias));
      if (found) return found;
    }
    return null;
  };
}

export function inferCanonicalJointsFromBoneResolver(resolveBone, options = {}) {
  const pick = (...boneNames) => {
    for (const boneName of boneNames) {
      const point = resolveBonePosition(resolveBone?.(boneName));
      if (point) return point;
    }
    return null;
  };

  const preferLimbRoots = options.preferLimbRoots === true;
  const shoulderSocketBias = clamp(numberOr(options.shoulderSocketBias, preferLimbRoots ? 0.72 : 0.46), 0.05, 0.95);
  const joints = {};
  const hips = pick("hips", "pelvis");
  const spine = pick("spine");
  const chest = pick("upperChest", "chest", "spine");
  const neck = pick("neck", "upperChest", "chest");
  const head = pick("head", "neck");
  const leftShoulderBone = pick("leftShoulder");
  const rightShoulderBone = pick("rightShoulder");
  const leftUpperArmBone = pick("leftUpperArm");
  const rightUpperArmBone = pick("rightUpperArm");
  const leftUpperLegBone = pick("leftUpperLeg");
  const rightUpperLegBone = pick("rightUpperLeg");

  joints.hips = hips;
  joints.spine = spine;
  joints.chest = chest;
  joints.neck = neck;
  joints.head = head;
  joints.left_shoulder = socketPoint(leftShoulderBone, leftUpperArmBone, shoulderSocketBias);
  joints.right_shoulder = socketPoint(rightShoulderBone, rightUpperArmBone, shoulderSocketBias);
  joints.left_elbow = pick("leftLowerArm");
  joints.right_elbow = pick("rightLowerArm");
  joints.left_wrist = pick("leftHand");
  joints.right_wrist = pick("rightHand");
  joints.left_hip = leftUpperLegBone || hips || null;
  joints.right_hip = rightUpperLegBone || hips || null;
  joints.left_knee = pick("leftLowerLeg");
  joints.right_knee = pick("rightLowerLeg");
  joints.left_ankle = pick("leftFoot");
  joints.right_ankle = pick("rightFoot");
  joints.left_toes = pick("leftToes", "leftToeBase", "leftToesEnd");
  joints.right_toes = pick("rightToes", "rightToeBase", "rightToesEnd");
  joints.left_middle_proximal = pick("leftMiddleProximal", "leftMiddle1", "leftIndexProximal");
  joints.right_middle_proximal = pick("rightMiddleProximal", "rightMiddle1", "rightIndexProximal");
  joints.shoulders_center = midpoint3(joints.left_shoulder, joints.right_shoulder);
  joints.hips_center = midpoint3(joints.left_hip, joints.right_hip) || hips || null;

  for (const [jointName, point] of Object.entries(joints)) {
    if (!point) delete joints[jointName];
  }
  return joints;
}

export function inferCanonicalJointsFromNamedBones(namedBones, options = {}) {
  return inferCanonicalJointsFromBoneResolver(createNamedBoneResolver(namedBones, options), options);
}

export function inferCanonicalJointsFromPoseLandmarks(landmarks, options = {}) {
  const minVisibility = numberOr(options.minVisibility, 0.52);
  const minPresence = numberOr(options.minPresence, 0.35);
  const mirror = options.mirror !== false;
  const pick = (index) => landmarks?.[index] || null;
  const joints = {};

  const nose = pick(POSE_LANDMARK_IDX.NOSE);
  const leftShoulder = pick(POSE_LANDMARK_IDX.LEFT_SHOULDER);
  const rightShoulder = pick(POSE_LANDMARK_IDX.RIGHT_SHOULDER);
  const leftElbow = pick(POSE_LANDMARK_IDX.LEFT_ELBOW);
  const rightElbow = pick(POSE_LANDMARK_IDX.RIGHT_ELBOW);
  const leftWrist = pick(POSE_LANDMARK_IDX.LEFT_WRIST);
  const rightWrist = pick(POSE_LANDMARK_IDX.RIGHT_WRIST);
  const leftHip = pick(POSE_LANDMARK_IDX.LEFT_HIP);
  const rightHip = pick(POSE_LANDMARK_IDX.RIGHT_HIP);
  const leftKnee = pick(POSE_LANDMARK_IDX.LEFT_KNEE);
  const rightKnee = pick(POSE_LANDMARK_IDX.RIGHT_KNEE);
  const leftAnkle = pick(POSE_LANDMARK_IDX.LEFT_ANKLE);
  const rightAnkle = pick(POSE_LANDMARK_IDX.RIGHT_ANKLE);

  if (isReliableLandmark(nose, minVisibility, minPresence)) joints.nose = normToWorld3(nose.x, nose.y, nose.z, mirror);
  if (isReliableLandmark(leftShoulder, minVisibility, minPresence)) joints.left_shoulder = normToWorld3(leftShoulder.x, leftShoulder.y, leftShoulder.z, mirror);
  if (isReliableLandmark(rightShoulder, minVisibility, minPresence)) joints.right_shoulder = normToWorld3(rightShoulder.x, rightShoulder.y, rightShoulder.z, mirror);
  if (isReliableLandmark(leftElbow, minVisibility, minPresence)) joints.left_elbow = normToWorld3(leftElbow.x, leftElbow.y, leftElbow.z, mirror);
  if (isReliableLandmark(rightElbow, minVisibility, minPresence)) joints.right_elbow = normToWorld3(rightElbow.x, rightElbow.y, rightElbow.z, mirror);
  if (isReliableLandmark(leftWrist, minVisibility, minPresence)) joints.left_wrist = normToWorld3(leftWrist.x, leftWrist.y, leftWrist.z, mirror);
  if (isReliableLandmark(rightWrist, minVisibility, minPresence)) joints.right_wrist = normToWorld3(rightWrist.x, rightWrist.y, rightWrist.z, mirror);
  if (isReliableLandmark(leftHip, minVisibility, minPresence)) joints.left_hip = normToWorld3(leftHip.x, leftHip.y, leftHip.z, mirror);
  if (isReliableLandmark(rightHip, minVisibility, minPresence)) joints.right_hip = normToWorld3(rightHip.x, rightHip.y, rightHip.z, mirror);
  if (isReliableLandmark(leftKnee, minVisibility, minPresence)) joints.left_knee = normToWorld3(leftKnee.x, leftKnee.y, leftKnee.z, mirror);
  if (isReliableLandmark(rightKnee, minVisibility, minPresence)) joints.right_knee = normToWorld3(rightKnee.x, rightKnee.y, rightKnee.z, mirror);
  if (isReliableLandmark(leftAnkle, minVisibility, minPresence)) joints.left_ankle = normToWorld3(leftAnkle.x, leftAnkle.y, leftAnkle.z, mirror);
  if (isReliableLandmark(rightAnkle, minVisibility, minPresence)) joints.right_ankle = normToWorld3(rightAnkle.x, rightAnkle.y, rightAnkle.z, mirror);

  const shouldersCenter = midpoint3(joints.left_shoulder, joints.right_shoulder);
  if (shouldersCenter) joints.shoulders_center = shouldersCenter;
  const hipsCenter = midpoint3(joints.left_hip, joints.right_hip);
  if (hipsCenter) joints.hips_center = hipsCenter;
  if (!joints.nose && shouldersCenter) {
    joints.nose = {
      x: shouldersCenter.x,
      y: shouldersCenter.y + 0.28,
      z: shouldersCenter.z + 0.02,
    };
  }
  return joints;
}

export function estimateBodyScaleFromJoints(joints) {
  const measures = [
    distance3(joints.left_shoulder, joints.right_shoulder),
    distance3(joints.left_hip, joints.right_hip),
    distance3(joints.shoulders_center, joints.hips_center),
  ].filter((value) => Number.isFinite(value) && value > 0.05);
  if (!measures.length) return 0;
  return measures.reduce((sum, value) => sum + value, 0) / measures.length;
}

export function estimateBodyMetricsFromJoints(joints, options = {}) {
  const out = { ...(joints || {}) };
  const shouldersCenter = out.shoulders_center || midpoint3(out.left_shoulder, out.right_shoulder);
  const hipsCenter = out.hips_center || midpoint3(out.left_hip, out.right_hip) || out.hips || null;
  const torsoTop = out.chest || out.neck || shouldersCenter || null;

  const rawShoulderWidth = distance3(out.left_shoulder, out.right_shoulder);
  const rawHipWidth = distance3(out.left_hip, out.right_hip);
  const torsoLen = distance3(hipsCenter, torsoTop) || numberOr(options.torsoLenFallback, 0.62);
  const headLen = distance3(out.neck, out.head || out.nose) || torsoLen * 0.3;
  const upperArmLen = meanFinite(
    [distance3(out.left_shoulder, out.left_elbow), distance3(out.right_shoulder, out.right_elbow)],
    0.36
  );
  const foreArmLen = meanFinite(
    [distance3(out.left_elbow, out.left_wrist), distance3(out.right_elbow, out.right_wrist)],
    upperArmLen * 0.92
  );
  const thighLen = meanFinite(
    [distance3(out.left_hip, out.left_knee), distance3(out.right_hip, out.right_knee)],
    0.5
  );
  const shinLen = meanFinite(
    [distance3(out.left_knee, out.left_ankle), distance3(out.right_knee, out.right_ankle)],
    thighLen * 0.92
  );
  const handLen = meanFinite(
    [distance3(out.left_wrist, out.left_middle_proximal), distance3(out.right_wrist, out.right_middle_proximal)],
    foreArmLen * 0.34
  );
  const footLen = meanFinite(
    [distance3(out.left_ankle, out.left_toes), distance3(out.right_ankle, out.right_toes)],
    shinLen * 0.4
  );
  const shoulderWidth = Math.max(
    rawShoulderWidth,
    rawHipWidth * 0.82,
    upperArmLen * 0.42,
    numberOr(options.shoulderWidthFallback, 0.44)
  );
  const hipWidth = Math.max(rawHipWidth, shoulderWidth * 0.68, numberOr(options.hipWidthFallback, shoulderWidth * 0.75));
  const torsoWidth = clamp(Math.max(shoulderWidth * 0.94, hipWidth * 1.02), 0.16, 0.9);
  const torsoDepth = clamp(Math.max(torsoWidth * 0.46, torsoLen * 0.16), 0.08, 0.4);
  const upperArmWidth = clamp(Math.max(shoulderWidth * 0.34, upperArmLen * 0.22), 0.045, 0.22);
  const foreArmWidth = clamp(Math.max(upperArmWidth * 0.82, foreArmLen * 0.2), 0.04, 0.18);
  const thighWidth = clamp(Math.max(hipWidth * 0.32, thighLen * 0.18), 0.06, 0.24);
  const shinWidth = clamp(Math.max(thighWidth * 0.82, shinLen * 0.14), 0.05, 0.2);
  const handWidth = clamp(Math.max(foreArmWidth * 0.72, handLen * 0.78), 0.05, 0.18);
  const footWidth = clamp(Math.max(shinWidth * 0.74, footLen * 0.32), 0.06, 0.2);
  const footHeight = clamp(Math.max(footLen * 0.24, shinWidth * 0.36), 0.04, 0.16);

  return {
    shoulderWidth,
    hipWidth,
    torsoLen,
    torsoLenRatio: clamp(torsoLen / 0.62, 0.6, 1.6),
    headLen,
    upperArmLen,
    foreArmLen,
    thighLen,
    shinLen,
    handLen,
    footLen,
    torsoWidth,
    torsoDepth,
    upperArmWidth,
    foreArmWidth,
    thighWidth,
    shinWidth,
    handWidth,
    footWidth,
    footHeight,
  };
}

export function completeCanonicalJoints(joints, metrics, options = {}) {
  const out = { ...(joints || {}) };
  const shouldersCenter = out.shoulders_center || midpoint3(out.left_shoulder, out.right_shoulder);
  if (!shouldersCenter) return out;
  out.shoulders_center = shouldersCenter;

  const shoulderWidth =
    distance3(out.left_shoulder, out.right_shoulder) ||
    Math.max(numberOr(metrics?.shoulderWidth, 0.32), numberOr(options.fallbackBodyScale, 0.32), 0.32);
  const torsoBasis = Math.max(
    numberOr(metrics?.torsoLen, 0.62),
    numberOr(options.fallbackBodyScale, 0),
    shoulderWidth,
    0.28
  );
  const torsoDropRatio = numberOr(options.syntheticTorsoDropRatio, 1.05);
  const hipWidthRatio = numberOr(options.syntheticHipWidthRatio, 0.74);
  const torsoDrop = clamp(torsoBasis * torsoDropRatio, 0.26, 0.84);
  const hipHalfWidth = clamp(
    (numberOr(metrics?.hipWidth, shoulderWidth * hipWidthRatio) || shoulderWidth * hipWidthRatio) * 0.5,
    0.08,
    0.28
  );

  if (!out.hips_center) {
    if (out.left_hip && out.right_hip) {
      out.hips_center = midpoint3(out.left_hip, out.right_hip);
    } else if (out.left_hip) {
      out.hips_center = { x: out.left_hip.x + hipHalfWidth, y: out.left_hip.y, z: numberOr(out.left_hip.z, 0.22) };
    } else if (out.right_hip) {
      out.hips_center = { x: out.right_hip.x - hipHalfWidth, y: out.right_hip.y, z: numberOr(out.right_hip.z, 0.22) };
    } else {
      out.hips_center = {
        x: shouldersCenter.x,
        y: shouldersCenter.y - torsoDrop,
        z: numberOr(shouldersCenter.z, 0.22) - 0.02,
      };
    }
  }

  if (out.hips_center) {
    const hipsCenter = out.hips_center;
    if (!out.left_hip) out.left_hip = { x: hipsCenter.x - hipHalfWidth, y: hipsCenter.y, z: numberOr(hipsCenter.z, 0.22) };
    if (!out.right_hip) out.right_hip = { x: hipsCenter.x + hipHalfWidth, y: hipsCenter.y, z: numberOr(hipsCenter.z, 0.22) };
  }

  if (!out.nose) {
    out.nose = {
      x: shouldersCenter.x,
      y: shouldersCenter.y + torsoDrop * 0.58,
      z: numberOr(shouldersCenter.z, 0.22) + 0.02,
    };
  }
  if (!out.head && out.nose) {
    out.head = { x: out.nose.x, y: out.nose.y, z: numberOr(out.nose.z, 0.24) };
  }
  if (!out.neck) {
    out.neck = {
      x: shouldersCenter.x,
      y: shouldersCenter.y + Math.min(torsoDrop * 0.14, 0.12),
      z: numberOr(shouldersCenter.z, 0.22) + 0.01,
    };
  }
  return out;
}

export function countReliableJoints(joints, jointNames = RELIABLE_JOINT_NAMES) {
  let count = 0;
  for (const jointName of jointNames) {
    if (isFinitePoint(joints?.[jointName])) count += 1;
  }
  return count;
}

export function estimateInferenceQuality(joints) {
  let score = 0;
  let weightSum = 0;
  for (const [jointName, weight] of Object.entries(QUALITY_JOINT_WEIGHTS)) {
    weightSum += weight;
    if (isFinitePoint(joints?.[jointName])) score += weight;
  }
  const bilateralPairs = [
    ["left_shoulder", "right_shoulder"],
    ["left_hip", "right_hip"],
    ["left_elbow", "right_elbow"],
    ["left_wrist", "right_wrist"],
    ["left_knee", "right_knee"],
    ["left_ankle", "right_ankle"],
  ];
  let bilateralScore = 0;
  for (const [left, right] of bilateralPairs) {
    if (isFinitePoint(joints?.[left]) && isFinitePoint(joints?.[right])) bilateralScore += 1;
  }
  const bilateralRatio = bilateralPairs.length ? bilateralScore / bilateralPairs.length : 0;
  const coverage = weightSum > 0 ? score / weightSum : 0;
  const qualityScore = clamp(coverage * 0.8 + bilateralRatio * 0.2, 0, 1);
  const qualityLabel =
    qualityScore >= 0.82 ? "good" : qualityScore >= 0.62 ? "fair" : qualityScore >= 0.42 ? "upper" : "low";
  return { qualityScore, qualityLabel, coverage, bilateralRatio };
}

export function deriveBodyShapeProfile(metrics = {}) {
  const shoulderWidth = Math.max(numberOr(metrics.shoulderWidth, 0.44), 0.2);
  const hipWidth = Math.max(numberOr(metrics.hipWidth, shoulderWidth * 0.75), 0.16);
  const torsoLen = Math.max(numberOr(metrics.torsoLen, 0.62), 0.2);
  const torsoWidth = Math.max(numberOr(metrics.torsoWidth, shoulderWidth * 0.94), 0.16);
  const torsoDepth = Math.max(numberOr(metrics.torsoDepth, torsoWidth * 0.46), 0.08);
  const upperArmLen = Math.max(numberOr(metrics.upperArmLen, 0.36), 0.12);
  const upperArmWidth = Math.max(numberOr(metrics.upperArmWidth, upperArmLen * 0.22), 0.045);
  const foreArmLen = Math.max(numberOr(metrics.foreArmLen, upperArmLen * 0.92), 0.1);
  const foreArmWidth = Math.max(numberOr(metrics.foreArmWidth, foreArmLen * 0.2), 0.04);
  const thighLen = Math.max(numberOr(metrics.thighLen, 0.5), 0.14);
  const thighWidth = Math.max(numberOr(metrics.thighWidth, thighLen * 0.18), 0.06);
  const shinLen = Math.max(numberOr(metrics.shinLen, thighLen * 0.92), 0.14);
  const shinWidth = Math.max(numberOr(metrics.shinWidth, shinLen * 0.14), 0.05);
  const handLen = Math.max(numberOr(metrics.handLen, foreArmLen * 0.34), 0.06);
  const handWidth = Math.max(numberOr(metrics.handWidth, handLen * 0.78), 0.05);
  const footLen = Math.max(numberOr(metrics.footLen, shinLen * 0.4), 0.08);
  const footWidth = Math.max(numberOr(metrics.footWidth, footLen * 0.32), 0.06);

  const shoulderToHipRatio = clamp(shoulderWidth / hipWidth, 0.72, 1.65);
  const torsoWidthToLen = clamp(torsoWidth / torsoLen, 0.18, 1.35);
  const torsoDepthToWidth = clamp(torsoDepth / torsoWidth, 0.12, 0.78);
  const armVolumeRatio = clamp(upperArmWidth / upperArmLen, 0.08, 0.5);
  const forearmVolumeRatio = clamp(foreArmWidth / foreArmLen, 0.08, 0.5);
  const thighVolumeRatio = clamp(thighWidth / thighLen, 0.08, 0.5);
  const shinVolumeRatio = clamp(shinWidth / shinLen, 0.08, 0.5);
  const handAspect = clamp(handWidth / handLen, 0.22, 1.2);
  const footAspect = clamp(footWidth / footLen, 0.18, 0.9);
  const legToTorsoRatio = clamp((thighLen + shinLen) / torsoLen, 0.9, 3.2);
  const label =
    shoulderToHipRatio >= 1.12
      ? "broad"
      : torsoWidthToLen <= 0.44 && armVolumeRatio <= 0.2
        ? "lean"
        : "balanced";

  return {
    label,
    shoulderToHipRatio,
    torsoWidthToLen,
    torsoDepthToWidth,
    armVolumeRatio,
    forearmVolumeRatio,
    thighVolumeRatio,
    shinVolumeRatio,
    handAspect,
    footAspect,
    legToTorsoRatio,
  };
}

export function estimateFitCalibration(metrics = {}, options = {}) {
  const qualityScore = clamp(numberOr(options.qualityScore, 1), 0, 1);
  const profile = options.shapeProfile || deriveBodyShapeProfile(metrics);
  const confidence = clamp(0.35 + qualityScore * 0.65, 0.35, 1);
  const bias = (amount, low, high) => clamp(1 + amount * confidence, low, high);
  const offset = (amount, low, high) => clamp(amount * confidence, low, high);
  return {
    confidence,
    torsoWidthBias: bias((profile.shoulderToHipRatio - 1) * 0.16 + (profile.torsoWidthToLen - 0.7) * 0.18, 0.88, 1.18),
    torsoDepthBias: bias((profile.torsoDepthToWidth - 0.46) * 0.72, 0.9, 1.2),
    armWidthBias: bias((profile.armVolumeRatio - 0.22) * 1.25, 0.88, 1.18),
    forearmWidthBias: bias((profile.forearmVolumeRatio - 0.2) * 1.2, 0.88, 1.16),
    thighWidthBias: bias((profile.thighVolumeRatio - 0.18) * 1.18, 0.88, 1.18),
    shinWidthBias: bias((profile.shinVolumeRatio - 0.14) * 1.15, 0.88, 1.16),
    handWidthBias: bias((profile.handAspect - 0.78) * 0.4, 0.92, 1.15),
    bootWidthBias: bias((profile.footAspect - 0.32) * 0.5, 0.9, 1.16),
    bootHeightBias: bias((profile.legToTorsoRatio - 1.9) * -0.08, 0.9, 1.1),
    verticalBias: bias((profile.legToTorsoRatio - 1.9) * 0.05, 0.94, 1.08),
    chestOffsetBias: offset((profile.torsoWidthToLen - 0.68) * 0.05, -0.03, 0.03),
    waistOffsetBias: offset((1.02 - profile.shoulderToHipRatio) * 0.04, -0.03, 0.03),
  };
}

export function estimateFitReadiness(snapshotLike = {}) {
  const reliableJointCount = numberOr(snapshotLike.reliableJointCount, 0);
  const qualityScore = clamp(numberOr(snapshotLike.qualityScore, 0), 0, 1);
  const hasMeasuredTorsoAnchors = Boolean(snapshotLike.hasMeasuredTorsoAnchors);
  const hasSolvedTorsoAnchors = Boolean(snapshotLike.hasSolvedTorsoAnchors);
  const hasUpperBodyAnchors = Boolean(snapshotLike.hasUpperBodyAnchors);
  const reasons = [];
  if (!hasSolvedTorsoAnchors) reasons.push("torso_anchors");
  if (!hasMeasuredTorsoAnchors) reasons.push("synthetic_torso");
  if (reliableJointCount < 7) reasons.push("joint_count");
  if (qualityScore < 0.55) reasons.push("quality");
  let label = "insufficient";
  if (
    hasSolvedTorsoAnchors &&
    reliableJointCount >= 7 &&
    qualityScore >= 0.55 &&
    (hasMeasuredTorsoAnchors || reliableJointCount >= 9)
  ) {
    label = "fit-ready";
  } else if (hasUpperBodyAnchors && reliableJointCount >= 5 && qualityScore >= 0.42) {
    label = "upper-body-only";
  }
  const score = clamp(
    qualityScore * 0.65 +
      (hasMeasuredTorsoAnchors ? 0.08 : 0) +
      (hasSolvedTorsoAnchors ? 0.22 : 0) +
      (hasUpperBodyAnchors ? 0.08 : 0) +
      clamp(reliableJointCount / RELIABLE_JOINT_NAMES.length, 0, 1) * 0.05,
    0,
    1
  );
  return { label, score, reasons };
}

export function createBoneInferenceSnapshot({ joints, source = "unknown", options = {} }) {
  const rawJoints = { ...(joints || {}) };
  const rawMetrics = estimateBodyMetricsFromJoints(rawJoints, options);
  const completedJoints = completeCanonicalJoints(rawJoints, rawMetrics, options);
  const metrics = estimateBodyMetricsFromJoints(completedJoints, options);
  const reliableJointCount = countReliableJoints(rawJoints);
  const hasMeasuredTorsoAnchors = Boolean(
    rawJoints.left_shoulder && rawJoints.right_shoulder && rawJoints.left_hip && rawJoints.right_hip
  );
  const hasSolvedTorsoAnchors = Boolean(
    completedJoints.left_shoulder &&
      completedJoints.right_shoulder &&
      completedJoints.left_hip &&
      completedJoints.right_hip
  );
  const hasUpperBodyAnchors = Boolean(
    rawJoints.left_shoulder &&
      rawJoints.right_shoulder &&
      (rawJoints.left_elbow || rawJoints.right_elbow || rawJoints.left_wrist || rawJoints.right_wrist)
  );
  const quality = estimateInferenceQuality(completedJoints);
  const shapeProfile = deriveBodyShapeProfile(metrics);
  const fitCalibration = estimateFitCalibration(metrics, {
    qualityScore: quality.qualityScore,
    shapeProfile,
  });
  const fitReadiness = estimateFitReadiness({
    reliableJointCount,
    qualityScore: quality.qualityScore,
    hasMeasuredTorsoAnchors,
    hasSolvedTorsoAnchors,
    hasUpperBodyAnchors,
  });

  return {
    source,
    rawJoints,
    joints: completedJoints,
    metrics,
    reliableJointCount,
    rawJointCount: countReliableJoints(rawJoints, CANONICAL_JOINT_ORDER),
    completedJointCount: countReliableJoints(completedJoints, CANONICAL_JOINT_ORDER),
    hasMeasuredTorsoAnchors,
    hasSolvedTorsoAnchors,
    hasUpperBodyAnchors,
    qualityScore: quality.qualityScore,
    qualityLabel: quality.qualityLabel,
    coverage: quality.coverage,
    bilateralRatio: quality.bilateralRatio,
    shapeProfile,
    fitCalibration,
    fitReadiness: fitReadiness.label,
    fitReadinessScore: fitReadiness.score,
    fitReadinessReasons: fitReadiness.reasons,
  };
}
