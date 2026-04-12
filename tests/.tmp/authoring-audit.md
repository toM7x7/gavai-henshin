# VRM-First Authoring Audit

- mode: `auto_fit`
- suitspec: `examples/suitspec.sample.json`
- sim: `sessions/body-sim.json`
- rebuild: 0
- tune: 7
- keep: 11

## Wave 1

- goal: 胸背腰と腕系の接続をVRM基準で作り直す
- parts: chest, back, waist, left_shoulder, right_shoulder, left_upperarm, right_upperarm, left_forearm, right_forearm

## Wave 2

- goal: 下半身の接続と足首まわりをVRM基準で安定させる
- parts: left_thigh, right_thigh, left_shin, right_shin, left_boot, right_boot

## Wave 3

- goal: 頭部と末端部位を仕上げて展示品質へ寄せる
- parts: helmet, left_hand, right_hand

## Baseline: Default VRM

- vrm_path: `viewer/assets/vrm/default.vrm`
- regression_ok: `True`
- fit_score: `80.969`
- can_save: `True`

### helmet

- decision: `keep`
- action: 現状維持
- wave / priority: Wave 3 / P2
- anchor / proxy: `head` / `head_sphere`
- seam_focus: helmet-chest
- reasons: baseline gate passed
- pass_gates: VRM baselineで再回帰して summary.canSave == true

### chest

- decision: `keep`
- action: 現状維持
- wave / priority: Wave 1 / P0
- anchor / proxy: `upperChest` / `torso_obb`
- seam_focus: helmet-chest, chest-back, chest-waist
- reasons: baseline gate passed
- pass_gates: VRM baselineで再回帰して summary.canSave == true

### back

- decision: `keep`
- action: 現状維持
- wave / priority: Wave 1 / P0
- anchor / proxy: `upperChest` / `torso_obb`
- seam_focus: chest-back
- reasons: baseline gate passed
- pass_gates: VRM baselineで再回帰して summary.canSave == true

### waist

- decision: `tune`
- action: 既存メッシュ補正 + fit再校正
- wave / priority: Wave 1 / P0
- anchor / proxy: `hips` / `torso_obb`
- seam_focus: chest-waist, waist-thigh
- reasons: part score 76.5 < 82
- pass_gates: surfaceViolations == 0 | heroOverflow == 0 | symmetryDelta ok

### left_shoulder

- decision: `keep`
- action: 現状維持
- wave / priority: Wave 1 / P0
- anchor / proxy: `leftShoulder` / `upperarm_capsule`
- seam_focus: shoulder-upperarm
- reasons: baseline gate passed
- pass_gates: VRM baselineで再回帰して summary.canSave == true

### right_shoulder

- decision: `keep`
- action: 現状維持
- wave / priority: Wave 1 / P0
- anchor / proxy: `rightShoulder` / `upperarm_capsule`
- seam_focus: shoulder-upperarm
- reasons: baseline gate passed
- pass_gates: VRM baselineで再回帰して summary.canSave == true

### left_upperarm

- decision: `tune`
- action: 既存メッシュ補正 + fit再校正
- wave / priority: Wave 1 / P0
- anchor / proxy: `leftUpperArm` / `upperarm_capsule`
- seam_focus: shoulder-upperarm, upperarm-forearm
- reasons: part score 79.4 < 82
- pass_gates: surfaceViolations == 0 | heroOverflow == 0 | symmetryDelta ok

### right_upperarm

- decision: `tune`
- action: 既存メッシュ補正 + fit再校正
- wave / priority: Wave 1 / P0
- anchor / proxy: `rightUpperArm` / `upperarm_capsule`
- seam_focus: shoulder-upperarm, upperarm-forearm
- reasons: part score 79.4 < 82
- pass_gates: surfaceViolations == 0 | heroOverflow == 0 | symmetryDelta ok

### left_forearm

- decision: `keep`
- action: 現状維持
- wave / priority: Wave 1 / P0
- anchor / proxy: `leftLowerArm` / `forearm_capsule`
- seam_focus: upperarm-forearm, forearm-hand
- reasons: baseline gate passed
- pass_gates: VRM baselineで再回帰して summary.canSave == true

### right_forearm

- decision: `keep`
- action: 現状維持
- wave / priority: Wave 1 / P0
- anchor / proxy: `rightLowerArm` / `forearm_capsule`
- seam_focus: upperarm-forearm, forearm-hand
- reasons: baseline gate passed
- pass_gates: VRM baselineで再回帰して summary.canSave == true

### left_hand

- decision: `keep`
- action: 現状維持
- wave / priority: Wave 3 / P2
- anchor / proxy: `leftHand` / `forearm_capsule`
- seam_focus: forearm-hand
- reasons: baseline gate passed
- pass_gates: VRM baselineで再回帰して summary.canSave == true

### right_hand

- decision: `keep`
- action: 現状維持
- wave / priority: Wave 3 / P2
- anchor / proxy: `rightHand` / `forearm_capsule`
- seam_focus: forearm-hand
- reasons: baseline gate passed
- pass_gates: VRM baselineで再回帰して summary.canSave == true

### left_thigh

- decision: `tune`
- action: 既存メッシュ補正 + fit再校正
- wave / priority: Wave 2 / P1
- anchor / proxy: `leftUpperLeg` / `thigh_capsule`
- seam_focus: waist-thigh, thigh-shin
- reasons: part score 70.8 < 82
- pass_gates: surfaceViolations == 0 | heroOverflow == 0 | symmetryDelta ok

### right_thigh

- decision: `tune`
- action: 既存メッシュ補正 + fit再校正
- wave / priority: Wave 2 / P1
- anchor / proxy: `rightUpperLeg` / `thigh_capsule`
- seam_focus: waist-thigh, thigh-shin
- reasons: part score 70.8 < 82
- pass_gates: surfaceViolations == 0 | heroOverflow == 0 | symmetryDelta ok

### left_shin

- decision: `tune`
- action: 既存メッシュ補正 + fit再校正
- wave / priority: Wave 2 / P0
- anchor / proxy: `leftLowerLeg` / `shin_capsule`
- seam_focus: thigh-shin, shin-boot
- reasons: part score 80.8 < 82
- pass_gates: surfaceViolations == 0 | heroOverflow == 0 | symmetryDelta ok

### right_shin

- decision: `tune`
- action: 既存メッシュ補正 + fit再校正
- wave / priority: Wave 2 / P0
- anchor / proxy: `rightLowerLeg` / `shin_capsule`
- seam_focus: thigh-shin, shin-boot
- reasons: part score 80.8 < 82
- pass_gates: surfaceViolations == 0 | heroOverflow == 0 | symmetryDelta ok

### left_boot

- decision: `keep`
- action: 現状維持
- wave / priority: Wave 2 / P0
- anchor / proxy: `leftFoot` / `foot_obb`
- seam_focus: shin-boot
- reasons: baseline gate passed
- pass_gates: VRM baselineで再回帰して summary.canSave == true

### right_boot

- decision: `keep`
- action: 現状維持
- wave / priority: Wave 2 / P0
- anchor / proxy: `rightFoot` / `foot_obb`
- seam_focus: shin-boot
- reasons: baseline gate passed
- pass_gates: VRM baselineで再回帰して summary.canSave == true
