# 実行下準備メモ（Lore基点 / Blueprint実行）

更新日: 2026-02-28  
参照元:
- `Lore Bible.md`（Version 1.0 / Draft）
- `blueprint.md`（Version 0.2）

## 1. Loreから固定する制約（実装で破らない）

1. 正規起動条件は固定: `設計 × 適合 × 承認 × 記録 × 封印`。
2. 手順逸脱の公式結果は固定: `起動拒否のみ`（拒否コードで分類）。
3. 変身工程は固定: `B(適合審査) -> C(仮組み) -> D(投影試着)` を経由。
4. 承認と演出は分離: 発声は儀式、実トリガーは承認一致。
5. 体験に出す情報は最小化: 手順・ログ・証明中心、ロア説明は出さない。
6. 文言語彙は固定: `規格/承認/監査/拒否/封印/記録` 軸で統一。
7. 生成AIの役割は固定: 物証生成（Blueprint/Emblem/ログ文）を主用途にする。
8. 保存物は固定: `SuitID, ApprovalID, MorphotypeID, Blueprint, Emblem, Log, Clip, Summary`。

## 2. Blueprintから固定する実行方針

1. 開発順は `SIM-first`（Armory Viewer優先）で進める。
2. 実装トラックは `Track A (Suit Forge)` と `Track B (Transform XR)` の2本。
3. 合流点はデータ契約: `SuitSpec` と `Morphotype` を先に固定する。
4. 開発運用は `Wear Build`（1着立てて着る）を最小ループにする。
5. 展示会安定策として、3Dはモジュール合成を基本にして生成失敗耐性を持つ。

## 3. Gate 0で先に用意した成果物

このターンで以下を追加済み:

- `schemas/suitspec.v0.2.schema.json`
- `schemas/morphotype.v0.2.schema.json`
- `docs/gate0-checklist.md`

狙い:

- 「文章の方針」を「実装可能な契約」に変換する。
- 仕様議論の争点をファイル単位で切り出す。
- Gate 1以降の実装で破壊的変更を防ぐ。

## 4. 現時点の未決定（先に決めるべき順）

1. `SuitID` 採番ルール（SERIES/ROLE/REV/SEQの運用）。
2. `modules` スロットの最小集合（MVPで何部位必須か）。
3. `blueprint/emblem` のファイル保存規約（相対パス構成と命名）。
4. `ApprovalID` の発行元（実サービス/仮発行のどちらで進めるか）。
5. 失敗時フォールバックの優先順位（過去資産再利用ルール）。

## 5. 次の着手（即実行可能）

1. `docs/gate0-checklist.md` の「未決定項目」を埋める。
2. `schemas/*.json` を基準に、`examples/` にサンプルJSONを2件ずつ作る。
3. Armory Viewer側の読み込みコードを `SuitSpec` 必須項目のみで実装する。
