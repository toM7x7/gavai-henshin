# Progress Log（都度更新用）

運用ルール:

- 日付は `YYYY-MM-DD` で記録する
- 1エントリに `実施 / 結果 / 次アクション` を最低 1 行ずつ書く
- 失敗や保留も記録して判断履歴を残す

---

## 2026-04-29

### 実施

- Web Forgeでヘルメットのみ選択した場合に、API側が `helmet/chest/back` を自動補完していた問題を修正
- 部分生成は `selected_overlay_parts` のまま保存し、完成ヒーロースーツ判定は `missing_required_overlay_parts` と `selection_complete_for_final_texture` で分離
- `model_quality_gate` は選択部位のmesh品質を確認しつつ、完成必須部位不足時は final texture lock を許可しないようにした
- Forge UIのモデルGate表示に「部分生成」状態を追加し、部分プレビューと本番スーツ化を区別

### 結果

- ヘルメットのみ生成は `装甲1パーツ` として扱われ、`back/chest` 不足が明示される
- 画像で見えていた状態は、完成ヒーロースーツではなく `VRM人体 + 基礎スーツ + mesh.v1仮外装プロキシ` の部分プレビューと位置づけた
- 現行meshは描画可能性のGateを通るが、シルエット、pivot、mount axis、VRM surface clearance、素材スロットの品質は未達
- 本番テクスチャ貼り込みは、必須部位が揃うまで `writes_final_texture=false` のまま止まる

### 次アクション

- `model-artifact.v1` を追加し、GLB/VRM候補アセットを `mesh.v1` fallback と並走させる
- ヒーロースーツ品質Gateを、mesh描画可能性から fit/mount/silhouette/material/UV の実品質へ拡張する
- Quest recallは壊さず、GLB優先・mesh.v1 fallbackのローダーへ段階的に移行する

---

## 2026-04-28

### 実施

- 参考資料 `examples/henshin_docs_bundle_v0_1/`、`examples/henshin_docs_gcp_bundle_v0_2/henshin_docs_gcp_v0_2/`、`examples/message (1).txt` を確認し、ロア/新規路線/GCP/PlayCanvas合成の軸を整理
- `docs/checkpoints/2026-04-28-system-progress.md` を追加し、PC電源OFF後の再開手順、現状進捗、残課題、ユーザー操作メモを固定
- `src/henshin/runtime_package.py` を追加し、`SuitSpec` / `SuitManifest` / `visual_layers` / `render_contract` を runtime 向け `RuntimeSuitPackage` に正規化
- `GET /v1/quest/recall/{recallCode}` が `runtime_package` を返すようにし、Quest/Web/将来Unity adapterの import checklist を一本化
- `src/henshin/armor_fit_contract.py` を追加し、VRM人体を基準にした `armor-body-fit.v1` の canonical slot map、左右ペア、身長スケール、必須slot監査を実装
- Web Forgeの鎧立てに基礎スーツ層・装甲パーツ層・表面/テクスチャ層の状態表示を追加
- Quest呼び出しUIに装備状態診断を追加し、`runtime_package.runtime_checks.can_render_runtime_suit=false` を装備不足として扱う導線へ更新
- `src/henshin/armor_model_quality.py` を追加し、`helmet/chest/back/left_shoulder/right_shoulder` の `model-quality-gate.v1` を実装
- Web Forge / Quest recall / RuntimePackage に `model_quality_gate` を接続し、生成コード発行と展示品質Gateを分離
- `viewer/assets/meshes/mesh-bounds.v1.json` を追加し、現行 `mesh.v1` 18部位の明示bounds sidecarを固定
- `tools/generate_mesh_assets.py` と `tools/update_mesh_bounds.py` を整備し、以後のmesh生成/sidecar生成でboundsが欠落しないようにした
- Nano Banana表面生成の `writes_final_texture` を `model_quality_gate.status == "pass"` に接続し、`texture_path` 書き込みもバックエンド側で再監査するようにした
- Web Forgeの表面生成UIを、Gate前のProbe用途とGate通過後のSuitSpec反映用途で出し分けるようにした

### 結果

- VRM-only recall を無効状態として扱う契約が `render_contract` だけでなく runtime package にも入った
- SuitSpecに後から入った `texture_path` を runtime manifest に投影するルールが純粋関数として分離された
- GCP移行前でも、Cloud Run / Unity / PlayCanvas へ移植しやすい境界ができた
- slot名の揺れは `shoulder_l` / `left_shoulder` などを `armor-body-fit.v1` で吸収し、runtime側では既存パーツ名を維持できる
- 現行 `viewer/assets/meshes` のP0部位は sidecar bounds により `model_quality_gate.status=pass` になった
- `update_suitspec=True` は生成履歴更新用、`writes_final_texture=True` は本番テクスチャ貼り込み用として分離できた
- Gate未通過時はUIが許可しても `part_generation.py` が `texture_path` を書かないため、表示と副作用の抜け道を閉じた
- `python -m pytest -q -p no:cacheprovider` は `150 passed, 50 subtests passed`
- Target確認 `python -m pytest -q -p no:cacheprovider tests/test_part_generation.py tests/test_armor_model_quality.py tests/test_new_route_api.py tests/test_dashboard_server.py tests/test_runtime_package.py` は `66 passed`
- `node --check viewer/armor-forge/forge.js` と `node --check viewer/quest-iw-demo/quest-demo.js` は成功
- `python -m py_compile src/henshin/armor_model_quality.py src/henshin/dashboard_server.py src/henshin/new_route_api.py src/henshin/part_generation.py tools/generate_mesh_assets.py tools/update_mesh_bounds.py` は成功

### 次アクション

- `model-artifact.v1` sidecarを起こし、GLB/VRM由来の候補アセットを `mesh.v1` fallbackと並走させる
- `mesh.v1` Gateは「描画可能」の確認に留め、次はpivot / mount axis / VRM surface clearance / material slots / UV contractを品質Gateに足す
- Quest recallはすぐ `.glb` に切り替えず、fallback-aware loaderを入れてから段階的にGLB優先へ進める
- `examples/suitspec.sample.json` の変更を canonical sample更新として採用するか判断する
- `tests/.tmp` と参考資料bundleをコミット対象から分離し、必要なら `.gitignore` / docs取り込み方針を決める
- 次の実装は実テクスチャ生成の速度確認、GLB/PlayCanvas/Unity向けの派生成果物contract、P0 fit/mount quality gate整備へ進める

---

## 2026-03-28

### 実施

- `viewer/body-fit/index.html` の UI を UTF-8 で全面修復し、`Cam Back` / `Cam POV` / `Live View` セレクタを正式化
- `docs/reentry-hub.md` を追加し、再開時の現状整理・危険因子・最短手順を 1 枚に固定
- `docs/game-studio-xr-poc-brief.md` と `docs/game-studio-xr-prompt-template.md` を追加
- `docs/body-fit-viewer.md` を更新し、`body-fit / live tracking` 再開手順を整理
- `docs/roadmap.md` を再整理し、Re-entry priorities と XR lane split を明文化

### 結果

- `body-fit` は HTML 崩れを前提にした曖昧な再開ではなく、配線済み UI をそのまま確認できる状態に戻った
- Game Studio は本線統合ではなく、XR PoC 導線として位置づけを固定できた
- `body-fit` を fitting truth source、8thWall を camera runtime 候補、XR Blocks / Game Studio を headset XR PoC として役割分担できた

### 次アクション

- `.playwright-cli/*` と `output/filelist.txt` を掃除して worktree を整理
- `body-fit` の live-view 挙動をブラウザで再検証
- `upperarm / forearm` の向き違和感を `VRM / anchor / live pose` に切り分ける

---

## 2026-03-03

### 実施

- 8thWall-aware policy を将来機能の継続判断基準として追加
- `viewer/body-fit` live pipeline に 8thWall-style camera pipeline module architecture を導入
- `docs/8thwall-element-integration.md` を追加

### 結果

- 8thWall の runtime を直接組み込まずに、camera pipeline の設計パターンだけを先行導入した
- `viewer/body-fit` の live pipeline を module 単位で分離し、拡張しやすくした

### 次アクション

- 以後の tracking / WebAR / camera runtime の設計更新では 8thWall の判断を必ず残す

---

## 2026-03-01

### 実施

- `docs/id-policy.md` を追加し、`SuitID / ApprovalID / MorphotypeID / SessionID` の発行ルールを固定
- `docs/armory-io-contract.md` を追加し、Armory Viewer 連携の入出力 JSON・座標・エラー契約を固定
- `generate-parts` に `--fallback-dir` / `--prefer-fallback` / `--texture-mode mesh_uv` を追加
- 既存資産 `sessions/S-20260228-JBJK/artifacts/parts` を使ったフォールバック生成を確認
- `serve-dashboard` と `viewer/suit-dashboard` を追加
- `python -m unittest discover -s tests -v` を実行

### 結果

- Phase 1 の契約系タスクを文書面で完了
- API キー未設定でも、既存パーツ画像から `generate-parts` を完走できるようになった
- 部位ごとの個別 3D 確認とダッシュボード上からの生成実行が可能になった
- 単体テストは成功した

### 次アクション

- API キー投入後の実画像生成スモークテスト
- Track A の最初の Wear Build 完走
- SuitSpec テンプレート拡充

---

## 2026-02-28

### 実施

- Lore / Blueprint の確認と Gate 0 下準備ドキュメントを作成
- `SuitSpec` / `Morphotype` の初期 schema を追加
- リポジトリ基盤（CLI / CI / test / docs）を整備
- Gemini 画像生成連携（REST）と `generate-image` を追加
- `.env` / `.env.example` を追加し、Gemini API キーのローカル管理を整備
- `examples/henshin-rightarm-poc` を分析し、右腕装着ロジックを本体へ移植
- `simulate-rightarm` / `simulate-body` / `generate-parts` / `viewer/body-fit` を追加

### 結果

- Demo（happy / refused）で成果物を保存できる基盤が揃った
- バリデーションとユニットテストが通過した
- API キー未投入でも、連携コード自体は呼び出し可能な準備段階まで到達した
- Browser ベースの全身 fit viewer を起点に、部位別パーツ生成へ移行できる導線を確立した

### 次アクション

- API キー投入後の実画像生成スモークテスト
- 生成失敗時フォールバックの強化
- Armory Viewer 連携 I/O 仕様の固定
