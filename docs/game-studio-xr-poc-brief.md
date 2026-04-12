# Game Studio XR PoC Brief

更新日: 2026-03-28

## 1. 目的

`Game Studio` は `gavai-henshin` 本線の runtime 置換ではなく、将来の XR 体験を高速に試すための PoC レーンとして使う。

この PoC レーンの責務は次の 3 点に限定する。

1. XR 空間 UI の試作
2. 変身演出のリズム検証
3. headset 向け interaction の仮説検証

## 2. First PoC

固定する最初の体験はこれ。

`pinch -> armor spawn -> body attach preview`

## 3. 世界観

- プレイヤーは空間中央に立つ
- 変身は「召喚」ではなく「装甲ユニットが身体へ再編成される儀式」
- 胸部ユニットが核で、腕・肩・背面ユニットが周囲から集まる
- UI は HUD ではなく、空間中の閾値リング・ガイドライン・attach ghost として表現する

## 4. Interaction Verbs

最小 verbs は以下で固定する。

1. `pinch`
   - 儀式開始
2. `hold`
   - attach preview 維持
3. `release`
   - attach 確定またはキャンセル
4. `head-look`
   - 次の attach ターゲットの確認

## 5. 成功条件

### UX

- 10 秒以内に「変身の始まり」が理解できる
- attach される部位が空間上で迷子にならない
- 胸部ユニットが主導し、腕・肩・背面が従う主従関係が見える

### 技術

- `SuitSpec` / `vrm_anchor` / fit 情報を truth source として再利用できる
- headset PoC 側で simulation truth を持たない
- current viewer と見比べて、部位アンカーの意味が破綻しない

## 6. 禁止事項

- 本線 schema を XR PoC の都合で変えない
- XR PoC 側に `SuitSpec` の新 runtime API を生やさない
- live tracking 品質課題を XR PoC でごまかさない
- 初手から full transformation 全工程を実装しない

## 7. 本線との境界

### 本線が持つもの

- `SuitSpec`
- `Morphotype`
- body-fit canon
- VRM fit
- 装着 truth

### PoC 側が持つもの

- XR 空間 UI
- 演出
- interaction 試作
- attach preview の見せ方

## 8. 役割分担

- current viewer
  - fitting truth source
  - 装着補正の検証環境
- 8thWall
  - WebAR / camera runtime 検討
- XR Blocks / Game Studio
  - headset 向け XR UX の高速 PoC

## 9. Demo Acceptance Criteria

1. pinch で変身シーケンスが開始する
2. armor unit が body anchor へ向かう
3. attach preview が胸・肩・腕の順で読める
4. 失敗時も UX が破綻しない
5. viewer で定義した fit truth と矛盾しない

## 10. 次に作るもの

1. first scene spec
2. prompt template
3. Game Studio 向け scene prompt
4. headset PoC の acceptance checklist
