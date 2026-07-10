# Wave 2 Modeler Order Sheet

Updated: 2026-04-30

## 発注意図

自由に提案してほしい。ただし、Webで「ヒーロースーツの鎧立て」として成立し、Questで同じ姿を呼び出せることを壊さない。
基礎スーツはVRM表面の完成ボディスーツ、外装はその上に装着された硬質シェル、toppingは親moduleに後乗せする追加装飾として扱う。

共通固定条件:

- 18 canonical module名は維持する。
- P0は `helmet`, `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder`, `left_shin`, `right_shin`。
- P0 metadataは `part_family`, `variant_key`, `base_motif_link`, `topping_slots`, `conflicts_with`, `vrm_attachment`, `texture_zone_notes` を持つ。
- Nanobanana前提。単色基礎スーツ、灰色proxy、透明bbox、ランダムSFノイズは最終案にしない。

## 部位別発注表

| 部位 | 固定条件 | 自由提案 | 3案ほしいvariant | 禁止事項 | Web/Questでの確認方法 |
|---|---|---|---|---|---|
| 基礎スーツ `base_suit_surface` | VRM表面に貼る完成ボディスーツ。首、胴、腕、腰、脚へ連続する。 | 守る対象/気質/paletteから、線、色面、発光導線を提案。 | `heroic_clean`, `speed_line`, `guardian_panel` | 単色下着、未完成地肌、暗い泥汚れ、無意味な細線ノイズ。 | Webで外装隙間から完成スーツに見える。Quest recallで同じtexture pointerを読む。 |
| `helmet` | 頭部外装、visor、後頭部、首元との接続を読む。 | crestやvisor形状の個性。顔の印象は明るい特撮寄り。 | `crest_hero`, `visor_sleek`, `antenna_guardian` | ホラー顔、暗すぎる目、頭だけ別作品、視界を塞ぐ巨大crest。 | 正面/3Qで顔の方向が分かる。Questで頭部が浮かず首元に接続する。 |
| `chest` | 胸郭を包む硬質シェル。`base_motif_link` を胸V線などで受ける。 | 中央core、rib trim、左右非対称の小アクセント。 | `v_core`, `broad_plate`, `split_rib` | 平板、透明箱、腹に刺さる箱、基礎スーツ線と無関係な模様。 | Web側面で身体を包む。Questで胴体前に浮かず変身時の主役になる。 |
| `back` | 肩甲骨から腰へ流れる背面装甲。薄板にしない。 | spine ridge、rear core、左右scapula pad。 | `spine_bus`, `wing_base`, `rear_core` | 背負い板、ランドセル箱、z厚みのないタイル。 | Web側面/背面で胸・腰と胴を挟む。Quest背面確認で浮きが目立たない。 |
| `waist` | 骨盤へ巻き付くbelt loop。前後左右の高さを揃える。 | buckle、side clip、背面clasp。 | `hero_buckle`, `side_clip`, `wrap_belt` | 浮いた輪、腰から離れた床物体、脚可動を塞ぐ巨大板。 | Web正面/側面で腰に装着。Questで脚を見ても隙間が破綻しない。 |
| `left_shoulder` / `right_shoulder` | 三角筋を覆い、胸/背中側へ差し込む。左右は基本mirror。 | shoulder fin、edge trim、片側だけの意図的アクセント。 | `sleek_cap`, `winged_fin`, `heavy_guard` | 肩球に乗った小物、腕可動を殺す巨大トゲ、左右意図不明差。 | Web回転で浮かない。Questで腕の動きに対して接続が読める。 |
| 腕 `upperarm` / `forearm` / `hand` | 腕に沿う分割外装。関節に逃げを残す。 | 前腕gauntlet、手甲plate、基礎スーツ線との細い接続。 | `stream_arm`, `gauntlet_core`, `knuckle_plate` | 棒プロキシ、円筒ガイド、肘/手首を塞ぐ一体筒。 | Web正面で腕外装に見える。Questで手首・肘の隙間が自然。 |
| `left_shin` / `right_shin` | 下腿シェル。ブーツ上端へ入るsocket/cuffを持つ。 | shin spike、縦発光線、膝下trim。 | `shin_spike`, `stream_shin`, `knee_trim` | 透明脚プロキシ、ブーツと無関係な板、左右高さズレ。 | Web正面/側面で脚が浮かない。Questでブーツとの継ぎ目が読める。 |
| `left_boot` / `right_boot` | 靴底をfloor planeへ揃える。toe、heel、ankle cuffを持つ。 | toe cap、heel guard、ankle cuff trim。 | `toe_hero`, `ankle_cuff`, `heel_guard` | 接地しない靴、床に置いた別物、すねと離れたブーツ。 | Webで足元が接地。Quest recall後も足元が最初に破綻しない。 |
| topping library | 親moduleが単体合格した後にlocal slotへ載せる。 | 小さく効くcrest/core/fin/buckle/spike案。 | `small`, `hero`, `bold` for each slot | 親moduleの代替、body anchor直取り、視界/可動/接地を壊す装飾。 | WebでON/OFFしても親が成立。Questでmanifestのselected toppingだけが出る。 |

## 造型師向けのOK/NG基準

| 観点 | NG例 | OK例 |
|---|---|---|
| 面 | のっぺりした一枚板、ただの箱、人体から離れた置物。 | 面の重なり、内側面と外側面、曲面ラップ、身体へ沿う返し。 |
| 縁 | エッジが消えた丸い塊、透明箱の輪郭だけ。 | 縁取り、段差、薄いリップ、トリム、面の切り返し。 |
| 接続 | 肩・腰・ブーツが浮く、胸と背面が別物。 | 分割継ぎ目、差し込み、カフ、ベルトループ、前後をつなぐ側面パーツ。 |
| 可動 | 関節を塞ぐ、肘/膝/足首を一体筒にする。 | 関節の逃げ、柔らかい基礎スーツが見える隙間、硬質外装の分割。 |
| 背面 | 背負い板、薄いタイル、平たいランドセル箱。 | spine ridge、scapula pad、lumbar clasp、左右side return。 |
| 光 | ランダムな発光線、全身に均一な細線ノイズ。 | 基礎スーツから外装へ続く発光ライン、core/visor/buckleへ意味を持って集まる光。 |

## 顔/ヘルメット細分

| 要素 | 固定条件 | 自由提案 | 3案ほしいvariant | 禁止事項 | Web/Quest確認 |
|---|---|---|---|---|---|
| visor | 目線と正面方向が読める。明るい特撮ヒーロー寄り。 | 一眼、双眼、細いバイザー、発光縁。 | `single_visor`, `twin_eye`, `slit_glow` | ホラー目、真っ黒で表情不明、視界を塞ぐ装飾。 | Web正面で顔が主役になる。Questで頭部装着時に暗く潰れない。 |
| crest / antenna | 頭頂または額に載るが、頭の外形を壊さない。 | 小さな角、通信アンテナ、額紋章。 | `short_crest`, `signal_antenna`, `forehead_mark` | 巨大すぎる角、髪のようなランダム束、視界干渉。 | 3Qでシルエットが読め、首元から浮かない。 |
| jaw / neck | 首元の基礎スーツへつながる。 | jaw trim、頬plate、後頭部リム。 | `jaw_guard`, `cheek_plate`, `rear_rim` | 頭だけ被り物、首接続なし、後頭部が空洞。 | Web側面で首との接続が見える。Questで頭が分離物に見えない。 |

## 胸腹背中の連続面

胸、腹、背中は別パーツでも、見え方は一つの胴体外装として扱います。

- `chest`: 胸郭を包むfront shell。中央coreとrib trimは基礎スーツの胸ラインを受ける。
- `waist`: 腹下から骨盤へ巻くbelt loop。前面buckle、side clip、背面claspを同じ高さ帯でつなぐ。
- `back`: 肩甲骨から腰へ流れるdorsal shell。spine ridge、scapula pad、lumbar claspで厚みを作る。

依頼する3案:

| 胴体案 | 内容 | 見たい差分 |
|---|---|---|
| `torso_v_core` | 胸V発光からbelt buckleへ落ちる王道案。 | 正面のヒーロー感、発光導線。 |
| `torso_wrap_guard` | 胸、脇、背面が広い面でつながる防御案。 | 側面の装着感、背面厚み。 |
| `torso_split_speed` | 斜め分割面で胸から肩/腰へ流す高速案。 | 面の重なり、左右非対称アクセント。 |

禁止:

- 胸だけ箱、腰だけ輪、背中だけ板に分離すること。
- 腹部に大きな箱を置いて身体へ刺さって見せること。
- 背面を薄くして正面だけで成立させること。

## 肩/腕/手首の密度

肩と腕は、密度を上げすぎると関節が死に、密度が低すぎると棒プロキシに戻ります。

固定:

- 肩は三角筋を覆い、胸/背面へ薄く差し込む。
- 上腕と前腕は分割外装。肘と手首に基礎スーツの逃げを残す。
- 手首はgauntletからhand plateへ細く締める。

3案:

| 腕案 | 内容 | 見たい差分 |
|---|---|---|
| `arm_stream` | 肩から前腕へ一本の差し色ラインが流れる。 | 軽快さ、Web正面の読みやすさ。 |
| `arm_guard` | 前腕gauntletと手甲plateを強める。 | 変身時の装備感、手首の締まり。 |
| `arm_fin` | 肩finと前腕trimを連動させる。 | topping拡張余地、横シルエット。 |

NG:

- 肩球に小物を置くだけ。
- 肘/手首を塞ぐ一体筒。
- 左右差の理由がない非対称。

OK:

- 肩の縁、腕への段差、手首のカフ、発光ラインの継続。
- 関節に基礎スーツが見える分割継ぎ目。

## 腰/ブーツの特撮的処理

腰とブーツは、特撮スーツらしさを最速で伝える部位です。
浮くと一気に玩具の置物に見えます。

固定:

- 腰はbelt loopとして骨盤に巻き付く。
- buckle、side clip、back claspは同じ高さ帯でつながる。
- ブーツはtoe cap、heel guard、sole、ankle cuffを持つ。
- 靴底はfloor planeへ揃える。

3案:

| 案 | 内容 | 見たい差分 |
|---|---|---|
| `belt_hero_buckle` | 中央buckleが胸Vラインを受ける。 | 正面の記号性。 |
| `belt_side_clip` | 左右side clipで腰と脚の隙間を締める。 | 側面の一体感。 |
| `boot_cuff_guard` | ankle cuffがすね装甲を受ける。 | 足元の接地と継ぎ目。 |

NG:

- 腰から離れた輪。
- ブーツが床に置いた別物。
- すねとブーツの間がただの空白。

OK:

- カフ、段差、靴底、つま先/かかとの硬質面。
- すねの発光線がブーツtrimへ入る分割継ぎ目。

## 各部位3案ずつの依頼

各部位は、最初から完成1案に絞らず、次の3方向を出してください。

| 部位 | 案A | 案B | 案C |
|---|---|---|---|
| helmet | `heroic_face` | `sleek_visor` | `crest_guardian` |
| chest | `v_core` | `broad_guard` | `split_rib` |
| back | `spine_ridge` | `scapula_shell` | `rear_core` |
| waist | `hero_buckle` | `side_clip` | `wrap_belt` |
| shoulder | `sleek_cap` | `winged_fin` | `heavy_guard` |
| arm | `stream_arm` | `gauntlet_core` | `knuckle_plate` |
| shin | `stream_shin` | `shin_spike` | `knee_trim` |
| boot | `toe_hero` | `ankle_cuff` | `heel_guard` |

各案には、狙い、`base_motif_link`、干渉しそうな `conflicts_with` を1行で添えてください。

## 納品物

- 各部位のGLB、source blend、front/side/back/3Q preview。
- P0 metadata 8点を含む `modeler.json` 相当メモ。
- 3案variantの名前、意図、`conflicts_with`。
- topping slot位置が分かるcloseupまたは注釈。
- Nanobanana用のmaterial zone意図とUV0確認メモ。

## 納品物の命名規則

基本フォルダ:

```text
viewer/assets/armor-parts/<module>/
  <module>.glb
  <module>.modeler.json
  source/<module>.blend
  preview/<module>_front.png
  preview/<module>_side.png
  preview/<module>_back.png
  preview/<module>_3q.png
  preview/<module>_closeup_<focus>.png
```

variant案:

```text
viewer/assets/armor-parts/<module>/variants/<variant_key>/
  <module>__<variant_key>.glb
  <module>__<variant_key>.modeler.json
  preview/<module>__<variant_key>_front.png
  preview/<module>__<variant_key>_side.png
  preview/<module>__<variant_key>_back.png
  preview/<module>__<variant_key>_3q.png
```

topping案:

```text
viewer/assets/armor-parts/<parent_module>/toppings/<topping_slot>/<topping_key>/
  <parent_module>__<topping_slot>__<topping_key>.glb
  <parent_module>__<topping_slot>__<topping_key>.modeler.json
  preview/<parent_module>__<topping_slot>__<topping_key>_3q.png
```

命名ルール:

- lowercase snake_case。
- module名はcanonical名から変えない。
- `variant_key` は `family_style` ではなく、部位内で短く読める名前にする。例: `v_core`, `spine_ridge`。
- toppingは `parent_module`, `topping_slot`, `topping_key` を必ず名前に含める。
- `.blend1` などのBlender backupは納品しない。

詳細数値は `docs/modeler-new-route-acceptance-spec.md`、体験仕様は `docs/web-hero-armor-stand-one-page-spec.md`、テクスチャ契約は `docs/nanobanana-texture-prompt-contract.md` を参照。
