# モデラー向けパーツ別レビューシート

Date: 2026-05-03  
Scope: クリエイターチーム/モデラーが、三面図の意図を1パーツずつ読み取り、Web/Quest採用前に fidelity を確認するためのレビューシート。  
Source images: `docs/assets/hero-suit-triview-2026-05-02/`

## 目的

このシートは、GLBやmanifestが技術的に通ったあとに、元三面図の意匠が「特撮スーツとして人体に装着されているか」を人間の目で確認するために使います。

完全なピクセル模写ではなく、次の4点を確認します。

1. 元三面図の主要記号が、そのパーツに残っていること。
2. VRM/body上の位置と可動域に対して、浮き、刺さり、過剰な厚みがないこと。
3. Web stagingで、front / side / back / 3q / closeup を見ても意図が読めること。
4. Questで、距離、解像度、装着姿勢、視界制限が入っても識別できる面と段差になっていること。

## レビュー前提

対象ライン:

| Line ID | Source concept | 特に読む意匠 |
|---|---|---|
| `line_rescue_knight` | `c02 Rescue Knight Sleek` | 白/青/シアン、青い visor、救助騎士感、compact back、接地するブーツ |
| `line_royal_insect` | `c01 Royal Insect Guardian` | 緑/白/金、複眼、太め短めの crest、emerald V chest、甲殻/翅ニュアンス |
| `line_final_oath` | `c15 Final Oath Form` | 白/金/シアン、王冠状 visor、大きな cyan core、肩から背面へ広がる高密度外装、全身 glow flow |

共通で見ること:

- grayscaleでも `helmet`, `chest`, `back`, `waist`, `shoulders`, `shins`, `boots` の差が読める。
- 基礎スーツの色面分割が外装に消されていない。
- 正面だけでなく、側面と背面にも意匠の説明責任がある。
- 透明/発光だけに頼らず、opaqueな面、段差、ベベルで形状が読める。
- 個別 `.modeler.json` に `source_concept_ids`, `line_id`, `design_intent`, `fidelity_notes` が入っている。

## 判定記号

| 記号 | 意味 |
|---|---|
| OK | 三面図意図、人体位置、Web/Quest視認性が通っている |
| Fix | 形は使えるが、意匠差、色面、厚み、可動逃げ、sidecar記録に修正が必要 |
| NG | 元三面図の記号が読めない、またはWeb/Quest採用前に作り直しが必要 |
| Hold | 判断材料不足。追加render、overlay、closeup、sidecar説明が必要 |

## 必須レビュー画像

各lineごとに、最低限以下を確認します。

```text
full_front.png
full_side.png
full_back.png
full_3q.png
source_overlay_front.png
helmet_closeup_front.png
helmet_closeup_side.png
torso_closeup_front.png
torso_closeup_back.png
boot_closeup_side.png
```

`source_overlay_front.png` は完全一致を見るものではありません。シルエット、顔、胸、配色、脚部、ブーツの読みが元三面図から外れていないかを見るための比較資料です。

## パーツ別レビュー

### helmet

| 項目 | チェック内容 |
|---|---|
| 見るべき意匠 | c02は青い visor と救助騎士らしい鋭い顔。c01は複眼に見える面構成、太め短めの crest、頬/口元/後頭部リム。c15は王冠状 visor / crest と機械的な face plate。 |
| 人体/VRM上の位置 | head bone中心。額、頬、顎、後頭部を包む helmet shell として成立させる。首の回転、顎下、肩との干渉を確認する。 |
| Web確認観点 | front / 3q で顔の向きが読める。line間で visor形状が似すぎない。細部textureだけで複眼や王冠を表現していない。 |
| Quest確認観点 | 近距離で白飛びしない。透明visorや細い発光線が潰れても、目/額/頬の大面と段差でキャラクターが判別できる。 |
| 判定 | OK / Fix / NG / Hold |
| 不備メモ |  |

### chest

| 項目 | チェック内容 |
|---|---|
| 見るべき意匠 | c02は胸の cyan triangular/core と肋骨方向へ回り込む rescue shell。c01は明確な emerald V core と白/金外装。c15は大きな cyan core、左右rib、肩/腰へつながる高密度な金trim。 |
| 人体/VRM上の位置 | spine/chest周辺に追従し、胸郭を包む。腹に刺さらず、腕を下ろしたときに上腕と干渉しない。背面/脇下へつながる torso system として見る。 |
| Web確認観点 | 正面の主役になっている。base suit color blocking が胸甲に消されていない。side viewでただの板に見えない。 |
| Quest確認観点 | 中距離でもcore、V字、rib trimが読める。発光が強すぎて胸形状が白飛びしない。腕IKや呼吸姿勢で胸パーツが浮いて見えない。 |
| 判定 | OK / Fix / NG / Hold |
| 不備メモ |  |

### back

| 項目 | チェック内容 |
|---|---|
| 見るべき意匠 | c02は compact blue spine/back unit。c01は身体に沿う wing-like dorsal shell / 甲殻ライン。c15は spine ridge と rear core、肩から背面へ広がる白/金/シアンの大パネル。 |
| 人体/VRM上の位置 | upper spineから腰へ落ちる背面ユニット。肩甲骨、脇下、腰ベルトと関係を持たせる。ランドセル箱や大翼として独立させない。 |
| Web確認観点 | full_backでline差が読める。side viewで胸/肩/腰とつながっている。背面だけ情報量が薄くならない。 |
| Quest確認観点 | 後ろ姿でも何のlineか分かる。薄すぎてbodyに埋まらず、厚すぎてVRM姿勢やカメラで邪魔にならない。 |
| 判定 | OK / Fix / NG / Hold |
| 不備メモ |  |

### waist

| 項目 | チェック内容 |
|---|---|
| 見るべき意匠 | c02は骨盤を巻く rescue driver。c01は emerald V chest とつながる guardian buckle。c15は belt buckle と side clip、脚へ続く金trim/cyan glow。 |
| 人体/VRM上の位置 | pelvis/hips周辺。腹部に刺さらず、骨盤を一周する belt / driver として成立させる。前屈、腰ひねり、脚上げの逃げを残す。 |
| Web確認観点 | chestからwaist、waistからthigh/shinへ線がつながる。正面だけ大きなバックルにならず、side/backにもベルトの存在がある。 |
| Quest確認観点 | 近距離で腹部クリッピングしない。座り/軽い屈み姿勢でパーツが胴体から浮かない。発光や金trimが細すぎて消えない。 |
| 判定 | OK / Fix / NG / Hold |
| 不備メモ |  |

### shoulders

| 項目 | チェック内容 |
|---|---|
| 見るべき意匠 | c02は小さく鋭い rescue knight cap。c01は翅/甲殻の先端を感じる wing cap。c15は小型finを含む oath guard、肩から背面への広がり。 |
| 人体/VRM上の位置 | left_shoulder / right_shoulder。三角筋を包み、鎖骨側、肩甲骨側、上腕側のつながりを見る。腕上げで首/胸/背中に刺さらない。 |
| Web確認観点 | front / side / backで肩の厚みと端の処理が読める。左右セットで寸法と角度が揃っている。line間で肩シルエットが似すぎない。 |
| Quest確認観点 | 腕を上げても視界や頭部に干渉しない。細いfinやcrestが揺れ物に見えず、硬質パーツとして安定して見える。 |
| 判定 | OK / Fix / NG / Hold |
| 不備メモ |  |

### arms

| 項目 | チェック内容 |
|---|---|
| 見るべき意匠 | c02は青/白の基礎スーツと救助騎士らしい細い外装線。c01は緑/白/金の甲殻的な前腕/上腕ライン。c15は金trimとcyan glowが胸/肩から前腕へ流れる高密度ライン。 |
| 人体/VRM上の位置 | left_upperarm / right_upperarm / left_forearm / right_forearm。肘、手首、肩の可動逃げを残し、硬質パーツを関節に詰めすぎない。 |
| Web確認観点 | 腕が単色の棒になっていない。胸/肩から手元へ色面と溝が続く。左右で意匠が揃い、肘曲げで破綻しない。 |
| Quest確認観点 | コントローラー操作時に手元の視界を邪魔しない。前腕の発光線や細溝がQuest解像度で潰れても、主要面の色分けが残る。 |
| 判定 | OK / Fix / NG / Hold |
| 不備メモ |  |

### hands

| 項目 | チェック内容 |
|---|---|
| 見るべき意匠 | 各lineの基礎スーツ色を手袋まで引き継ぐ。c02は青/白の軽い rescue glove、c01は緑/金の節や甲殻ニュアンス、c15は白/金/シアンの最終フォーム感を小面積で入れる。 |
| 人体/VRM上の位置 | left_hand / right_hand。手甲、指、手首カフを分けて見る。握り、指ポーズ、コントローラー保持を想定し、指関節に硬質装甲を載せすぎない。 |
| Web確認観点 | 手首から前腕への接続が自然。手甲だけが浮いた板に見えない。左右セットでサイズと向きが揃っている。 |
| Quest確認観点 | 一人称視点で大きすぎない。細い指装飾がちらつかず、手元操作の邪魔にならない。発光はアクセントに留める。 |
| 判定 | OK / Fix / NG / Hold |
| 不備メモ |  |

### thighs

| 項目 | チェック内容 |
|---|---|
| 見るべき意匠 | c02は青い脚部基礎スーツと白外装のコントラスト。c01は緑/白の脚部色面と甲殻的な縦線。c15は腰から脚へ続く金trim/cyan glowと完成形らしい密度。 |
| 人体/VRM上の位置 | left_thigh / right_thigh。太もも前面、側面、外腿、内腿の可動を分ける。股関節、膝、腰パーツに干渉しない。 |
| Web確認観点 | waistからshinへ意匠が途切れない。正面だけでなくside viewで脚の厚みと色面が読める。左右の長さと角度が揃う。 |
| Quest確認観点 | 歩行/しゃがみで腰や膝に刺さらない。遠目で脚が単色に潰れず、lineごとの色面差が残る。 |
| 判定 | OK / Fix / NG / Hold |
| 不備メモ |  |

### shins

| 項目 | チェック内容 |
|---|---|
| 見るべき意匠 | c02はすねに沿う青/白の縦流れと rescue stream。c01は細い guardian ridge と ankle trim。c15は脚の発光線と硬質 shell、金trimの連続。 |
| 人体/VRM上の位置 | left_shin / right_shin。膝下から足首まで。膝曲げと足首回転の逃げを残し、膝皿やブーツと接続を分ける。 |
| Web確認観点 | full_frontとboot_closeup_sideで、すねからブーツへの接続が読める。左右セットで高さ、角度、発光位置が揃う。 |
| Quest確認観点 | 低解像度でも縦ridgeや色面が残る。細い線だけに頼らず、面分割と段差で脚部の特徴が読める。 |
| 判定 | OK / Fix / NG / Hold |
| 不備メモ |  |

### boots

| 項目 | チェック内容 |
|---|---|
| 見るべき意匠 | c02は接地する rescue toe guard、toe cap、heel guard、ankle cuff。c01は guardian split toe と甲殻/緑白の記号。c15は oath hero sole、toe、heel、金trim/cyan glowの完成度。 |
| 人体/VRM上の位置 | left_boot / right_boot。足首、甲、つま先、かかと、靴底を分ける。床に浮かず、VRM foot boneの向きと接地面が合う。 |
| Web確認観点 | `boot_closeup_side.png` で、足首、ソール、つま先、すねからブーツへの接続、色面分割が確認できる。足元だけ玩具的に太くならない。 |
| Quest確認観点 | 床接地、移動時の足元、遠目のシルエットを確認する。ソールが薄すぎて消えず、厚すぎて足が重く見えない。 |
| 判定 | OK / Fix / NG / Hold |
| 不備メモ |  |

## ライン別の重点メモ

### `line_rescue_knight`

- 最初の基準スーツなので、軽く、硬質で、公共救助感があることを優先する。
- 青い visor、胸の cyan core、青い脚/腕/胴と白外装の分離を必ず見る。
- backは compact。大きな箱や翼にしない。
- bootsは接地感を最優先し、床から浮くものはNG。

### `line_royal_insect`

- 複眼、crest、emerald V chest、甲殻/翅ニュアンスが一瞬で読めることを優先する。
- 虫っぽさを強めすぎて怪人化しない。明るい守護者のスーツとして見る。
- crestはQuest視認性を考え、細長すぎるものより太め短めを優先する。
- backは大翼ではなく close-to-body の dorsal shell として扱う。

### `line_final_oath`

- c01と似せず、最終フォームとして密度、金trim、cyan glow、王冠状 visor を強める。
- ただし「全部を大きくする」はNG。胸、肩、背面、腰、脚の流れで完成度を出す。
- glow flowは visor/chest/belt/shin/boot まで意味を持ってつながること。
- 金色パーツが身体から浮いて見える場合はFixまたはNG。

## レビュー記入欄

| Line ID | Part | 判定 | 不備メモ | 必要な追加資料 | 再確認者 |
|---|---|---|---|---|---|
| `line_rescue_knight` | `helmet` |  |  |  |  |
| `line_rescue_knight` | `chest` |  |  |  |  |
| `line_rescue_knight` | `back` |  |  |  |  |
| `line_rescue_knight` | `waist` |  |  |  |  |
| `line_rescue_knight` | `shoulders` |  |  |  |  |
| `line_rescue_knight` | `arms` |  |  |  |  |
| `line_rescue_knight` | `hands` |  |  |  |  |
| `line_rescue_knight` | `thighs` |  |  |  |  |
| `line_rescue_knight` | `shins` |  |  |  |  |
| `line_rescue_knight` | `boots` |  |  |  |  |
| `line_royal_insect` | `helmet` |  |  |  |  |
| `line_royal_insect` | `chest` |  |  |  |  |
| `line_royal_insect` | `back` |  |  |  |  |
| `line_royal_insect` | `waist` |  |  |  |  |
| `line_royal_insect` | `shoulders` |  |  |  |  |
| `line_royal_insect` | `arms` |  |  |  |  |
| `line_royal_insect` | `hands` |  |  |  |  |
| `line_royal_insect` | `thighs` |  |  |  |  |
| `line_royal_insect` | `shins` |  |  |  |  |
| `line_royal_insect` | `boots` |  |  |  |  |
| `line_final_oath` | `helmet` |  |  |  |  |
| `line_final_oath` | `chest` |  |  |  |  |
| `line_final_oath` | `back` |  |  |  |  |
| `line_final_oath` | `waist` |  |  |  |  |
| `line_final_oath` | `shoulders` |  |  |  |  |
| `line_final_oath` | `arms` |  |  |  |  |
| `line_final_oath` | `hands` |  |  |  |  |
| `line_final_oath` | `thighs` |  |  |  |  |
| `line_final_oath` | `shins` |  |  |  |  |
| `line_final_oath` | `boots` |  |  |  |  |

## 受領判断

- 全lineの `helmet`, `chest`, `back`, `waist`, `shins`, `boots` がOKでない場合、Web/Quest runtime本採用には進めない。
- Fixがある場合は、Web staging上で元三面図との横比較を行い、修正範囲を部位単位で返す。
- Holdがある場合は、追加renderまたはsidecar追記を待つ。推測でQuestへ送らない。
- 技術validatorがpassしていても、三面図fidelityが弱い場合は `technical pass / fidelity hold` として扱う。
