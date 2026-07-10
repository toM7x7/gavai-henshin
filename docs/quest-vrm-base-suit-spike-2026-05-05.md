# Quest VRM Base Suit Spike - 2026-05-05

## Decision

Decision: do not wire VRM into quest-demo.js in this spike.

The repository has enough local material to start a VRM spike, but not enough to replace the current Quest base-suit fallback safely in one small viewer-only change.

## Local Findings

- `viewer/assets/vrm/default.vrm` exists and is a valid glTF 2.0 binary VRM from VRoid Studio.
- `package.json` includes `three` and `GLTFLoader`, but `@pixiv/three-vrm is not in package.json`.
- The VRM uses `VRMC_vrm`, `VRMC_springBone`, and `VRMC_materials_mtoon`. None are listed as required extensions, so `GLTFLoader` can likely parse the raw scene, but it will not provide VRM humanoid semantics, MToon parity, or spring-bone behavior.
- The local VRM has bone nodes such as `J_Bip_C_Neck` and `J_Bip_C_Head`.
- `Face` and `Body` are SkinnedMesh nodes. The body is one skinned mesh, so hiding the head/neck reliably is not equivalent to hiding a separate mesh node.

## Why Not Implement Now

The current user-facing requirement is stricter than "load a VRM file":

- Quest first-person must not draw anything above the neck.
- Mirror and armor-stand views should keep a human guide.
- Existing armor placement uses Quest mock-body anchors and runtime placement offsets.

With only `GLTFLoader`, we can load the VRM as a raw glTF scene, but we cannot safely remove just the head/neck surface from the skinned `Body` mesh. Hiding `J_Bip_C_Head` or `J_Bip_C_Neck` bones is not a reliable visibility mask for vertices already skinned into one body mesh. Showing that raw scene in first-person risks reintroducing the exact visual obstruction this task just removed.

## First-Person Operating Rule

first-person rule: never render VRM head/neck.

Until the VRM path has a proven head/neck mask, Quest first-person should keep using the current guide policy:

- Hide base-suit `head`, `neck`, `spine`, `shoulder_line`, and `torso` in self view.
- Hide generated fallback armor capsules in self view.
- Keep the human guide available in mirror and armor-stand preview.
- Treat helmet and VRM head/neck as the same obstruction class in self view.

## Shortest Safe Implementation Route

1. Add `@pixiv/three-vrm` or an equivalent local VRM humanoid adapter.
2. Load `viewer/assets/vrm/default.vrm` through a VRM-aware loader plugin, not only `GLTFLoader`.
3. Build a `BaseSuitAvatarAdapter` behind the existing `baseSuitGroup` interface:
   - `loadBaseSuitAvatar(suitspec, runtimePackage)`
   - `setBaseSuitAvatarMode("self" | "mirror" | "armor_stand")`
   - `applyBaseSuitAvatarPose(standTransform)`
   - `disposeBaseSuitAvatar()`
4. For mirror and armor stand, render the VRM avatar as the body guide.
5. For first-person, either:
   - use a confirmed headless/body-only mesh export, or
   - apply a tested material/geometry mask that removes head and neck vertices, or
   - keep the current procedural guide with the upper shell hidden.
6. Add browser QA with a debug snapshot that reports:
   - `baseSuit.source = "procedural" | "vrm"`
   - `baseSuit.firstPersonHeadNeckVisible = false`
   - VRM node names used for humanoid mapping.

## Acceptance Gate

Do not replace the procedural guide until all are true:

- Quest first-person screenshot shows no head, neck, face, hair, or upper-shell obstruction.
- Mirror view shows a readable human guide.
- Armor stand shows the full human guide with armor placement intact.
- Runtime placement and existing `tests/test_quest_recall_render_contract.py` pass.
- A contract test prevents loading raw VRM as first-person body shell without a head/neck mask.

