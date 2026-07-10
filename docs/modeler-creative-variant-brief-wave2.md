# Modeler Creative Variant Brief Wave 2

Updated: 2026-04-30

このブリーフは、Wave 2のモデラー/デザイナー向けに「自主制作で提案してよい余白」と「ランタイムが固定する契約」を分けて渡すためのものです。目的は、既存のWeb Forge、Quest変身体験、GLBアーマーパーツ契約と矛盾せずに、プロシージャルな仮パーツを「 believable な特撮ヒーロースーツのシルエット」へ寄せることです。

## 1. ロアと変身体験の意図

Web側は、ユーザーが自分のヒーロースーツを設計して確定する「Forge」です。ここでスーツIDとリコールコードが発行され、Quest側はその同じスーツを呼び出して、ユーザー本人の周囲に装甲が形成される変身体験を行います。

Quest側で新しいテクスチャや別スーツを生成して補正する前提にはしません。QuestはWebで確定したSuitSpec/manifestを呼び出し、キャリブレーション、スキャン、各パーツのステージング、収縮、シール、アクティブ待機までを「同じスーツが身体へ装着される」体験として見せます。

目指す読後感は、暗いSF倉庫の装備試験ではなく、明るく検分できる特撮ヒーロースーツです。ベーススーツはただの下着やプレーンなインナーではなく、ゴム/布地の質感、身体に沿うパネルライン、細い発光ガイド、色分けを持つ完成済みのボディスーツです。GLBアーマーはその上に載る硬質な外装で、ベーススーツのラインや色面を受けて、胸、背中、腰、肩、腕、脚、ブーツまで連続して見える必要があります。

Wave 2で特に解消したい読みは次の通りです。

- 胸は前面の箱ではなく、肋骨へ回り込む連続したチェストシェルにする。
- 背中は薄い板やバックパックではなく、肩甲骨から脊椎へつながる厚みのあるドーサルシェルにする。
- 腰/ベルトは浮いたリングではなく、骨盤の近くに密着した変身ドライバー/ベルトとして読む。
- 肩、前腕、脛は身体の外側へ置いた小物ではなく、身体を覆う外装シェルとして読む。
- ブーツは足首と甲、踵、つま先を包み、地面に接地する。足元に浮いたスラブは不可。

## 2. モデラーが自主的に提案してよい範囲

モデラーは、固定契約を守る範囲で、各部位につき3案程度のバリアントを自主提案できます。提案はラフメッシュ、スケッチ、GLB試作、またはデザインノートのいずれでも構いませんが、最終候補はWeb/Questの同一スーツ体験に乗ることを前提にしてください。

提案してよいもの:

- 部位ごとのシルエット差分。ただしターゲットエンベロープとアタッチメント契約内に収める。
- 既存モチーフを受けたパネルライン、トリム、発光ライン、メカ/生体/儀礼的ディテール。
- `variant_key`の追加候補。例: `sleek`, `heavy`, `tech`, `organic`, `heroic`, `winged`から派生した命名。
- `base_motif_link`の提案。どのベーススーツの線、色面、発光ガイドを外装へ連続させるかを明記する。
- `texture_zone_notes`の提案。最終生成はNano Banana前提だが、素材/色面/発光の意図はモデラー側から出してよい。
- トッピング候補。例: crest、visor trim、chest core、spine ridge、belt buckle、shoulder fin、shin spike。ただし親モジュールはトッピングなしでも成立すること。
- 意図的な左右非対称。片側だけの武装、傷、記章などは提案可。ただし寸法差や意図をメタデータで明記する。

提案してはいけないもの:

- 18個のcanonical module名、primary attachment slot、座標系、単位、GLB出力契約の変更。
- Quest側での再生成や補正を前提にした造形。
- トッピングなしでは成立しない親パーツ。
- ベーススーツと無関係な飾りだけの外装。

## 3. 固定するGLB/scale/pivot/material/topping slot契約

### Canonical modules

固定モジュールは次の18個です。名前は変更しません。

- `helmet`
- `chest`
- `back`
- `waist`
- `left_shoulder`, `right_shoulder`
- `left_upperarm`, `right_upperarm`
- `left_forearm`, `right_forearm`
- `left_hand`, `right_hand`
- `left_thigh`, `right_thigh`
- `left_shin`, `right_shin`
- `left_boot`, `right_boot`

Webプレビューの目標は18/18 GLBパーツ、fallback 0です。最重要のruntime coreは`helmet`, `chest`, `back`です。

### Scale and orientation

- 単位はメートル。
- 参照身体は170 cm級のVRMプレビュー。
- glTFはY-up。
- local axesは既存契約に従い、x=lateral、y=vertical/proximal-distal、z=outwardを前提にする。
- 各GLBはエクスポート前にtransformを適用する。
- primary bone/attachment slotの座標フレームは変えない。
- local originはパーツのpivot centerに置く。
- variantは同じcanonical moduleを差し替えるだけで、同じslotに装着できること。

### Envelope targets

ターゲット寸法は既存acceptance specを基準にする。目標は±10%以内、±15%超はfail領域として扱う。

| Module family | Target bbox x/y/z m | Clearance m | Shell thickness m | Tri target |
| --- | ---: | ---: | ---: | ---: |
| helmet | 0.2856 / 0.3400 / 0.2584 | 0.018 | 0.035 | 1800 |
| chest | 0.6392 / 0.4992 / 0.1632 | 0.024 | 0.045 | 1800 |
| back | 0.5984 / 0.5148 / 0.1360 | 0.026 | 0.050 | 1600 |
| waist | 0.4896 / 0.1716 / 0.1904 | 0.022 | 0.034 | 1200 |
| shoulder | 0.1904 / 0.1224 / 0.1632 | 0.028 | 0.038 | 900 |
| upperarm | 0.1088 / 0.2924 / 0.1088 | 0.018 | 0.028 | 1100 |
| forearm | 0.1020 / 0.2788 / 0.1020 | 0.018 | 0.028 | 1100 |
| hand | 0.1156 / 0.0816 / 0.1360 | 0.014 | 0.020 | 700 |
| thigh | 0.1360 / 0.3956 / 0.1292 | 0.020 | 0.030 | 1100 |
| shin | 0.1156 / 0.3956 / 0.1156 | 0.020 | 0.030 | 1100 |
| boot | 0.1224 / 0.0884 / 0.2856 | 0.018 | 0.032 | 900 |

左右ペアの寸法差は原則3%以内です。意図的な非対称は`variant_key`またはメタデータで明記してください。

### Material zones

最低限、次のmaterial zoneを安定名で持たせます。

- `base_surface`
- `accent`
- `emissive`
- `trim`

`base_surface`は必須です。UV0を持ち、主要な重なりがないこと。灰色プロキシ、bbox表示、透明ガイド、未確定の単色マテリアルを最終見えとして扱わないでください。

### Metadata

P0パーツには最低限、以下のメタデータを付けます。対象は`helmet`, `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder`, `left_shin`, `right_shin`を優先し、可能なら全18パーツに展開してください。

- `part_family`
- `variant_key`
- `base_motif_link`
- `topping_slots`
- `conflicts_with`
- `texture_zone_notes`

### Topping slots

トッピングは親モジュールのlocal slotに付く小物です。親パーツのシルエット、fit、texture reviewを成立させるための必須要素にはしません。

| Parent | Slot candidates | Max bbox target m |
| --- | --- | ---: |
| helmet | `crest`, `visor_trim` | crest 0.08 / 0.12 / 0.06 |
| chest | `chest_core`, `rib_trim` | core 0.14 / 0.12 / 0.035 |
| back | `spine_ridge`, `rear_core` | ridge 0.12 / 0.20 / 0.040 |
| waist | `belt_buckle`, `side_clip` | buckle 0.16 / 0.08 / 0.035 |
| shoulder | `shoulder_fin`, `edge_trim` | fin 0.10 / 0.12 / 0.040 |
| shin | `shin_spike`, `ankle_cuff_trim` | spike 0.06 / 0.12 / 0.040 |

各トッピングは`parent_module`, `topping_slot`, `slot_transform`, `max_bbox_m`, `conflicts_with`を宣言します。身体側のanchorを奪わず、親モジュール側のlocal mountとして扱います。

## 4. 顔・胸・腰・背中・腕・脚・手足の細部パーツ候補

### 顔 / helmet

- 複眼風または一眼バイザーのレンズ面。
- 額のcrest、アンテナ、短いホーン、発光シール。
- 頬のインテーク、顎ガード、口元のスリット。
- 耳側の丸ポート、サイドフィン、通信モジュール。
- visor trimと頬ラインを胸のVラインへつなぐ。

### 胸 / chest

- sternum core、V字またはY字の発光ライン。
- clavicle shelf、胸筋シェル、肋骨へ回り込むside return。
- rib trim、胸中央の変身紋章、左右の小パネル。
- 腹上部へ落ちる短いセンターライン。
- 背中パーツへ続く肩甲帯の連続ライン。

### 腰 / waist

- belt buckle、driver window、変身カートリッジ、認証レンズ。
- side clip、hip guard、骨盤に沿うlow pelvis lip。
- 背面のrear clasp、短いケーブル/発光ライン。
- 前垂れではなく、骨盤へ近い薄いベルト構造。
- 胸のcoreや背中のspine ridgeと意味がつながる記号。

### 背中 / back

- spine ridge、rear core、肩甲骨パッド。
- 肩から背中へ回るlat return。
- 背面の発光バス、冷却ベント、変身後のロック機構。
- 小さな後頭部から背中への流れ。
- 薄板ではなく、胸と対になる厚みのあるドーサルシェル。

### 腕 / shoulders, upperarms, forearms

- 肩のdeltoid cup、胸/背中へ食い込むshoulder return。
- 上腕のベーススーツ線に合わせた短い外装帯。
- 前腕のvambrace、wrist cuff、肘可動の逃げ。
- edge trim、発光スリット、左右で意味を持つ小型ギア。
- 武器化しすぎず、腕を包む外装シェルとして成立させる。

### 脚 / thighs, shins

- 大腿外側のライン、膝下へ落ちるspeed stripe。
- 脛正面のVライン、calf return、ankle cuff trim。
- 膝の小さなリップやプロテクター。ただし可動を塞がない。
- shin spikeは任意トッピングで、親の脛シェルは単独で成立させる。
- 足元へ向けて軽く絞り、ブーツと連続させる。

### 手足 / hands, boots

- 手はベースグローブを主にし、外側にknuckle plate、hand plate、短いcuff lockを足す。
- 手のひら側は握りや操作を邪魔しない。
- ブーツはtoe cap、instep plate、heel cup、ankle cuff、sole railを候補にする。
- 足首と甲を包み、つま先が地面へ接地する。
- 足元の発光は接地感を壊さず、靴底の外周や甲の短いラインへ入れる。

## 5. 1部位あたり3案程度のvariant方針

| 部位 | Variant A | Variant B | Variant C |
| --- | --- | --- | --- |
| 顔 / helmet | `heroic_clean_mask`: 大きな明るいバイザー、短いcrest、頬ラインを胸へ接続 | `compound_eye_signal`: 複眼レンズ、額シール、耳ポートで変身デバイス感を強める | `crest_commander`: 高めのcrestと顎ガード。主役感を出すがbbox内に抑える |
| 胸 / chest | `heroic_v_core`: 中央V coreと肋骨へ回るshell return | `rib_wrap_plate`: 左右rib trimを強調し、胸と背中を環状に見せる | `ceremonial_sternum`: 紋章的coreと細い発光線で儀式性を出す |
| 腰 / waist | `driver_buckle_low`: 骨盤近くの低いdriver buckle、前面は薄く密着 | `side_clip_runner`: side clipとhip guardを強め、可動と速度感を優先 | `rear_clasp_belt`: 背面claspと短いラインで背中パーツと接続 |
| 背中 / back | `spine_bus_shell`: spine ridgeとrear coreを中心に、厚みのある背面を作る | `scapula_wrap`: 肩甲骨パッドとlat returnで胸/肩と連続 | `compact_rear_core`: 小型rear coreと冷却ベント。薄板化しない範囲で軽量化 |
| 腕 / arm set | `sleek_vambrace`: 前腕の流線型vambraceと短いwrist cuff | `pauldron_return`: 肩の外装を胸/背中へ噛ませ、prop感を消す | `tech_gauntlet`: 手首周辺の小型発光と操作部。手の可動を残す |
| 脚 / leg set | `runner_shin`: 脛の前面Vと足首への絞りでスピード感 | `guardian_knee`: 膝下リップとcalf returnで守備的に見せる | `blade_line`: shin_spikeは任意トッピングに留め、親シェルは細身に成立 |
| 手 / hands | `knuckle_glow`: knuckle plateと短い発光点 | `cuff_lock`: glove cuffを外装化し、前腕と接続 | `soft_plate`: 手甲だけ硬質、指と掌はベーススーツを主役にする |
| 足 / boots | `grounded_toe`: toe capとinstep plateで足の包み込みを明確化 | `ankle_driver`: ankle cuffと側面小パネルで変身機構感 | `speed_sole`: sole railと踵カップで接地しつつ軽快に見せる |

各variantは、単独で成立する親パーツを先に作り、その後にトッピングの相性を見ます。トッピングで情報量を増やす場合も、胸、背中、腰、肩、脛、ブーツの大きな読みに勝たせないでください。

## 6. NG集

- 胸だけが前に貼り付いた箱。肋骨方向への回り込みがないもの。
- 背中が薄い板、ただの蓋、または巨大なバックパックに見えるもの。
- 腰ベルトが身体から浮いたリングに見えるもの。
- 肩、前腕、脛が身体から離れた小道具に見えるもの。
- ブーツが足から浮いたスラブ、足首のないサンダル、接地しない厚板に見えるもの。
- ベーススーツが単色の下着、灰色プロキシ、未完成インナーに見えるもの。
- 外装がベーススーツの線、色面、発光ガイドと無関係なもの。
- 透明ガイド、bbox、デバッグボックス、proxy materialを最終デザインとして残すもの。
- 暗く泥っぽいSF、ホラー、ポストアポカリプス、倉庫装備試験の方向。
- canonical module名、GLB単位、pivot、attachment slot、material zone名を変更するもの。
- 親パーツなしでは成立しないトッピング、または身体側anchorへ直接刺さるトッピング。
- 左右ペアの寸法差が3%を大きく超えるのに意図が書かれていないもの。
- Webの正面/側面/背面/3/4確認で読めない過密ディテール。
- Quest側の再生成、スケール補正、隠し当たり判定で成立させる前提。

## 7. 納品チェックリスト

モデラー納品前に、次を確認してください。

- 18個のcanonical module名を変更していない。
- 対象パーツのGLB、source `.blend`、sidecar metadata、preview/review画像が揃っている。
- GLBはメートル単位、Y-up、transform適用済み、local originがpivot center。
- target bboxは±10%目標内。±15%を超える軸がない。
- 左右ペアは原則3%以内。非対称は意図と寸法差を明記している。
- `base_surface`, `accent`, `emissive`, `trim`のmaterial zoneが安定名で存在する。
- UV0があり、主要な重なりがない。
- `part_family`, `variant_key`, `base_motif_link`, `topping_slots`, `conflicts_with`, `texture_zone_notes`を記入している。
- トッピングは`parent_module`, `topping_slot`, `slot_transform`, `max_bbox_m`, `conflicts_with`を宣言している。
- 親パーツはトッピングなしでもシルエット、fit、texture reviewを通る。
- 胸、背中、腰、肩、前腕、脛、ブーツが外装シェルとして読める。
- ブーツは足首/甲/踵/つま先を包み、接地感がある。
- ベーススーツと外装のライン/色面/発光ガイドが連続している。
- 最終テクスチャ生成はNano Banana前提で、proxy/cache/fallbackを最終品質として扱っていない。
- Quest側での再生成や補正を前提にしていない。
- Web armor standの正面、側面、背面、3/4 viewで、特撮ヒーロースーツとして明るく検分できる。
