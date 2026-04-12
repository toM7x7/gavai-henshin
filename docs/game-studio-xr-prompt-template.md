# Game Studio XR Prompt Template

更新日: 2026-03-28

このテンプレートは、Game Studio / XR Blocks 系の XR PoC を起こすときに使う。
目的は `gavai-henshin` の truth source を壊さず、XR 体験部分だけを高速に試すこと。

## Template

### 1. Scene Premise

- project: `gavai-henshin`
- scene goal:
- player fantasy:
- target runtime:
- session length:

### 2. Player Position

- start pose:
- start camera relationship:
- expected facing:
- world origin rule:

### 3. Body Anchor Points

- source of truth: `SuitSpec + vrm_anchor + body-fit canon`
- required anchors:
- preview anchors:
- attach order:

### 4. Attach Sequence

- trigger verb:
- pre-roll:
- spawn behavior:
- convergence behavior:
- attach confirm:
- cancel path:

### 5. Feedback / A11y

- visual cue:
- audio cue:
- haptic cue:
- accessibility fallback:
- failure feedback:

### 6. Success / Failure States

- success state:
- soft failure:
- hard failure:
- reset behavior:

## Example Seed for First PoC

### Scene Premise

- project: `gavai-henshin`
- scene goal: `pinch -> armor spawn -> body attach preview`
- player fantasy: `空間中央で変身儀式を開始し、装甲ユニットが身体へ再編成される`
- target runtime: `headset XR prototype`
- session length: `30-60 seconds`

### Player Position

- start pose: `neutral standing`
- start camera relationship: `first-person or over-shoulder preview`
- expected facing: `front-facing chest anchor visible first`
- world origin rule: `player chest center is the main presentation anchor`

### Body Anchor Points

- source of truth: `SuitSpec + vrm_anchor + body-fit canon`
- required anchors: `chest, left_upperarm, right_upperarm, left_forearm, right_forearm`
- preview anchors: `shoulder and back may remain ghosted in v1`
- attach order: `chest -> shoulders -> upperarms -> forearms`

### Attach Sequence

- trigger verb: `pinch`
- pre-roll: `brief threshold ring and ghost silhouette`
- spawn behavior: `armor modules appear in front hemisphere`
- convergence behavior: `modules align to target anchors, then slow before contact`
- attach confirm: `short glow + lock sound`
- cancel path: `release before threshold returns modules to idle orbit`

### Feedback / A11y

- visual cue: `ghost silhouette, attach rails, chest-led pulse`
- audio cue: `low synth charge, attach ticks, lock confirm`
- haptic cue: `optional, not required in v1`
- accessibility fallback: `high-contrast rails and reduced motion mode`
- failure feedback: `module fades back to standby orbit`

### Success / Failure States

- success state: `player clearly understands attach order and body alignment`
- soft failure: `module hesitates, then returns to preview`
- hard failure: `anchors unresolved, show ghost silhouette only`
- reset behavior: `single gesture returns to ready state`
