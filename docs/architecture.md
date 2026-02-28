# Architecture (Provisional)

## Context
本リポジトリは、Lore（世界観）を直接露出せずに、Blueprint（実行計画）を技術検証可能な単位へ分解するための基盤。

## Layers
1. Contract Layer
   - `schemas/suitspec.v0.2.schema.json`
   - `schemas/morphotype.v0.2.schema.json`
2. Rule Layer
   - `config/provisional_rules.json`
   - `src/henshin/ids.py`
3. Execution Layer
   - `src/henshin/forge.py`（ドラフト生成）
   - `src/henshin/transform.py`（プロトコル状態遷移）
   - `src/henshin/archive.py`（成果物保存）
4. Interface Layer
   - `src/henshin/cli.py`

## Integration points
- Track A/B 合流点: `SuitSpec` + `Morphotype`
- セッション永続化: `sessions/<SESSION_ID>/`
- 監査証跡: `DepositionLog.txt` + `AuditSummary.txt`

## Non-goals (current phase)
- Unity実装本体
- mocopi実機連携本体
- 画像生成APIの実呼び出し
