import { clampSurfaceOffsetForPart } from "./armor-canon.js";

export const RUNTIME_PLACEMENT_MODE_WEB_PREVIEW = "web_preview_parity";
export const RUNTIME_PLACEMENT_MODE_QUEST_RIG = "quest_rig";

function firstString(...values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "";
}

export function vectorArrayFromRuntimeRecord(record) {
  if (!record || typeof record !== "object") return null;
  if (Array.isArray(record)) {
    const values = record.slice(0, 3).map((value) => Number(value));
    return values.length >= 3 && values.every((value) => Number.isFinite(value)) ? values : null;
  }
  const values = ["x", "y", "z"].map((axis) => Number(record[axis]));
  return values.every((value) => Number.isFinite(value)) ? values : null;
}

export function positiveVectorArrayFromRuntimeRecord(values, fallback = [1, 1, 1]) {
  const source = Array.isArray(values) ? values : null;
  return [0, 1, 2].map((index) => {
    const value = Number(source?.[index]);
    return Number.isFinite(value) && value > 0 ? value : fallback[index];
  });
}

export function isRuntimeRenderPlacementRecord(value) {
  return Boolean(
    value
      && typeof value === "object"
      && (
        firstString(value.contract_version) === "runtime-render-placement.v1"
        || "target_size_array_m" in value
        || "target_size_m" in value
        || "offset_m" in value
        || "rotation_deg" in value
        || "quest_rig_offset_m" in value
      ),
  );
}

export function resolveRuntimePlacementMode({ placement, webPreviewParity = false } = {}) {
  if (webPreviewParity) return RUNTIME_PLACEMENT_MODE_WEB_PREVIEW;
  const mode = firstString(placement?.quest_runtime_placement_mode).toLowerCase();
  return ["web_preview_parity", "web-preview", "web_preview", "web", "parity"].includes(mode)
    ? RUNTIME_PLACEMENT_MODE_WEB_PREVIEW
    : RUNTIME_PLACEMENT_MODE_QUEST_RIG;
}

export function resolveRuntimeTargetSize({ placement, fallback = [1, 1, 1], mode = RUNTIME_PLACEMENT_MODE_QUEST_RIG } = {}) {
  const target = mode === RUNTIME_PLACEMENT_MODE_WEB_PREVIEW
    ? vectorArrayFromRuntimeRecord(placement?.target_size_m) || vectorArrayFromRuntimeRecord(placement?.target_size_array_m)
    : vectorArrayFromRuntimeRecord(placement?.target_size_array_m) || vectorArrayFromRuntimeRecord(placement?.target_size_m);
  return positiveVectorArrayFromRuntimeRecord(target, fallback);
}

export function questOffsetArrayFromPlacement(placement) {
  return vectorArrayFromRuntimeRecord(placement?.quest_rig_offset_m);
}

export function webPreviewOffsetArrayFromPlacement(placement) {
  return vectorArrayFromRuntimeRecord(placement?.offset_m);
}

export function questSurfaceOffsetArrayFromPlacement(placement) {
  return vectorArrayFromRuntimeRecord(placement?.quest_surface_offset_clamped_m)
    || vectorArrayFromRuntimeRecord(placement?.surface_anchor?.quest_rig_offset_clamped_m);
}

export function webPreviewSurfaceOffsetArrayFromPlacement(placement) {
  return vectorArrayFromRuntimeRecord(placement?.surface_offset_clamped_m)
    || vectorArrayFromRuntimeRecord(placement?.surface_anchor?.offset_clamped_m);
}

export function clampedQuestOffsetArrayFromPlacement(part, placement) {
  const runtimeClampedOffset = questSurfaceOffsetArrayFromPlacement(placement);
  if (runtimeClampedOffset) return runtimeClampedOffset;
  const offset = questOffsetArrayFromPlacement(placement);
  return offset ? clampSurfaceOffsetForPart(part, offset, "quest") : null;
}

export function resolveRuntimeOffset({ part, placement, mode = RUNTIME_PLACEMENT_MODE_QUEST_RIG } = {}) {
  if (mode === RUNTIME_PLACEMENT_MODE_WEB_PREVIEW) {
    const runtimeClampedOffset = webPreviewSurfaceOffsetArrayFromPlacement(placement);
    if (runtimeClampedOffset) return runtimeClampedOffset;
    const offset = webPreviewOffsetArrayFromPlacement(placement);
    return offset ? clampSurfaceOffsetForPart(part, offset, "vrm") : null;
  }
  return clampedQuestOffsetArrayFromPlacement(part, placement);
}

function radiansFromDegrees(value) {
  return (Number(value) || 0) * Math.PI / 180;
}

export function resolveRuntimeRotation({ placement, mode = RUNTIME_PLACEMENT_MODE_QUEST_RIG } = {}) {
  const rotation = vectorArrayFromRuntimeRecord(placement?.rotation_deg);
  if (!rotation) return null;
  return mode === RUNTIME_PLACEMENT_MODE_WEB_PREVIEW
    ? [
        radiansFromDegrees(rotation[0]),
        radiansFromDegrees(rotation[1]),
        radiansFromDegrees(rotation[2]),
      ]
    : [
        radiansFromDegrees(-rotation[0]),
        radiansFromDegrees(-rotation[1]),
        radiansFromDegrees(rotation[2]),
      ];
}

export function runtimePlacementMatchesIdentity({ part, placement, selectedVariantKey = "", assetRef = "" } = {}) {
  if (!isRuntimeRenderPlacementRecord(placement)) return false;
  const placementPart = firstString(placement.part);
  if (placementPart && part && placementPart !== part) return false;
  const placementKey = firstString(
    placement.selected_variant_key,
    placement.variant_key,
    placement.modeler_sidecar_variant_key,
  );
  if (placementKey && selectedVariantKey && placementKey !== selectedVariantKey) return false;
  const placementAsset = firstString(placement.asset_ref).replace(/\\/g, "/").replace(/[?#].*$/, "").replace(/^\/+/, "");
  const selectedAsset = firstString(assetRef).replace(/\\/g, "/").replace(/[?#].*$/, "").replace(/^\/+/, "");
  if (placementAsset && selectedAsset && placementAsset !== selectedAsset) return false;
  return true;
}
