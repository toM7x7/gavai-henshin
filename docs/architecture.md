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
   - `src/henshin/bodyfit.py`（全身セグメント装着追従）
   - `src/henshin/part_prompts.py`（部位別画像生成プロンプト）
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

## WebAR Stack Note (2026-03-03)
- 8thwall is a first-class candidate stack for WebAR and live camera pipeline features in this repository.
- Current implementation already adopts an 8thwall-style camera pipeline module structure in viewer/body-fit.
- Future related architecture changes should include a short 8thwall decision note in docs.

## Concept-Driven Refactor Note (2026-03-07)
- Browser-side armor canon is now centralized in `viewer/shared/armor-canon.js`.
- Live pose pipeline primitives are now separated into `viewer/body-fit/body-fit-live.js`.
- `viewer/body-fit` and `viewer/suit-dashboard` should consume shared part/anchor definitions instead of redefining them locally.
- See `docs/concept-driven-refactor.md` for the rationale and next seams.

## Body Fit Frontend Refactor Note (2026-03-07)
- `viewer/body-fit/viewer.js` remains the scene orchestrator and UI wiring layer.
- `viewer/body-fit/body-fit-live.js` is now the live re-henshin signal layer: pose extraction, pose quality gates, and camera pipeline modules.
- Current hotspot after this refactor is still the static armor/VRM lexicon inside `viewer/body-fit/viewer.js`; that is the next safe extraction target.
- `viewer/suit-dashboard/dashboard.js` is the second large frontend hotspot and should follow the same split strategy once body-fit live tracking stabilizes.
