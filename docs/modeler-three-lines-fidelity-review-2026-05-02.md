# モデラー納品確認: 三面図再現性レビュー

Date: 2026-05-02  
Target delivery: `first-three-lines-2026-05-02`  
Checked worktree: `.claude/worktrees/jovial-cohen-4bf60f`

## 結論

今回の納品は、技術受領ゲートは通っています。ただし、元の三面図への再現性はまだ合格にしません。

理由は、3系統が視覚的にかなり似ており、`c02 Rescue Knight Sleek`, `c01 Royal Insect Guardian`, `c15 Final Oath Form` の固有のシルエット、配色、顔、胸、背面、脚部の差分が十分に出ていないためです。

この段階では Web/Quest runtime への本採用は保留します。モデラー側には「procedural first pass は通ったが、三面図 fidelity pass が必要」と返してください。

## 技術確認結果

モデラー作業ツリーでは以下を確認しました。

```powershell
cd C:\dev\codex\gavai-henshin\.claude\worktrees\jovial-cohen-4bf60f

python tools\validate_modeler_delivery_manifest.py --manifest docs\modeler-deliveries\first-three-lines-2026-05-02.delivery-manifest.json
# status=pass / asset_count=30 / reasons=0 / warnings=0

python -m pytest tests\test_validate_modeler_delivery_manifest.py tests\test_validate_variant_catalog.py tests\test_armor_part_variant_catalog.py tests\test_variant_topping_intake.py -q
# 20 passed

python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots
# PASS
```

注意: 報告にあった `--include-delivered-assets` は、この worktree の `validate_variant_catalog.py` では未対応でした。上記のオプションなし strict 検証は PASS しています。

## 技術的には通っている点

- 30/30 variant asset が manifest validator を通過。
- GLB / sidecar / source blend のパスは存在。
- 12枚の review PNG が存在。
- `variant_catalog.json` には30件の line variant が追加済み。
- `line_id` / `source_concept` は catalog 上では追跡可能。

## 合格にできない点

### 1. 3系統の見た目が似すぎている

`line_rescue_knight`, `line_royal_insect`, `line_final_oath` の render は、白/水色の procedural armor 方向に寄りすぎています。元三面図では以下のように大きく違います。

| Line | 元三面図の固有差分 | 今回renderの問題 |
|---|---|---|
| `line_rescue_knight` / c02 | 白/青、鋭い救助騎士、青い visor、胸の cyan core、脚にも青の面 | 白いブロック感が強く、青いボディスーツ/脚部/胸coreが弱い |
| `line_royal_insect` / c01 | 緑/白/金、複眼、触角、V胸、昆虫甲殻、背面の細いウイング感 | c02/c15との差が弱く、緑/複眼/触角/V胸/背面甲殻が読みにくい |
| `line_final_oath` / c15 | 白/金/シアン、王冠visor、金の装飾密度、肩の広がり、全身発光ライン | c01とかなり似ており、金/王冠/最終形の密度が不足 |

### 2. 三面図の「色面」と「基礎スーツ」が再現されていない

元絵は、白い外装だけではなく、基礎スーツの色面が大きな識別要素です。

- c02: 青い脚/腕/胴と白い外装のコントラスト
- c01: 深緑スーツと白/金外装
- c15: 白スーツ、金装飾、シアン発光の高密度な統一感

今のrenderは、基礎スーツの色面が弱く、全体が白い試作装甲に見えます。

### 3. 顔と胸が元案の主役になっていない

特撮スーツは顔と胸で一瞬にして何者かが伝わる必要があります。

- c01 は複眼とV胸。
- c02 は青visorと救助的な胸core。
- c15 は王冠visorと大きな cyan core。

ここが弱いと、いくらmanifestが通っても「三面図を再現した」とは言えません。

### 4. 背面/側面の再現が弱い

元三面図では背面の情報量がかなり重要です。

- c01: 背中中央の緑/白の縦ユニットと甲殻ライン
- c02: コンパクトな青い背面ユニット
- c15: 金/白/シアンの背面大パネルと肩から背中への広がり

今回の納品は背面や側面のライン差分が弱く、3系統の意図が分かれきっていません。

### 5. sidecarに意図の埋め込みが不足

Manifest には `source_concept_ids`, `line_id`, `design_intent_summary` が入っていますが、個別 `.modeler.json` 側には `source_concept_ids` や `design_intent` が見えませんでした。後続のWeb/QuestやNanobanana工程へ渡すには、個別sidecarにも意図を入れてください。

## 差し戻し要件

### 共通

- 元三面図と並べて、front / side / back / 3q を比較できる review sheet を出す。
- 3系統が grayscale でもシルエットで判別できるようにする。
- base suit color blocking を必ず入れる。
- helmet / chest / back / waist / shin / boot の少なくとも6部位で、元案の固有記号を反映する。
- 個別 `.modeler.json` に `source_concept_ids`, `line_id`, `design_intent`, `fidelity_notes` を入れる。

### Line 1: Rescue Knight Sleek

元三面図: `sheet-01-concepts-01-03.png` の2段目。

必須再現:

- 青い visor。
- 胸の cyan triangular/core。
- 白外装 + 青基礎スーツの明確な分離。
- 肩は小さく鋭い rescue knight cap。
- 背面は compact blue spine/back unit。
- すね/ブーツに青と白の分割、接地する靴底。

### Line 2: Royal Insect Guardian

元三面図: `sheet-01-concepts-01-03.png` の1段目。

必須再現:

- 緑の複眼、または複眼に見える visor。
- 触角/crest。ただしQuest視認性のため太めで短め。
- 緑/白/金の配色。
- 胸の明確な emerald V core。
- 肩と背面に昆虫甲殻/翅のニュアンス。
- 脚部も緑/白の色面を残す。

### Line 3: Final Oath Form

元三面図: `sheet-05-concepts-13-15.png` の3段目。

必須再現:

- 王冠状 visor / crest。
- 白/金/シアンの最終形 palette。
- 胸の大きな cyan core。
- 肩から背面へ広がる金/白の高密度外装。
- 腰/脚/ブーツまで金trimとcyan glowがつながる。
- c01と似せず、より豪華で完成形に見える密度にする。

## 次回納品で追加してほしい画像

各lineごとに以下をお願いします。

```text
full_front.png
full_side.png
full_back.png
full_3q.png
source_overlay_front.png   # 元三面図とrenderを横並び or 半透明比較
helmet_closeup_front.png
helmet_closeup_side.png
torso_closeup_front.png
torso_closeup_back.png
boot_closeup_side.png
```

`source_overlay_front.png` は fidelity review の必須にします。厳密なピクセル一致ではなく、シルエット、顔、胸、配色、背面の読みを確認するためです。

## Engineering側の判断

今回の納品は「技術的な土台の確認」としては価値があります。ただし、元三面図再現性を重視する方針では、今の30 variantを main runtime へ本採用しません。

次の進め方:

1. このレビューをモデラーへ返す。
2. 3系統それぞれで fidelity pass を作り直してもらう。
3. 新しい manifest が pass したら、Web Forgeへ staging 表示だけ入れる。
4. Webで元三面図との横比較を確認してから Quest へ送る。
