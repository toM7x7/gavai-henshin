# Wave 1 モデラー発注チェックリスト

Updated: 2026-04-30

## 格納場所

```text
viewer/assets/armor-parts/<module>/
  <module>.glb
  <module>.modeler.json
  source/<module>.blend
  preview/<module>.mesh.json
  textures/
```

詳細な寸法・監査結果は `docs/armor-part-fit-modeler-requests.md` を参照してください。

## 対象パーツ

- P0: `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder`
- P1: `left_upperarm`, `right_upperarm`, `left_forearm`, `right_forearm`
- Web見た目ブロッカー確認: `left_boot`, `right_boot`, `left_shin`, `right_shin`

## P0観点

- 胸・背中・腰が、透明な箱ではなく人体を包む外装に見える。
- 肩が球体に乗った小物ではなく、胸/背中へ差し込まれた肩アーマーに見える。
- 腰ベルトが骨盤に巻き付き、胸装甲と脚の間の隙間を自然に受けている。

## P1観点

- 上腕と前腕が棒状プロキシではなく、腕に沿う分割装甲に見える。
- 肩-上腕-前腕の間に大きな浮きや不自然な隙間がない。
- 透明ガイドやbboxより、装甲の輪郭が先に目に入る。

## Webプレビュー検収

正面、側面、回転で確認します。

- ヒーロースーツを着ている第一印象になっている。
- 半透明プロキシが主役に見えない。
- 肩、腰、足元が浮いて見えない。
- 左右ペアのサイズ差が意図しない差に見えない。
- 足元はWave 2対象でも、靴底の接地感だけ先に確認する。

## 納品チェック

- 各対象moduleに `<module>.glb` と `<module>.modeler.json` がある。
- `modeler.json` に `bbox_m`, `triangle_count`, `material_zones`, `vrm_attachment.primary_bone` が入っている。
- `base_surface` のmaterial zoneがある。
- 正面/側面/回転のWebプレビュー確認画像、または同等の確認メモを添える。

## 確認コマンド

```bash
python tools/validate_armor_parts_intake.py
python tools/audit_armor_part_fit_handoff.py --format markdown --output docs/armor-part-fit-modeler-requests.md
```
