# モデラー発注票: まず作る3系統

Date: 2026-05-02  
Source images: `docs/assets/hero-suit-triview-2026-05-02/`  
Runtime premise: Web Forge / Quest recall の既存18 module、既存 variant/topping 選定は壊さない。

## 発注の狙い

15案すべてを一気に作るのではなく、まず3系統で「特撮スーツとして成立する基準」を作ります。モデラー側には形状解釈、分割、厚み、面構成、制作的な逃げを任せます。一方で、Web/Questへ受け取るための module 名、キー、納品構造は固定します。

重要: 元の三面図への再現性を重視します。完全なピクセル模写ではありませんが、シルエット、顔、胸、背面、色面、発光ラインの主要記号は元案から読み取れる必要があります。manifest が通っても、三面図 fidelity が弱いものは本採用しません。

今回の3系統:

| Priority | Line ID | Source concept | 役割 | 画像 |
|---|---|---|---|---|
| 1 | `line_rescue_knight` | `c02 Rescue Knight Sleek` | 最初の基準スーツ。公共性、白系、装着感、Web/Quest検証の基準。 | `sheet-01-concepts-01-03.png` |
| 2 | `line_royal_insect` | `c01 Royal Insect Guardian` | 特撮らしい顔と胸の記号性。複眼、V胸、背面ウイングの象徴型。 | `sheet-01-concepts-01-03.png` |
| 3 | `line_final_oath` | `c15 Final Oath Form` | 密度と完成度の上限目標。王冠 visor、金/シアン、全身 glow flow。 | `sheet-05-concepts-13-15.png` |

補助参照:

- `c05 Cyber Oath Runner`: 全系統共通の base suit line / circuit seam / Nanobanana texture prompt 参考。
- `c11 Avian Flight Form`: 背面と肩の薄い羽状ラインの参考。大型翼ではなく close-to-body。

## 共通固定条件

### Runtime

- 18 canonical module 名は変更しない。
- `module:base` は canonical GLB を指す。variantへ移さない。
- 新しい名前はまず `proposed_variant_key` / `proposed_topping_key` として提案する。
- Web/Quest入稿時は、Engineering 側で既存 `variant_catalog.json` の key へマッピングしてから受け取る。
- 左右パーツは原則セット納品。

### 造形

- スーツは「体表に貼った基礎ボディスーツ + その上に載る硬質外装」として作る。
- 胸、背中、腰は別々の板ではなく、身体を一周する torso system として見せる。
- 側面と背面に情報を入れる。正面だけ成立する造形はNG。
- 透明や発光は演出用。形状の読みやすさは opaque な面と段差で確保する。
- コスプレ制作を想定し、分割線、重なり、固定位置、可動逃げを意識する。

### 納品

各系統につき、最初は P0 部位を優先:

- `helmet`
- `chest`
- `back`
- `waist`
- `left_shoulder` / `right_shoulder`
- `left_shin` / `right_shin`
- `left_boot` / `right_boot`

余力があれば:

- `left_forearm` / `right_forearm`
- `left_upperarm` / `right_upperarm`
- `left_hand` / `right_hand`
- `left_thigh` / `right_thigh`

納品ファイル:

```text
GLB
modeler.json
source/*.blend
front / side / back / 3q preview PNG
必要なら textures/
```

## Line 1: Rescue Knight Sleek

Source: `c02 Rescue Knight Sleek`  
Sheet: `docs/assets/hero-suit-triview-2026-05-02/sheet-01-concepts-01-03.png`

### 目的

最初にWeb/Questへ入れる基準スーツです。白/パール系、コバルト/シアン、公共救助感を持たせつつ、鎧としては軽く、硬質で、シュッとした印象にしてください。

### 見た目の方向

- 白/パールの基礎スーツに、青/シアンの発光線。
- 胸は大きな箱ではなく、肋骨方向に回り込む滑らかな chest shell。
- 肩は大きすぎない cap。上腕の動きを邪魔しない。
- 背中は薄い spine unit と compact dorsal plate。ランドセル箱にしない。
- ブーツは接地感を優先。toe cap、heel guard、ankle cuff が読めること。

### 依頼する初回パーツ

| Module | Proposed direction | Notes |
|---|---|---|
| `helmet` | `proposed_variant_key: helmet:rescue_sleek` | visor は細すぎず、顔の向きが正面/3Qで読める。 |
| `chest` | `proposed_variant_key: chest:rescue_wrap` | 胸郭を包む。中央 core から rib trim へ流す。 |
| `back` | `proposed_variant_key: back:compact_spine` | 肩甲骨から腰へ細く落ちる。厚みは控えめ。 |
| `waist` | `proposed_variant_key: waist:rescue_driver` | 骨盤を巻く。腹に刺さらない。 |
| `left_shoulder` / `right_shoulder` | `proposed_variant_key: shoulder:sleek_rescue_cap` | 小さめ、丸み、端に機械ベベル。 |
| `left_shin` / `right_shin` | `proposed_variant_key: shin:rescue_stream` | すねに沿う縦流れ。膝と足首に逃げ。 |
| `left_boot` / `right_boot` | `proposed_variant_key: boot:rescue_toe_guard` | 接地、toe cap、ankle cuff。 |

### NG

- 白い箱を胸や背中に置くだけ。
- 透明パーツだけで形状を読ませる。
- ブーツが床から浮く。

## Line 2: Royal Insect Guardian

Source: `c01 Royal Insect Guardian`  
Sheet: `docs/assets/hero-suit-triview-2026-05-02/sheet-01-concepts-01-03.png`

### 目的

特撮ヒーローとしての顔と記号性を強くする系統です。複眼、V字胸、背面の羽/甲殻ニュアンスを使います。ただし昆虫怪人ではなく、明るい守護者のスーツにしてください。

### 見た目の方向

- emerald / white / gold を中心に、明るい heroic palette。
- ヘルメットは compound-eye 的な面構成。ただし細かい粒は texture でよく、GLBは大面と段差を優先。
- 胸は V core が明確。base suit の線から外装へつながる。
- 背面は wing-like dorsal shell。実翼ではなく、身体に沿う薄い甲殻。
- 肩は翅の先端を感じるが、腕可動を邪魔しない。

### 依頼する初回パーツ

| Module | Proposed direction | Notes |
|---|---|---|
| `helmet` | `proposed_variant_key: helmet:compound_guardian` | 目、頬、口元、後頭部リムを分ける。 |
| `chest` | `proposed_variant_key: chest:emerald_v_core` | V字 core と rib trim。正面の主役。 |
| `back` | `proposed_variant_key: back:wing_shell_close` | 翅モチーフを close-to-body にする。大翼NG。 |
| `waist` | `proposed_variant_key: waist:guardian_buckle` | V core とつながる belt buckle。 |
| `left_shoulder` / `right_shoulder` | `proposed_variant_key: shoulder:wing_cap` | 肩から背中側へ薄く返す。 |
| `left_shin` / `right_shin` | `proposed_variant_key: shin:guardian_ridge` | 細い縦 ridge と ankle trim。 |
| `left_boot` / `right_boot` | `proposed_variant_key: boot:guardian_split_toe` | 足先に記号を入れるが、接地を優先。 |

### NG

- 虫っぽさが強すぎて怪人化する。
- 背面が羽根として大きく広がりすぎる。
- 複眼を小粒メッシュだけで作り、Questで潰れる。

## Line 3: Final Oath Form

Source: `c15 Final Oath Form`  
Sheet: `docs/assets/hero-suit-triview-2026-05-02/sheet-05-concepts-13-15.png`

### 目的

完成度と密度の上限を作る系統です。最初から全部を作り切るより、Line 1/2で得た装着基準を使い、より細かい面、冠状 visor、金/シアンの発光、全身の統一感を入れます。

### 見た目の方向

- pearl / gold / cyan の明るい最終形。
- 頭、胸、腰、背面、脚まで発光ラインが意味を持ってつながる。
- 胸は大きくなってよいが、腹と腕に干渉しない。
- 背面は薄くても存在感を出す。spine ridge と rear core を分ける。
- すねとブーツは「足元で完成度が落ちない」ことを重視。

### 依頼する初回パーツ

| Module | Proposed direction | Notes |
|---|---|---|
| `helmet` | `proposed_variant_key: helmet:oath_crown_visor` | crown visor と face plate。王冠に寄せすぎず機械的に。 |
| `chest` | `proposed_variant_key: chest:oath_core_shell` | 中央 core、左右 rib、肩への流れ。 |
| `back` | `proposed_variant_key: back:oath_spine_rear_core` | spine ridge と rear core を分離。背面の主役。 |
| `waist` | `proposed_variant_key: waist:oath_driver_ring` | belt buckle と side clip で腰を巻く。 |
| `left_shoulder` / `right_shoulder` | `proposed_variant_key: shoulder:oath_guard_fin` | 小型 fin。大型化しすぎない。 |
| `left_shin` / `right_shin` | `proposed_variant_key: shin:oath_glow_guard` | 脚の発光線と硬質 shell を両立。 |
| `left_boot` / `right_boot` | `proposed_variant_key: boot:oath_hero_sole` | sole / toe / heel を明確化。 |

### NG

- 最終形だからといって全部を大きくする。
- 金色パーツが身体から浮く。
- 線がランダムで、visor/chest/belt/shin/boot の流れが切れる。

## 初回レビュー画像

各系統で最低限ほしい画像:

- full suit front
- full suit side
- full suit back
- full suit 3q
- helmet closeup front / side
- torso closeup front / side / back
- boot closeup side / front

Web/Quest移植判断では、特に side/back を重視します。現状の課題は「正面はよくても背面が薄い」「腰や背中が浮く」「足元が玩具化する」なので、ここを潰せる資料が必要です。

三面図再現性レビュー用に、各系統で `source_overlay_front.png` または元三面図とrenderを横並びにした比較画像も提出してください。

## 入稿前チェック

納品前に以下を確認してください。

```bash
python tools/validate_modeler_delivery_manifest.py --manifest <delivery-manifest.json>
```

Engineering側で追加確認:

```bash
python tools/validate_armor_parts_intake.py --root viewer/assets/armor-parts
python tools/validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --include-delivered-assets
python tools/smoke_web_glb_load.py
```

## まずの依頼文

モデラーさんへ送る短文:

> 15案の中から、まず `c02 Rescue Knight Sleek`, `c01 Royal Insect Guardian`, `c15 Final Oath Form` の3系統を優先したいです。完全な模写ではなく、特撮スーツとして人体に装着できるよう、基礎スーツ、胸/背面/腰、ヘルメット、肩、すね、ブーツへ分解して再設計してください。Web/Questでは既存18 module構造で受け取るため、創作案は proposed key として出していただき、入稿時にこちらで既存 catalog key へマッピングします。正面だけでなく側面/背面の装着感、可動逃げ、足元の接地感を重視します。
