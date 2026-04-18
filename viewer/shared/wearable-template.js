import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import * as BufferGeometryUtils from "three/addons/utils/BufferGeometryUtils.js";

const OPEN_ARC = Math.PI * 1.62;
const OPEN_START = Math.PI * 0.19;

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function materializeGeometry(geometry, { scale = [1, 1, 1], rotate = [0, 0, 0], translate = [0, 0, 0] } = {}) {
  const next = geometry.clone();
  next.scale(scale[0], scale[1], scale[2]);
  next.rotateX(rotate[0]);
  next.rotateY(rotate[1]);
  next.rotateZ(rotate[2]);
  next.translate(translate[0], translate[1], translate[2]);
  if (next.index) {
    const expanded = next.toNonIndexed();
    expanded.computeVertexNormals();
    return expanded;
  }
  next.computeVertexNormals();
  return next;
}

function roundedBox(width, height, depth, radius = 0.08, segments = 4) {
  return new RoundedBoxGeometry(
    width,
    height,
    depth,
    segments,
    clamp(radius, 0.01, Math.min(width, height, depth) * 0.45),
  );
}

function mergeParts(geometries) {
  const valid = geometries.filter(Boolean).map((geometry) => materializeGeometry(geometry));
  if (!valid.length) return new THREE.BoxGeometry(1, 1, 1).toNonIndexed();
  const merged = BufferGeometryUtils.mergeGeometries(valid, false);
  merged.computeVertexNormals();
  merged.computeBoundingBox();
  merged.computeBoundingSphere();
  return merged;
}

function makeSleeveTemplate({
  topRadius = 0.28,
  bottomRadius = 0.24,
  length = 1,
  arc = OPEN_ARC,
  start = OPEN_START,
  dorsalDepth = 0.12,
  cuffHeight = 0.1,
  ridgeScale = 0.9,
}) {
  const shell = new THREE.CylinderGeometry(topRadius, bottomRadius, length, 48, 1, true, start, arc);
  const upperCuff = materializeGeometry(
    new THREE.CylinderGeometry(topRadius * 1.04, topRadius * 0.92, cuffHeight, 48, 1, true, start, arc),
    { translate: [0, length * 0.5 - cuffHeight * 0.45, 0] },
  );
  const lowerCuff = materializeGeometry(
    new THREE.CylinderGeometry(bottomRadius * 1.05, bottomRadius * 0.92, cuffHeight, 48, 1, true, start, arc),
    { translate: [0, -length * 0.5 + cuffHeight * 0.45, 0] },
  );
  const dorsalPlate = materializeGeometry(
    roundedBox((topRadius + bottomRadius) * ridgeScale, length * 0.72, dorsalDepth, 0.04, 3),
    { translate: [0, 0, Math.max(topRadius, bottomRadius) * 0.92] },
  );
  const elbowRib = materializeGeometry(
    roundedBox((topRadius + bottomRadius) * 0.52, cuffHeight * 1.25, dorsalDepth * 0.7, 0.03, 2),
    { translate: [0, -length * 0.32, Math.max(topRadius, bottomRadius) * 0.86] },
  );
  return mergeParts([shell, upperCuff, lowerCuff, dorsalPlate, elbowRib]);
}

function makeShoulderTemplate() {
  const dome = materializeGeometry(
    new THREE.SphereGeometry(0.52, 36, 24, 0, Math.PI * 2, 0.1, Math.PI * 0.72),
    { scale: [0.94, 0.7, 1.0], translate: [0, 0.02, 0.02] },
  );
  const collar = materializeGeometry(
    new THREE.CylinderGeometry(0.34, 0.42, 0.2, 36, 1, true, OPEN_START, OPEN_ARC),
    { rotate: [0, 0, Math.PI * 0.5], translate: [0.02, -0.02, 0.01], scale: [0.88, 0.86, 0.88] },
  );
  const strikeFace = materializeGeometry(
    roundedBox(0.42, 0.3, 0.18, 0.05, 3),
    { translate: [0, 0.06, 0.28], rotate: [0.04, 0, 0], scale: [0.86, 0.84, 0.84] },
  );
  return mergeParts([dome, collar, strikeFace]);
}

function makeChestTemplate() {
  const plate = materializeGeometry(
    roundedBox(1.08, 0.64, 0.32, 0.1, 4),
    { translate: [0, 0.0, 0.0], scale: [0.84, 0.78, 0.7] },
  );
  const sternum = materializeGeometry(
    roundedBox(0.24, 0.54, 0.18, 0.05, 3),
    { translate: [0, -0.02, 0.14], scale: [0.82, 0.78, 0.82] },
  );
  const shoulderYokes = [
    materializeGeometry(roundedBox(0.28, 0.14, 0.14, 0.04, 2), { translate: [-0.28, 0.16, 0.08], scale: [0.84, 0.8, 0.8] }),
    materializeGeometry(roundedBox(0.28, 0.14, 0.14, 0.04, 2), { translate: [0.28, 0.16, 0.08], scale: [0.84, 0.8, 0.8] }),
  ];
  const lowerAb = materializeGeometry(
    roundedBox(0.58, 0.14, 0.16, 0.03, 2),
    { translate: [0, -0.19, 0.11], scale: [0.8, 0.8, 0.78] },
  );
  return mergeParts([plate, sternum, lowerAb, ...shoulderYokes]);
}

function makeBackTemplate() {
  const plate = materializeGeometry(
    roundedBox(1.06, 0.72, 0.28, 0.1, 4),
    { translate: [0, 0.02, -0.01], scale: [0.82, 0.8, 0.68] },
  );
  const spine = materializeGeometry(
    roundedBox(0.18, 0.62, 0.18, 0.04, 3),
    { translate: [0, 0.02, -0.12], scale: [0.82, 0.8, 0.78] },
  );
  const packRails = [
    materializeGeometry(roundedBox(0.12, 0.46, 0.12, 0.03, 2), { translate: [-0.22, 0.02, -0.08], scale: [0.76, 0.78, 0.72] }),
    materializeGeometry(roundedBox(0.12, 0.46, 0.12, 0.03, 2), { translate: [0.22, 0.02, -0.08], scale: [0.76, 0.78, 0.72] }),
  ];
  return mergeParts([plate, spine, ...packRails]);
}

function makeWaistTemplate() {
  const belt = materializeGeometry(
    roundedBox(1.08, 0.24, 0.44, 0.08, 3),
    { scale: [0.8, 0.86, 0.74] },
  );
  const centerGuard = materializeGeometry(
    roundedBox(0.3, 0.3, 0.2, 0.05, 3),
    { translate: [0, -0.03, 0.12], scale: [0.8, 0.76, 0.74] },
  );
  const sideTransfer = [
    materializeGeometry(roundedBox(0.18, 0.2, 0.16, 0.04, 2), { translate: [-0.3, 0.0, 0.08], scale: [0.76, 0.74, 0.7] }),
    materializeGeometry(roundedBox(0.18, 0.2, 0.16, 0.04, 2), { translate: [0.3, 0.0, 0.08], scale: [0.76, 0.74, 0.7] }),
  ];
  return mergeParts([belt, centerGuard, ...sideTransfer]);
}

function makeHelmetTemplate() {
  const dome = materializeGeometry(
    new THREE.SphereGeometry(0.5, 36, 24, 0, Math.PI * 2, 0.08, Math.PI * 0.82),
    { scale: [0.84, 0.82, 0.88], translate: [0, 0.05, 0.01] },
  );
  const faceShell = materializeGeometry(
    roundedBox(0.68, 0.42, 0.62, 0.08, 4),
    { translate: [0, -0.08, 0.03], scale: [0.82, 0.84, 0.7] },
  );
  const visorBand = materializeGeometry(
    roundedBox(0.64, 0.1, 0.16, 0.03, 2),
    { translate: [0, 0.0, 0.22], scale: [0.78, 0.82, 0.84] },
  );
  const jaw = materializeGeometry(
    roundedBox(0.44, 0.14, 0.34, 0.04, 2),
    { translate: [0, -0.18, 0.12], scale: [0.78, 0.76, 0.78] },
  );
  return mergeParts([dome, faceShell, visorBand, jaw]);
}

function makeHandTemplate() {
  const gauntlet = materializeGeometry(
    roundedBox(0.52, 0.22, 0.92, 0.06, 3),
    { translate: [0, -0.02, 0.06], scale: [0.8, 0.84, 0.8] },
  );
  const cuff = materializeGeometry(
    roundedBox(0.48, 0.26, 0.3, 0.05, 3),
    { translate: [0, 0.0, -0.22], scale: [0.78, 0.82, 0.76] },
  );
  const knuckle = materializeGeometry(
    roundedBox(0.4, 0.08, 0.26, 0.03, 2),
    { translate: [0, 0.06, 0.28], scale: [0.76, 0.8, 0.78] },
  );
  return mergeParts([gauntlet, cuff, knuckle]);
}

function makeBootTemplate() {
  const toe = materializeGeometry(
    roundedBox(0.48, 0.2, 0.82, 0.05, 3),
    { translate: [0, -0.01, 0.06], scale: [0.84, 0.78, 0.82] },
  );
  const cuff = materializeGeometry(
    roundedBox(0.44, 0.34, 0.36, 0.05, 3),
    { translate: [0, 0.13, -0.06], scale: [0.8, 0.82, 0.78] },
  );
  const ankleGuard = materializeGeometry(
    roundedBox(0.34, 0.12, 0.18, 0.03, 2),
    { translate: [0, 0.06, 0.16], scale: [0.78, 0.8, 0.8] },
  );
  const heel = materializeGeometry(
    roundedBox(0.24, 0.12, 0.18, 0.03, 2),
    { translate: [0, -0.01, -0.2], scale: [0.76, 0.8, 0.76] },
  );
  return mergeParts([toe, cuff, ankleGuard, heel]);
}

function makeLegTemplate(kind) {
  if (kind === "thigh") {
    return makeSleeveTemplate({
      topRadius: 0.34,
      bottomRadius: 0.29,
      length: 1,
      dorsalDepth: 0.14,
      cuffHeight: 0.12,
      ridgeScale: 1.08,
    });
  }
  return makeSleeveTemplate({
    topRadius: 0.28,
    bottomRadius: 0.22,
    length: 1,
    dorsalDepth: 0.12,
    cuffHeight: 0.1,
    ridgeScale: 0.92,
  });
}

function makeArmTemplate(kind) {
  if (kind === "upperarm") {
    return makeSleeveTemplate({
      topRadius: 0.26,
      bottomRadius: 0.22,
      length: 1,
      dorsalDepth: 0.12,
      cuffHeight: 0.11,
      ridgeScale: 1.0,
    });
  }
  return makeSleeveTemplate({
    topRadius: 0.22,
    bottomRadius: 0.18,
    length: 1,
    dorsalDepth: 0.11,
    cuffHeight: 0.09,
    ridgeScale: 0.92,
  });
}

export function createWearableTemplateGeometry(partName, fallbackShape = "box") {
  switch (partName) {
    case "helmet":
      return makeHelmetTemplate();
    case "chest":
      return makeChestTemplate();
    case "back":
      return makeBackTemplate();
    case "waist":
      return makeWaistTemplate();
    case "left_shoulder":
    case "right_shoulder":
      return makeShoulderTemplate();
    case "left_upperarm":
    case "right_upperarm":
      return makeArmTemplate("upperarm");
    case "left_forearm":
    case "right_forearm":
      return makeArmTemplate("forearm");
    case "left_hand":
    case "right_hand":
      return makeHandTemplate();
    case "left_thigh":
    case "right_thigh":
      return makeLegTemplate("thigh");
    case "left_shin":
    case "right_shin":
      return makeLegTemplate("shin");
    case "left_boot":
    case "right_boot":
      return makeBootTemplate();
    default:
      if (fallbackShape === "cylinder") {
        return makeSleeveTemplate({});
      }
      if (fallbackShape === "sphere") {
        return materializeGeometry(new THREE.SphereGeometry(0.5, 32, 24));
      }
      return materializeGeometry(roundedBox(1, 1, 1, 0.08, 3));
  }
}
