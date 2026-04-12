# VRM-First Authoring Plan

更新日: 2026-04-12

## 1. 方針

従来は `Armor First -> VRM Fit` の順で進めていたが、今後は `VRM First -> Armor Authoring -> Parametric Variation` を基準にする。

理由は明確です。

- 先に基準VRMを決める
- そのVRMに沿う原型メッシュを作る
- 可変パラメータは原型の微調整に限定する
- 画像生成やUVテクスチャ生成は最後に乗せる

この順序にしないと、fit engine が永遠に後始末になる。

## 2. 実行順序

1. `default.vrm` を authoring baseline として固定する
2. `authoring-audit` で 18 部位を `rebuild / tune / keep` に分類する
3. `Wave 1 -> Wave 2 -> Wave 3` の順で補正する
4. 各 wave の完了ごとに `fit-regression` を再実行する
5. `default.vrm` が安定したら第2 baseline VRM を追加する

## 3. Wave 設計

### Wave 1

- 対象: `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder`, `left_upperarm`, `right_upperarm`, `left_forearm`, `right_forearm`
- 目的: 胸背腰と腕系の接続を VRM 基準で安定させる
- 最優先 seam:
  - `shoulder -> upperarm`
  - `upperarm -> forearm`
  - `chest -> back -> waist`

### Wave 2

- 対象: `left_thigh`, `right_thigh`, `left_shin`, `right_shin`, `left_boot`, `right_boot`
- 目的: 下半身の接続と足首まわりを VRM 基準で安定させる
- 最優先 seam:
  - `waist -> thigh`
  - `thigh -> shin`
  - `shin -> boot`

### Wave 3

- 対象: `helmet`, `left_hand`, `right_hand`
- 目的: 頭部と末端部位を仕上げて展示品質へ寄せる

## 4. 判定基準

### `rebuild`

- VRM 基準で原型再制作
- 条件:
  - critical surface violation がある
  - critical part score が `58` 未満
  - symmetry drift が許容外

### `tune`

- 既存メッシュ補正 + fit 再校正
- 条件:
  - critical ではないが surface violation がある
  - hero overflow がある
  - part score が `82` 未満

### `keep`

- 現状維持
- 条件:
  - baseline 再回帰で `summary.canSave == true`
  - 顕著な接続破綻がない

## 5. 監査の見方

`authoring-audit` には以下の診断が出る。

- `weak_pairs`
  - 接続が弱いペア。今どの seam が支配的に悪いかを見る
- `min_scale_lock_axes`
  - `auto-fit` が出した縮小解を `minScale` が潰している軸
- `surface_violation_count`
  - VRM 表面に対して足りないか、盛りすぎかの件数
- `hero_overflow_count`
  - 演出的な盛り量が policy を超えている件数

実務上は `weak_pairs` と `min_scale_lock_axes` を先に見て、mesh を直すべきか fit を直すべきかを切る。

## 6. 部位ごとの authoring 指針

- `helmet`
  - 頭部 proxy に合わせて被る。発光面やバイザーは別層で扱う
- `chest / back / waist`
  - 3 パーツで連続する torso shell として設計する
- `shoulder`
  - 肩は一枚板にせず、upperarm との接続文法として作る
- `upperarm / forearm`
  - 真円よりも VRM の腕に沿うカプセル系で作る
- `thigh / shin`
  - 可動優先。外周のボリュームは hero allowance に逃がす
- `boot`
  - `foot_obb` 基準で足首と甲の seam を先に固める
- `hand`
  - 末端表現は控えめにして、forearm 側の接続を優先する

## 7. コマンド

baseline 回帰:

```powershell
python tools/run_henshin.py fit-regression --root .
```

authoring backlog 生成:

```powershell
python tools/run_henshin.py authoring-audit --root . --output-json sessions/authoring-audit.json --output-md sessions/authoring-audit.md
```

## 8. ルール

- mesh の再制作は `Wave 1` から始める
- `rebuild` 判定の部位から先に着手する
- authoring 中は `Bridges: Off` で純粋な装甲形状を確認する
- save 可否の判断は viewer の見た目ではなく `fit-regression` と `authoring-audit` を truth source にする
- 第2 baseline VRM の追加は `Wave 1` が安定してから行う
