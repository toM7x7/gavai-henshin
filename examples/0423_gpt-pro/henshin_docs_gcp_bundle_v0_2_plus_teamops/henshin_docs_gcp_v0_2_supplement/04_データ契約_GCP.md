# 04_データ契約_GCP

Version: 0.2  
用途: Web / Backend / Quest / AI で共有する schema の初版

---

## 1. EmotionProfile

```json
{
  "emotion_profile_id": "EP-0001",
  "bravery": 0.85,
  "restraint": 0.70,
  "protectiveness": 0.90,
  "mysticism": 0.55,
  "context_tags": ["正義", "未来志向", "仲間想い"],
  "raw_input": "仲間を守り、未来を切り開く存在になりたい。...",
  "confidence": 0.74,
  "assumptions": ["入力は守護志向と解釈した"]
}
```

---

## 2. DesignVector

```json
{
  "design_vector_id": "DV-0001",
  "silhouette": "sharp",
  "armor_mass": "medium",
  "helmet_type": "visor",
  "shoulder_volume": "high",
  "palette_family": "carmine_titanium_cyan",
  "emissive_style": "core_line",
  "combat_bias": "speed_close_range"
}
```

---

## 3. PartPlan (抽象案)

```yaml
theme: vanguard
helmet:
  style: visor
  silhouette: sharp
  aggression: medium
chest:
  emphasis: core
  armor_mass: medium
arms:
  type: bracer
legs:
  mobility: high
back_unit:
  type: wing_booster
emblem:
  motif: solar
palette:
  primary: carmine
  secondary: titanium
  accent: cyan
```

---

## 4. ResolvedPartPlan

```json
{
  "base_body": "base_frame_alpha",
  "helmet": "helmet_visor_03",
  "chest": "chest_core_05",
  "arm_l": "arm_bracer_02",
  "arm_r": "arm_bracer_02",
  "belt": "belt_driver_01",
  "leg_l": "leg_strider_03",
  "leg_r": "leg_strider_03",
  "back": "back_wing_01",
  "emblem": "emblem_solar_01",
  "warnings": [],
  "substitutions": []
}
```

---

## 5. SuitManifest (正本)

```json
{
  "suit_id": "SUIT-X01-0241",
  "version": 3,
  "project_id": "PRJ-001",
  "display_name": "X-01 ヴァンガード",
  "base_body": "base_frame_alpha",
  "parts": {
    "helmet": "helmet_visor_03",
    "chest": "chest_core_05",
    "arm_l": "arm_bracer_02",
    "arm_r": "arm_bracer_02",
    "belt": "belt_driver_01",
    "leg_l": "leg_strider_03",
    "leg_r": "leg_strider_03",
    "back": "back_wing_01",
    "emblem": "emblem_solar_01"
  },
  "materials": {
    "undersuit": "m_under_black_01",
    "armor_main": "m_armor_titanium_03",
    "armor_sub": "m_armor_carmine_01",
    "emissive": "m_emit_cyan_01"
  },
  "design_source": {
    "emotion_profile_id": "EP-0001",
    "design_vector_id": "DV-0001",
    "part_plan_id": "PP-0001"
  },
  "artifacts": {
    "preview_png": "gs://.../preview.png",
    "blueprint_png": "gs://.../blueprint.png",
    "emblem_png": "gs://.../emblem.png",
    "merged_glb": "gs://.../merged.glb"
  },
  "status": "READY_FOR_QUEST"
}
```

---

## 6. Morphotype

```json
{
  "morphotype_id": "M-0032",
  "height": 173,
  "shoulder_width": 44.2,
  "hip_width": 31.0,
  "arm_length": 59.4,
  "leg_length": 92.0,
  "torso_length": 58.2,
  "scale": 1.00,
  "source": "manual|quest|mocopi",
  "confidence": 0.82
}
```

---

## 7. TransformSession

```json
{
  "trial_id": "TRIAL-0047-Q",
  "project_id": "PRJ-001",
  "participant_id": "P-250527-012",
  "device_id": "QUEST-01",
  "suit_id": "SUIT-X01-0241",
  "morphotype_id": "M-0032",
  "status": "COMPLETED",
  "fit_score": 0.987,
  "started_at": "2026-04-23T08:30:00Z",
  "ended_at": "2026-04-23T08:31:15Z"
}
```

---

## 8. TransformEvent

```json
{
  "event_id": "EVT-0001",
  "trial_id": "TRIAL-0047-Q",
  "seq": 1,
  "t_ms": 3210,
  "type": "FIT_CONFIRMED",
  "payload": {
    "fit_score": 0.936
  }
}
```

### 想定イベント種別
- FIT_STARTED
- FIT_CONFIRMED
- DRY_FIT_STARTED
- DRY_FIT_DONE
- VOICE_WAIT
- VOICE_ACCEPTED
- TRANSFORM_BEGIN
- DEPOSITION_FINISHED
- SEALED
- RESULT_READY
- REPLAY_READY
- ARCHIVED

---

## 9. ReplayScript

```json
{
  "replay_id": "RPL-0001",
  "trial_id": "TRIAL-0047-Q",
  "mode": "QUEST_REPLAY",
  "segments": [
    {
      "at_ms": 3210,
      "title": "適合確定",
      "subtitle": "適合率 93.6% を確認",
      "camera": "front_close",
      "fx": "fit_glow"
    },
    {
      "at_ms": 7640,
      "title": "変身開始",
      "subtitle": "掛け声を受理",
      "camera": "center_full",
      "fx": "core_flash"
    },
    {
      "at_ms": 15230,
      "title": "蒸着完了",
      "subtitle": "装甲展開を確認",
      "camera": "orbit_half",
      "fx": "deposition_finish"
    }
  ]
}
```

---

## 10. PartCatalog (最小モデル)

```json
{
  "part_id": "helmet_visor_03",
  "category": "helmet",
  "display_name": "Phoenix Visor",
  "socket": "head_socket",
  "compatible_base_bodies": ["base_frame_alpha"],
  "material_slots": ["armor_main", "armor_sub", "emissive"],
  "bounds_profile": "medium_head",
  "status": "ACTIVE"
}
```

---

## 11. Firestore live model

### `quest_devices/{deviceId}`
```json
{
  "deviceId": "QUEST-01",
  "status": "CONNECTED",
  "lastSeenAt": "2026-04-23T08:30:10Z",
  "currentTrialId": "TRIAL-0047-Q",
  "operatorId": "OP-001"
}
```

### `live_trials/{trialId}`
```json
{
  "trialId": "TRIAL-0047-Q",
  "currentStep": "VOICE_WAIT",
  "progress": 0.63,
  "fitScore": 0.987,
  "questConnection": "LIVE",
  "updatedAt": "2026-04-23T08:30:40Z"
}
```

---

## 12. Cloud SQL relation rough map

```text
projects ─┬─ suits ─┬─ suit_versions
          │         └─ transform_sessions ─┬─ transform_events
          │                                └─ replay_scripts
          ├─ participants
          ├─ emotion_profiles
          ├─ design_vectors
          ├─ part_plans
          └─ audit_logs

part_catalog ─┬─ part_assets
              └─ compatibility_rules
```

---

## 13. Schema固定の優先順位

### 今すぐ固定
- SuitManifest
- PartCatalog
- TransformSession
- TransformEvent type
- ReplayScript

### 次に固定
- Operator / Participant / Project
- Firestore live docs
- Asset path rule

### 後で拡張
- analytics
- export jobs
- reporting
