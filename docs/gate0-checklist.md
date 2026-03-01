# Gate 0 チェックリスト（実行開始前）

## 1. 仕様固定（必須）

- [x] `SuitSpec v0.2` のJSON Schemaが存在する
- [x] `Morphotype v0.2` のJSON Schemaが存在する
- [x] `SuitID` 採番規約（SERIES / ROLE / REV / SEQ）が確定している
- [x] `ApprovalID` と `MorphotypeID` の発行方式が確定している

## 2. 実装前提（必須）

- [ ] Armory Viewerが `SuitSpec` の必須項目だけで起動できる
- [ ] `modules` の最小スロット構成（最低4部位）が確定している
- [ ] Blueprint投影方式（`decal/projector/triplanar`）のMVP採用方式が決まっている
- [x] 生成失敗時に過去資産へフォールバックできる

## 3. 受け入れ条件（Gate 0 DoD）

- [ ] `SuitSpec` JSONを1件読み込み、1着を表示できる
- [ ] `Morphotype` JSONを1件読み込み、体型スライダーへ反映できる
- [ ] SuitID付きで保存し、再読み込みで同一表示を再現できる
- [ ] 下記3指標で最低ラインを満たす

判定指標:
- Silhouette: 遠目で鎧として識別できる
- Joint Safety: 肩・肘・膝で大破綻しない
- Seal Readability: 胸部の封印/意匠が視認できる

## 4. 議論ログ（決めたら追記）

- 決定1: ID規約は `docs/id-policy.md` に固定（`VDA-{SERIES}-{ROLE}-{REV}-{SEQ}`、`APV-########`、`MTP-########`）。
- 決定2: Armory連携のI/O契約は `docs/armory-io-contract.md` に固定（`SuitSpec` + `simulate-body` JSON）。
- 保留1: `SuitPackage` の実バイナリ構成（Unity側ローダー実装時に確定）。
