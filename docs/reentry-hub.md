# Re-entry Hub

更新日: 2026-03-28

## 1. 現在地

- Phase 0-2 は概ね完了
- `viewer/body-fit` と `viewer/suit-dashboard` は存在し、Track A の基礎 viewer は動く
- VRM attach / auto-fit v1 / 8thWall-style camera pipeline pattern は採用済み
- 再開本線は `body-fit / live tracking`
- XR は本線置換ではなく別レーンで扱う

## 2. 未完了の本線課題

1. live tracking 品質の安定化
2. `upperarm / forearm` の arm orientation / bone roll 切り分け
3. `mocopi` 統合前の fallback 挙動の確認

## 3. 危険因子

- dirty worktree がある
  - `viewer/body-fit/body-fit-live.js`
  - `viewer/body-fit/index.html`
  - `viewer/body-fit/styles.css`
  - `viewer/body-fit/viewer.js`
- 一時生成物が混入しやすい
  - `.playwright-cli/*`
  - `output/filelist.txt`
- 8thWall は継続評価対象なので、関連実装を変えたら docs に判断理由を残す

## 4. 10分で戻す最短手順

### 4.1 サーバ起動

```powershell
npm run dev
```

開く URL:

- `http://localhost:8010/viewer/body-fit/`

### 4.2 baseline 確認順

1. `Load`
2. `Load VRM`
3. `Apply T-Pose`
4. `Auto Fit + Save`
5. `Attach: Hybrid`
6. `Start WebCam`

### 4.3 確認メトリクス

- `meta.live_pose_quality`
- `meta.live_pose_reliable_joints`
- `meta.vrm_live_driven`
- `meta.live_view_mode`
- `meta.live_view_effective`
- `meta.live_view_mirrored`
- `meta.camera_preset`
- `meta.live_pipeline_error`

## 5. UI Surface と期待挙動

### Camera Preset

- `Cam Front`
- `Cam Side`
- `Cam Back`
- `Cam POV`
- `Cam Top`
- `Focus Fit`

### Live View

- `auto`
  - `Cam Front` => mirror
  - `Cam Back` / `Cam POV` => world
- `mirror`
  - 常に mirror
- `world`
  - 常に world

## 6. 優先順位

1. body-fit baseline repair
2. `front/back/pov` と `mirror/world` の採否確定
3. arm orientation の切り分け
4. `mocopi` 前提の live 安定化
5. Game Studio / XR Blocks 向け XR PoC kickoff

## 7. XR Lane Split

- current viewer
  - fitting truth source
  - `SuitSpec` / `Morphotype` / VRM fit の確認基盤
- 8thWall
  - WebAR / camera runtime 候補
  - 現状は設計パターン採用に留める
- XR Blocks / Game Studio
  - headset 向け XR UX の高速 PoC
  - 本線コード統合ではなく、設計資産と first-scene prototyping に限定

## 8. 次のスプリント

### Sprint 1: body-fit baseline repair

- HTML 崩れ修復
- temporary artifacts cleanup
- live view change の採否確定
- body-fit docs 更新

### Sprint 2: live tracking stabilization

- `front/back/pov` と `mirror/world` の挙動確認
- `ReliableJoints`, `PoseQuality`, `LiveDrive` の確認導線を明文化
- low-confidence 時の挙動を再確認

### Sprint 3: arm orientation diagnosis

- 左右反転問題と bone roll 問題を分離
- `upperarm / forearm` の回転違和感を `VRM / anchor / live pose` に切り分け

### Sprint 4: Game Studio XR PoC kickoff

- PoC brief 確定
- first scene spec 固定
- demo acceptance criteria 定義
