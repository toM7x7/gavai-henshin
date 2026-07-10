# Modeler Delivery Coordinate Review - 2026-05-03

## Scope

対象は `.claude/worktrees/jovial-cohen-4bf60f` の `first-three-lines-2026-05-02` 納品です。
三面図の元案は `c01 Royal Insect Guardian`, `c02 Rescue Knight Sleek`, `c15 Final Oath Form`。
Web/Questで使うため、ファイル受領、人体基準配置、三面図再現性を分けて評価します。

## Current Verdict

| Gate | Status | Notes |
| --- | --- | --- |
| File delivery | Technical pass | 30 delivered variants have GLB, `.modeler.json`, source `.blend`, preview mesh. |
| Manifest validation | Pass | `validate_modeler_delivery_manifest.py` は 30/30 pass。 |
| Catalog lineage | Partial | Catalogには `line_id`, `source_concept`, `design_intent` がある。sidecar直下には未反映。 |
| Fidelity to tri-view | Hold | 三面図のシルエット/顔/胸/背面/足元の差がまだ弱い。 |
| Web/Quest placement parity | In progress | `runtime-render-placement.v1` を追加し、Questも同契約を読む導線へ寄せた。 |

## Audit Output

- Worktree audit JSON: `tests/.tmp/modeler-part-delivery-audit-worktree-2026-05-03.json`
- Worktree audit report: `docs/modeler-part-delivery-audit-worktree-2026-05-03.md`
- Current audit counts: `metadata_hold: 72`, `fidelity_hold: 30`, `missing: 14`
- Model quality acceptance JSON: `python tools/export_model_quality_acceptance_report.py --out qa/model-quality-acceptance-latest.json --report-json --no-color`
- Integrated modeler handoff summary: `python tools/export_modeler_handoff_summary.py --out docs/modeler-handoff-summary-latest.md --report-json`
- Handoff share gate: `python tools/validate_modeler_handoff_summary.py --handoff docs/modeler-handoff-summary-latest.md --strict --report-json`

読み方:

- `fidelity_hold: 30` は今回納品30variant。ファイルはあるが `fidelity_notes` が未記録なので、三面図再現性の手確認が必要。
- `metadata_hold: 72` は既存/canonical/base/bold/sleek系を含む旧資産。line情報がないものが多い。
- `missing: 14` はP1部位や旧boot variantの未納品分。今回の30variant受領失敗ではない。
- `model-quality-acceptance-latest.json` は Quest配置ラインを一旦凍結しても見る共通レポート。`runtime_release_allowed`, `model_delivery_acceptance_status`, `fidelity_acceptance_blockers`, `micro_dimension_warnings`, `p1_missing_matrix_summary` を確認し、runtime可とモデル納品/P1停止を混同しない。
- `modeler-handoff-summary-latest.md` は、P1 limb不足発注packetと30variant三面図修正依頼を1枚にまとめるモデラー向け資料。`p1_order_status`, `triview_fidelity_status`, `modeler_action_queue`, `acceptance_gate`, `runtime_release_note`, `handoff_message_japanese` を同時に確認する。
- `validate_modeler_handoff_summary.py --strict` は共有前チェック。P1不足24件、`fidelity_hold`、runtime releaseとmodel delivery blockedの区別、acceptance gate、日本語メッセージが欠けていればfailにする。

## Modeler Delivery Package Index

モデラー共有前の入口は `python tools\export_modeler_delivery_package_index.py --out docs\modeler-delivery-package-index-latest.md --report-json` とする。生成物は `documents_to_share`, `generated_packets`, `validators_to_run`, `blocked_items`, `runtime_release_note`, `do_not_share_local_artifacts` を同じ目録で確認し、P1発注packet、30variant修正依頼、handoff summary、handoff validatorの順にたどれるようにする。

このindexは「展示runtimeはpackage gateが通れば進めるが、P1納品24件と30variant fidelity_holdはmodel delivery blockedのまま」という読み方を固定する。`.claude/worktrees/**`, `tests/.tmp/**`, cache、未参照のQA画像や端末ログは共有対象外とし、共有物はindexに列挙されたdocs/packetだけに絞る。

GitHub投入前はindex内の `pre_github_reading_order` と `github_submission_preflight` を先に見る。`p1_strict_delivery_acceptance` は現時点ではpass前提ではなく、24件不足を次回モデラー発注へ流すための失敗/未完gateとして読む。共有前に必須なのは package index、P1 order packet、30variant fix request、handoff summary の再生成と、`validate_modeler_handoff_summary.py --strict` のpassである。

## Line Fidelity Notes

| Line | Source | What must read at silhouette level | Current hold point |
| --- | --- | --- | --- |
| `line_rescue_knight` | c02 | 白/青/シアン、細いvisor、救助/公共性のある滑らかな胸core、細身で速い印象 | 顔と胸の意匠差がまだ弱い。全体が共通proceduralに見えやすい。 |
| `line_royal_insect` | c01 | 複眼、昆虫/王立感、緑/白/金、背面wing shell、V胸意匠 | 複眼と背面shellが三面図ほど主役化していない。肩/背中の連続性が不足。 |
| `line_final_oath` | c15 | 白/金/シアン、高密度、冠visor、大きい胸core、最終形態らしい密度 | 王冠/胸/肩/背面の密度差がまだ足りず、c01/c02との差が小さい。 |

## Per-Part Review

| Part | VRM/body anchor | Placement rule | Defect memo / next request |
| --- | --- | --- | --- |
| `helmet` | `head` | 顔面はVRM正面、首可動と一人称視界を塞がない。 | c01複眼、c02細visor、c15 crown visorを sidecar `fidelity_notes` とcloseupで明示。頭頂/後頭部の三面図差を増やす。 |
| `chest` | `upperChest` | 胸郭に沿う前面shell。前方+Zへ出すが浮かせない。 | 中央coreとrib/pector分割がまだ弱い。c01 V、c02 rescue core、c15大coreの差分を強くする。 |
| `back` | `upperChest` | 背面-Z側、rotation 180deg系。肩甲骨から腰へ流す。 | 背面がまだ薄く、三面図の背中情報が読みにくい。c01 wing shell、c02 compact spine、c15 rear coreを別物にする。 |
| `waist` | `hips` | 骨盤に巻く。前buckleは+Z、腰/太腿と干渉しない。 | driver/buckle/ringの違いが小さい。横から見た厚み、腰巻き、変身アイテム感を強める。 |
| `left_shoulder` / `right_shoulder` | `leftShoulder` / `rightShoulder` | 左右mirror、三角筋を覆い腕可動に逃げを残す。 | c01 wing cap、c02 sleek cap、c15 guard finの外形差をcloseupで証明。肩から胸/背中への連続線が欲しい。 |
| `left_shin` / `right_shin` | `leftLowerLeg` / `rightLowerLeg` | 膝と足首に逃げ、脚正面ラインを揃える。 | ridge/glow/streamの差が遠景で消えやすい。膝側と足首側の切り欠き/発光lineを明確化。 |
| `left_boot` / `right_boot` | `leftFoot` / `rightFoot` | 床接地優先。toeは+Z、左右toe方向を逆にしない。 | sole/heel/toeの三面図差、接地、足首cuffをcloseupで確認する。Questでは最もズレが目立つ部位。 |
| `upperarm` / `forearm` / `hand` / `thigh` | limb bones | 今回の30variant外。 | 全身hero suitとしては隙間が出る。次WaveでP1部位も3系統variant化する。 |

## Runtime Alignment Work

今回のエンジニアリング側対応:

- `src/henshin/runtime_package.py` に `render_placements` を追加。
- `runtime-render-placement.v1` で `asset_ref`, `body_anchor`, `offset_m`, `quest_rig_offset_m`, `target_size_m` をWeb/Quest共通化。
- `viewer/quest-iw-demo/quest-demo.js` は固定の `QUEST_GLB_TARGET_SIZES` より runtime placement の `target_size_array_m` を優先。
- Quest live/standby/motion/segment pose は runtime placement offset を加算。

この修正は、Webで見たパーツサイズ/位置とQuestで見たパーツサイズ/位置が別テーブルでズレる問題を減らすための土台です。
ただし、三面図再現性そのものはモデル品質の問題なので、別ゲートで継続確認します。

## Acceptance Gates For Next Modeler Delivery

1. 30variantそれぞれに `fidelity_notes` を追加する。
2. 各lineで `front/side/back/3q` と、helmet/chest/back/boot closeupを出す。
3. `line_id`, `source_concept`, `design_intent` はcatalogだけでなくsidecarにも同期する。
4. 背面とbootはWeb previewで座標確認後、Questで再確認する。
5. P1部位、特に upperarm/forearm/hand/thigh の3系統化を次Waveに入れる。
