from pathlib import Path


def test_web_quest_runtime_placement_resolver_review_names_shared_contracts() -> None:
    doc = Path("docs/web-quest-runtime-placement-resolver-unification-review-2026-05-05.md").read_text(
        encoding="utf-8"
    )

    for token in {
        "viewer/shared/runtime-placement-resolver.js",
        "runtime-render-placement.v1",
        "armor-canon.js",
        "wearableSurfaceFitPolicyForPart(partName)",
        "clampSurfaceOffsetForPart(partName, offset, space = \"vrm\")",
        "isRuntimeRenderPlacementRecord(value)",
        "runtimePlacementMatchesIdentity({ part, placement, selectedVariantKey, assetRef })",
        "selectRuntimePlacementForPart({",
        "resolveRuntimePlacementMode({",
        "resolveRuntimeTargetSize({",
        "resolveRuntimeOffset({",
        "resolveRuntimeRotation({",
        "resolveRuntimeScale({",
        "resolveRuntimePlacementDiagnostics({",
    }:
        assert token in doc


def test_web_quest_runtime_placement_resolver_review_maps_current_duplicate_helpers() -> None:
    doc = Path("docs/web-quest-runtime-placement-resolver-unification-review-2026-05-05.md").read_text(
        encoding="utf-8"
    )

    for token in {
        "runtimePlacementForPreviewPart(part, module)",
        "runtimeTargetSizeForPreviewPart(part, module)",
        "runtimeOffsetForPreviewPart(part, module)",
        "runtimeRotationForPreviewPart(part, module)",
        "runtimeRenderPlacement(runtimePackage, part)",
        "targetSizeArrayFromPlacement(placement, fallback)",
        "runtimePlacementOffsetArrayForPart(part, placement)",
        "runtimePlacementRotationArray(placement)",
        "questRuntimePlacementAnchorDiagnosticsForPart(part, placement)",
        "armorStandRigPoseForPart()",
        "clampedQuestOffsetArrayFromPlacement(...)",
    }:
        assert token in doc


def test_web_quest_runtime_placement_resolver_review_preserves_mode_policy_and_risks() -> None:
    doc = Path("docs/web-quest-runtime-placement-resolver-unification-review-2026-05-05.md").read_text(
        encoding="utf-8"
    )

    for token in {
        "web_preview",
        "quest_rig",
        "web_preview_parity",
        "quest_armor_stand",
        "Armor Stand Decision Point",
        "Option A - Armor Stand Honors Shared Resolver",
        "Option B - Armor Stand Remains Quest-Rig Inspection",
        "Do not share scene code. Share resolver semantics.",
        "`runtime-render-placement.v1` remains the single selected placement record shape.",
        "`armor-canon.js` remains the owner of surface clamp policy, not duplicated tables.",
    }:
        assert token in doc


def test_shared_runtime_placement_resolver_is_used_by_web_and_quest() -> None:
    resolver = Path("viewer/shared/runtime-placement-resolver.js").read_text(encoding="utf-8")
    quest = Path("viewer/quest-iw-demo/quest-demo.js").read_text(encoding="utf-8")
    forge = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")

    for token in {
        'export const RUNTIME_PLACEMENT_MODE_WEB_PREVIEW = "web_preview_parity";',
        'export const RUNTIME_PLACEMENT_MODE_QUEST_RIG = "quest_rig";',
        "export function isRuntimeRenderPlacementRecord(value)",
        "export function resolveRuntimePlacementMode({ placement, webPreviewParity = false } = {})",
        "export function resolveRuntimeTargetSize({ placement, fallback = [1, 1, 1], mode = RUNTIME_PLACEMENT_MODE_QUEST_RIG } = {})",
        "export function resolveRuntimeOffset({ part, placement, mode = RUNTIME_PLACEMENT_MODE_QUEST_RIG } = {})",
        "export function resolveRuntimeRotation({ placement, mode = RUNTIME_PLACEMENT_MODE_QUEST_RIG } = {})",
        "clampSurfaceOffsetForPart(part, offset, \"quest\")",
        "clampSurfaceOffsetForPart(part, offset, \"vrm\")",
        "export function runtimePlacementMatchesIdentity({ part, placement, selectedVariantKey = \"\", assetRef = \"\" } = {})",
    }:
        assert token in resolver

    for token in {
        "../shared/runtime-placement-resolver.js",
        "resolveRuntimePlacementMode({",
        "resolveRuntimeTargetSize({",
        "resolveRuntimeOffset({",
        "resolveRuntimeRotation({",
    }:
        assert token in quest

    for token in {
        "../shared/runtime-placement-resolver.js",
        "isRuntimeRenderPlacementRecord(value)",
        "resolveRuntimeTargetSize({",
        "resolveRuntimeOffset({",
        "resolveRuntimeRotation({",
    }:
        assert token in forge
