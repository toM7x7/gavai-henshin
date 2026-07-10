# Quest centerline telemetry QA - 2026-05-04

目的: Quest実機で見える「自分/鎧立ての中心線がずれる」問題を、1) runtime anchor/rigずれ、2) hard centerlineずれ、3) 部位anchor/runtime offsetずれ、4) GLB原点/boundsずれに分解する。

## 前提

- Quest URLは必ずcache-busting付きにする。
- telemetry取得時は `newRoute=1&code=3601&debug=1&qa=centerline&liveBody=1` を付ける。
- Web/API `8010` と Quest Vite `5173` は長時間terminalで起動したままにする。
- ADB reverseは `5173` と `8010` の両方を張る。
- 展示PCではまず helper を使い、手動 `adb reverse` は helper が使えない時だけにする。

標準起動:

```powershell
.\tools\start_quest_adb_reverse.ps1 -QuestPath "/viewer/quest-iw-demo/?newRoute=1&qa=centerline&debug=1&liveBody=1" -RecallCode 3601 -CacheBust -LaunchBrowser
```

helper が使えない時の手動起動:

```powershell
adb reverse --remove-all
adb reverse tcp:5173 tcp:5173
adb reverse tcp:8010 tcp:8010

$t = Get-Date -Format yyyyMMddHHmmss
$questUrl = "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&debug=1&qa=centerline&liveBody=1&t=$t"
adb shell am start -a android.intent.action.VIEW -d $questUrl com.oculus.browser
```

最新telemetry:

```powershell
$latest = Invoke-RestMethod http://127.0.0.1:8010/api/quest-debug/latest
$p = $latest.record.payload
$p.query.href
$p.uxState
$p.xr
$p.humanBodyMock.centerlineWorld
$p.meshes.records | Select-Object part,meshSource,runtimeOffsetClamped,@{n="originToBounds";e={$_.partCenter.originToBoundsCenterWorldM}},@{n="canonicalToOrigin";e={$_.partCenter.canonicalAnchorToMeshOriginWorldM}},@{n="canonicalToBounds";e={$_.partCenter.canonicalAnchorToBoundsCenterWorldM}},@{n="liveToOrigin";e={$_.partCenter.liveAnchorToMeshOriginWorldM}},@{n="liveToBounds";e={$_.partCenter.liveAnchorToBoundsCenterWorldM}}
```

当日ログ保存:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline
```

Quest表示がONで画像も必要なら:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline -Screencap
```

保存先は `qa\logs\quest-3601-<timestamp>\`。`quest-debug-latest.json` に `centerlineQa`、`operator-summary.txt` に `verdict/classification/displayLine` の短縮サマリが残る。

## 取得シーン

1. neutral self: 正面を向いてVR開始、1秒静止。
2. self live body: `liveBody=1` のまま変身中/完了直後、両手を自然に下ろす。
3. armor stand: 鎧立てON直後、手操作前。
4. armor stand after grab: 右grip移動/両grip回転を1回だけ実施。
5. mirror/replay observer: 鎧立てを閉じ、鏡またはReplay observerへ戻る。
6. recenter: ズレが見えた状態で再センター/再入室し、同じ値を再取得。

各シーンで `/api/quest-debug/latest` の `query.href` が直近timestampであることを先に確認する。古いURLならそのサンプルは捨てる。

## 判定順

### 1. runtime anchor / rigずれ

最初に `xr` を見る。

- `xr.xrWorldAnchorProfile` が期待状態と一致すること。
  - self: `self`
  - armor stand: `armor_stand`
  - mirror: `mirror`
  - replay observer: `replay_observer`
- `xr.anchorToRigDistanceM <= 0.05`
- `abs(xr.anchorToRigYawDeltaDeg) <= 3`
- `xr.cameraToAnchorDistanceM` がprofile距離と大きく外れない。
- `xr.cameraToAnchorWorldM` が `xr.cameraForwardWorld` 方向に伸びている。

ここでNGなら、見た目の中心線ズレは部位ではなくruntime anchor/rig更新の問題として扱う。部位調整やGLB修正に進まない。

### 2. hard centerlineずれ

anchor/rigが合格したら、`cameraLocalInRig` と `humanBodyMock.centerlineWorld` を見る。

- self開始直後のneutral姿勢では `xr.cameraLocalInRig.x` がほぼ0であること。
- `humanBodyMock.centerlineWorld.head -> pelvis` が、視覚上の身体中心線と同じ方向にずれているか確認する。
- すべてのpartで `partCenter.liveAnchorToMeshOriginWorldM` または `partCenter.liveAnchorToBoundsCenterWorldM` が同じ左右方向に寄る場合は、部位個別ではなくhard centerlineずれ。

hard centerlineずれの典型:

- helmet/chest/waist/bootsまで同じX符号でずれる。
- `runtimeOffsetClamped` は小さい、または左右対称なのに全体が寄る。
- `originToBoundsCenterWorldM` は部位ごとに違うが、全体の見え方は同じ方向へ流れる。

この場合は `QUEST_HUMAN_BODY_MOCK`, `questBodyRelativeOffsetForPart`, `liveHeadPosition`, `liveTorsoYaw` の調整対象。GLB原点修正にしない。

### 3. 部位anchor / runtime offsetずれ

hard centerlineが合格したら、partごとの `runtimeOffsetClamped` と canonical/live差分を見る。

- `runtimeOffsetClamped` が大きい部位だけずれるならruntime placement。
- `canonicalAnchorToMeshOriginWorldM` が特定部位だけ大きいなら、その部位anchorかruntime offset。
- self live bodyでは `liveAnchorToMeshOriginWorldM` を優先する。
- armor stand/mirror/replay observerでは `canonicalAnchorToMeshOriginWorldM` を優先する。

判定:

- chest/back/waistだけ前後にずれる: torso anchor contractまたはsurface offset。
- 左右腕だけ外側/内側にずれる: shoulder/upperarm/forearm anchorまたは左右符号。
- bootsだけ床方向にずれる: boot anchorまたはfloor lift。

### 4. GLB原点 / boundsずれ

最後に `originToBoundsCenterWorldM` を見る。

- `canonicalAnchorToMeshOriginWorldM` は小さいが、`canonicalAnchorToBoundsCenterWorldM` が大きい。
- または `liveAnchorToMeshOriginWorldM` は小さいが、`liveAnchorToBoundsCenterWorldM` が大きい。

この場合はGLBのoriginが見た目中心とずれている。runtime offsetで吸収すると、鎧立て/Replay/Forge preview間で別のずれを作るため、modeler側のorigin/bounds修正または明示的な part fit metadata に戻す。

## 合格ライン

- anchor: `anchorToRigDistanceM <= 0.05`, `abs(anchorToRigYawDeltaDeg) <= 3`
- self neutral: `abs(cameraLocalInRig.x) <= 0.08`
- hard centerline: head/upper torso/pelvisが同じ左右方向に0.10m以上流れない
- per-part: torso主要部位の `liveAnchorToBoundsCenterWorldM` または `canonicalAnchorToBoundsCenterWorldM` が部位意図に対して0.10m以内
- GLB origin: `originToBoundsCenterWorldM` が大きい部位は、modeler修正票に回し、runtime anchor修正PRに混ぜない

## 記録フォーマット

```text
timestamp:
questUrl:
uxState:
anchorProfile:
anchorToRigDistanceM / anchorToRigYawDeltaDeg:
cameraLocalInRig:
centerlineWorld head/upperTorso/pelvis:
top deviating parts:
- part / meshSource / runtimeOffsetClamped / originToBounds / liveToBounds or canonicalToBounds
classification:
next owner:
```

分類は `runtime_anchor`, `hard_centerline`, `part_anchor_runtime_offset`, `glb_origin_bounds`, `mixed` のどれかにする。

## 自動判定 telemetry

Quest URLに `debug=1&qa=centerline` が付いている場合、payloadには `centerlineQa` が入る。展示QAではまず人間がベクトルを読む前にこの値を見る。

```powershell
$latest = Invoke-RestMethod http://127.0.0.1:8010/api/quest-debug/latest
$qa = $latest.record.payload.centerlineQa
$qa.verdict
$qa.classification
$qa.displayLine
$qa.checks.runtimeAnchor
$qa.checks.hardSync
$qa.checks.partAnchorRuntimeOffset.parts
$qa.checks.glbOriginBounds.parts
```

判定キー:

- `pass`: 閾値内。展示続行。
- `runtime_anchor`: `anchorToRigDistanceM` または `anchorToRigYawDeltaDeg`、profile不一致、anchor未ready。まず再センター/anchor capture/snapを疑う。
- `hard_sync_centerline`: anchorは合っているが `cameraLocalInRig.x` または複数partのrig-local横ズレが揃っている。Quest実機由来の頭/中心線同期、`liveHeadPosition`、`liveTorsoYaw` を疑う。
- `part_anchor_runtime_offset`: 特定partの `live/canonicalAnchorToMeshOriginRigLocalM` が閾値超過。runtime placementまたは部位anchor contractを疑う。
- `glb_origin_bounds`: `originToBoundsCenterRigLocalM` が閾値超過。GLB原点と見た目中心がずれているため、modeler修正票に回す。
- `mixed`: 複数分類が同時に出ている。`runtime_anchor` が含まれる場合は先にanchorを直し、同じURLで再取得する。

現在の閾値:

- `anchorToRigDistanceMaxM = 0.05`
- `anchorToRigYawMaxDeg = 3`
- `cameraLocalXMaxM = 0.08`
- `coherentPartLateralMinM = 0.08`
- `partAnchorDeltaMaxM = 0.12`
- `glbOriginToBoundsMaxM = 0.08`

ログ保存:

- `centerlineQa` は既存の `/api/quest-debug` payloadに含まれるため、`/api/quest-debug/latest` と履歴ログの両方で残る。
- VR内/画面上のdebug欄には `qa=centerline` のときだけ `centerline QA pass/pass anchor=OK hard=OK part=0 glb=0` の形式で短く表示される。
- 表示が変化した時だけ追記する。1秒telemetryで同じ行を連打しない。
