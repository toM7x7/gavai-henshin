# リファクタ台帳 (2026-07-05 監査より)

Status: Active — 2026-07-05 のフルリポジトリ監査(12視点並列)で確認された改善項目のうち、
同日に**未適用**のものを優先順で保持する。適用済み項目は末尾に記録。

## P1 — クラウド移行の前提になるもの

1. **new_route_api.py の分割**(3,188行 / 104メソッドの god class)
   - `routes.py`(パス→ハンドラのテーブル化)/ `suit_store.py`・`trial_store.py`(永続化をプロトコル化)/ `forge_planner.py`(~60の `_forge_*` は suitspec 辞書上の純計算)/ `replay.py`
   - SuitStore シームは Cloud SQL/GCS ドライバの差し込み口を兼ねる(cloud-architecture Phase 1)。
2. **認証 + CORS** — `CORS_ALLOWED_ORIGINS` は現在どこからも読まれていないデッド設定。変異系/課金系エンドポイント(generation-jobs, iw-henshin/voice, suitspec-save)に共有シークレット。POST の Content-Type 検査(text/plain CSRF 対策)。
3. **GET /v1/trials/{id}/replay の書き込み副作用除去** — 読み取りで replay-script.json を書き、transform-session.json を変異させている。
4. **並行性** — ThreadingMixIn 下で suit/trial JSON の read-modify-write が無ロック(append_trial_event でイベント欠落があり得る)。ストア層導入時にロック/トランザクションへ。
5. **viewer/shared/api-client.js 抽出** — fetch層が3アプリで三重化し、同名 `fetchJson` の契約が非互換(forge: throw / dashboard: {res,data})。suit-dashboard は remote-base 完全非対応。
6. **viewer/shared/mesh-payload.js 抽出** — `meshGeometryFromPayload` が4実装で挙動乖離(nested配列 / uv|uvs / bounds検査 / centering)。同じ mesh.v1 が「あるアプリでは描け、別では例外」になり得る。

## P2 — 品質・保守性

7. 18部位カノン + 日本語ラベルの一本化 — forge.js 内でも `PARTS` と `PART_DISPLAY_LABELS` が乖離(left_forearm: 左腕甲 vs 左前腕)。`shared/armor-canon.js` から `ARMOR_PART_IDS` / `PART_LABELS_JA` を export。
8. quest-demo.js のデッド関数8個削除(vectorArrayFromRecord, questSurfaceOffsetArrayFromPlacement, questRotationArrayFromPlacement, webPreviewRotationArrayFromPlacement, armorStandPoseForPart, normalizeTriggerText, formatFitContract, formatTextureFallback)+ forge.js rotationZFromSegment。※source-string テストの同時更新必須。
9. rightarm.py 廃止 — bodyfit.py の verbatim サブセット。`simulate-rightarm` CLI は 1セグメント spec の薄いラッパへ。
10. GeneratePartsPayload / GenerationRequest のフィールド重複統一(dashboard_server ↔ part_generation)。
11. tools/ の共通化 — REPO_ROOT ブートストラップ18回コピー、importlib での相互ロード + `module.REPO_ROOT` モンキーパッチ、GLB ヘッダパーサ6重複 → `src/henshin/glb.py` と `tools/henshin_tools/` パッケージへ。
12. 音声トリガー語の設定不整合 — コード既定「生成」/ .env.example「変身」/ demo example「seisei」。クライアント TRIGGER_ALIASES と iw_henshin の重複も一本化。
13. three.js ランタイム分裂 — vendored r164 と npm ^0.180 が混在。@pixiv/three-vrm が CDN-only(オフライン展示で劣化)。0.180 に統一 + three-vrm を vendor。
14. `?v=` キャッシュバスタの手管理廃止(auto-fit-engine が3つの異なるURLでロードされ、別モジュールインスタンス化)。
15. SSE ハンドラ — Condition ロック保持のままクライアントへ write(遅いクライアントが emit を止める)/ 非数値 cursor で uncaught ValueError。
16. Gemini API キーが URL クエリに載る(`?key=`)→ `x-goog-api-key` ヘッダへ。
17. sessions/_cache/parts のエビクション導入(現在無制限成長)。
18. suit-dashboard の provider select がデッドUI(常に nano_banana ハードコード)。

## P3 — docs / 構造

19. 日付付き64ドキュメントのアーカイブ移動(docs/archive/2026-05/ + index)— PROJECT_STRUCTURE の Docs Policy 準拠。
20. qa/ の生JSON 17件を qa/logs/ へ(「curated manifests only」規約)。
21. docs/_smoke_renders + docs/assets の視覚成果物15件をアーカイブへ。
22. examples/ が本番シード(new_route_api がリクエスト時に読む)を兼ねる緊張の解消 — seeds/ へ分離 or パッケージリソース化。
23. morphotype.v0.2.schema.json がどこからも enforce されていない / CLI validate に replay-record kind がない。
24. source-string 契約テスト(quest-demo.js を~20回 grep)の段階的な挙動テスト化。

## 適用済み (2026-07-05)

- 機微パス静的配信ガード(dashboard_server.send_head + _resolve_repo_path)
- per-part テクスチャプロンプトの二重注入バグ修正(part_generation / part_prompts)
- プロトコル状態リストの constants.py 一本化(new_route_api の三重定義解消)
- iw_henshin.py の重複デッド定数統合(unicodeエスケープ版を可読版へ)
- `_load_dotenv` 3実装 → `src/henshin/_env.py` に統合(CWD非依存の repo-root フォールバック付き)
- `.gitignore` `blender/` → `/blender/`(tools/blender の Wave-2 パイプラインがコミット可能に)
- CI 修復(deps インストール + pytest 化 + permissions: contents: read)
- ドリフトしていた契約テスト11件を現行実装に更新(суite 587 green)
- PROJECT_STRUCTURE.md のアーカイブパス修正 + 30体救出先の明記
- .env.example の PFX パスフレーズをプレースホルダ化
- infra/gcp: Dockerfile / .dockerignore / cloudbuild.yaml 追加、schema.sql に recall_codes / generation_jobs、env.example の命名統一
