# モデル資産 準備状況と整備計画 (2026-07-05)

Status: Active / 監査済み(本ドキュメントは 2026-07-05 のフルリポジトリ監査結果に基づく)

目的: Webサービス化に向けた 3D モデル資産の「正確な現在地」と「完全なスーツラインナップまでの残作業」を1枚に確定する。

## 1. 現在地サマリ

| 資産クラス | 状態 | 数量 |
| --- | --- | --- |
| カノニカル部位 GLB | 納品済み・tracked (ローカル変更あり) | 18/18 |
| スタイルバリアント GLB (base/sleek/bold + semantic) | 納品済み・**untracked** | 54 (メインツリー) |
| ラインバリアント GLB (fidelity_hold) | **アーカイブのみに存在** | 30 |
| トッピング GLB | 納品済み・untracked | 32 (16/55 スロット) |
| P1 リムバリアント | 発注済み・未納品 | 0/24 |
| テクスチャ | **全部位ゼロ** (factor-only PBR) | 0 |
| VRM ベースライン | default.vrm のみ | 1 |

- GLB は全て Khronos glTF Blender I/O 出力・低ポリ・3共有マテリアルゾーン (armor_base_surface / armor_emissive / armor_accent)、スキニングなし、sidecar `modeler-part-sidecar.v1` でボーン追従。
- ランタイム負荷は軽量: GLB 計 ~2.8MB + VRM 8.6MB。重いのはレビュー用プレビュー PNG 141.6MB (149枚) で、これは配信対象から除外できる。

## 2. 【重要】30体ラインバリアントの救出記録

`docs/modeler-fix-request-latest.md` が参照する 30 体の fidelity_hold ラインバリアント
(line_final_oath / line_rescue_knight / line_royal_insect × 10 スロット) は、
worktree `.claude/worktrees/jovial-cohen-4bf60f/` に納品された後、worktree が空になり
**メインツリーからもgit履歴からも消えていた**。

2026-07-05 の監査で以下に完全保全されていることを確認した(GLB 30 + sidecar + blend + preview 完備):

```text
D:\personal_dev\gavai-henshin\gavai-henshin-local-archive\post-exhibition-cleanup-2026-05-12\.claude\worktrees\jovial-cohen-4bf60f\viewer\assets\armor-parts\
```

対象 30 ファイルセット(部位/バリアントキー):

```text
helmet:    oath_crown_visor, rescue_sleek, compound_guardian
chest:     oath_core_shell, rescue_wrap, emerald_v_core
back:      oath_spine_rear_core, wing_shell_close, compact_spine
waist:     oath_driver_ring, rescue_driver, guardian_buckle
shoulders: oath_guard_fin, sleek_rescue_cap, wing_cap (L/R)
shins:     oath_glow_guard, rescue_stream, guardian_ridge (L/R)
boots:     oath_hero_sole, rescue_toe_guard, guardian_split_toe (L/R)
```

**推奨アクション(優先度: 最高)**
1. このアーカイブフォルダを別ドライブ/クラウドストレージへ即時バックアップする(単一ディスクにしか存在しない)。
2. fidelity_hold の再監査を行い、合格分から `viewer/assets/armor-parts/<part>/variants/` へ復帰 + `variant_catalog.json` 登録 + git commit。
3. 復帰時は `tools/validate_variant_catalog.py` と `tools/validate_armor_parts_intake.py` を通す。

## 3. Git 上の資産ガバナンス(サービス化ブロッカー)

現状、**バリアント/トッピング層の全 86 GLB ファイルセットと `variant_catalog.json` 自体が untracked**。
つまり「デプロイの正」となるバージョン管理された資産ソースが存在しない。

- 18 カノニカル部位も全て locally modified・uncommitted。
- `.gitignore` の `blender/` パターンが `tools/blender/` の Wave-2 バリアント生成パイプラインを誤って ignore していた → 2026-07-05 に `/blender/` へ修正済み。コミット可能になった。
- 資産のステージングは PROJECT_STRUCTURE.md の「catalog-referenced のみ昇格」ゲートに従い、`tools/audit_repo_readiness.py --fail-on-blocked` を通すこと。

## 4. 完全なラインナップまでの残作業(優先順)

1. **資産のgit確定** — 54 バリアント + 32 トッピング + catalog を専用コミットでステージ(上記ゲート経由)。
2. **30体の復帰監査** — アーカイブから fidelity 再判定 → 復帰。provenance フィールド(source_concept_ids / line_id / design_intent / fidelity_notes)の追記が受け入れ条件。
3. **P1 リム 24 ファイルセット** — 発注済み(`docs/modeler-deliveries/p1-limb-order-packet-latest.json`)。腕・脚は現状カノニカル1種のみで、スーツの「見た目の弱点」。納品受け入れは `tools/validate_modeler_variant_order_manifest.py --require-delivered`。
4. **ブーツ基本 3 バリアント × L/R (6)** — カタログ定義済み・未納品。
5. **テクスチャパス(nano_banana ルート)** — 全 GLB が無テクスチャ。sidecar の `texture_provider_profile` と `docs/nanobanana-texture-prompt-contract.md` は定義済みなので、mesh-UV 2K アトラス生成 → GLB への流し込み(または runtime texture_path 参照)を実装する。UV0 ゲート(uv-texture-lock-gate.v1)が per-part の可否を決める。
6. **VRM head/neck マスクアダプタ** — Quest ランタイムは `raw_vrm_disabled_until_head_neck_mask_adapter` で VRM ベーススーツを無効化中。ここを解けば「本人の体に蒸着する」体験が一段上がる。
7. **カタログ整合** — 重複スロットキー (`face_plate`/`faceplate`, `ankle_cuff_trim`/`ankle_cuff`) の統一。`docs/modeler-fix-request-latest.md` が参照する `first-three-lines-2026-05-02.delivery-manifest.json` は存在しない → 参照修正。

## 5. クラウド配信の観点

- 配信バケットへは GLB / sidecar / catalog / VRM / mesh.v1 fallback のみ(~30MB)。preview PNG (141.6MB) と .blend (11.4MB) はレビュー用アーカイブへ。
- `variant_catalog.json` は version + source hash を付けて GCS `catalogs/parts/{catalogVersion}/` に配置する契約が既に `docs/web-service-phase0-task-breakdown-2026-05-02.md` (P0-09) にある。
- 公開ランタイム有効化は現在も `runtime_public_activation_allowed=False`(P1 納品 + fidelity 受け入れが解除条件)。この判定は資産ではなく**制度**なので、解除も監査ログとして記録する。
