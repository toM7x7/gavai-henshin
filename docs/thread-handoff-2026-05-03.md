# Thread Handoff - 2026-05-03

## 目的

このメモは、現スレッドのコンテキスト肥大化に伴い、新しいスレッドへ安全に移行するための引き継ぎです。
プロジェクトの基準はロアを守りつつ、「Webでスーツ成立、Questで変身試験、Replayで体験を残す」新規路線です。

## 現在の到達点

### 1. Web側

- `viewer/armor-forge/` のWeb Forgeは、4桁コード発行、身長入力、パーツ選択、variant自動選択、Quest入力URLの導線まで動いている。
- 右側プレビューは簡素化方向に進めている。
- SakuraAI連携は `gpt-oss-120b` 前提。TTSと同じ鍵を流用する方針。
- LLMは入力情報をもとにvariantを選択し、Nanobanana画像生成/表面生成と一緒に進める設計。
- Webプレビューの課題は、スーツ/鎧としての造形完成度と三面図再現性。仕組みは見えてきたが、美術品質はまだ不足。

### 2. Quest側

- Quest BrowserでVR体験は確認済み。
- 4桁コード呼び出し、VR内入力、メニュー、音声、変身、鏡/第三者視点などは段階的に動作確認済み。
- 直近の要望: 成功後も鎧を常時表示しない。変身装着時だけ表示。メニューの「鎧立て」で離れた位置に表示可能にする。
- Quest側の後退点として、WebプレビューとQuest表示でパーツ位置/サイズがズレる問題があった。
- 対応済み: Web/Quest共通の `runtime-render-placement.v1` を追加し、Questも `runtime_package.render_placements` の `target_size_array_m` と `quest_rig_offset_m` を読む導線へ寄せた。

主要ファイル:

- `src/henshin/runtime_package.py`
- `viewer/quest-iw-demo/quest-demo.js`
- `tests/test_runtime_package.py`
- `tests/test_quest_recall_render_contract.py`

検証:

- `python -m pytest tests/test_runtime_package.py tests/test_quest_recall_render_contract.py tests/test_audit_modeler_part_delivery.py -q`
- 結果: `19 passed, 48 subtests passed`

### 3. モデラー/3Dパーツ

- 三面図15案から、まず作る3系統を選定済み。
- 選定3系統:
  - `line_rescue_knight` / c02 Rescue Knight Sleek
  - `line_royal_insect` / c01 Royal Insect Guardian
  - `line_final_oath` / c15 Final Oath Form
- モデラー納品は worktree `.claude/worktrees/jovial-cohen-4bf60f` に存在。
- `first-three-lines-2026-05-02.delivery-manifest.json` は 30/30 pass。
- 30variantはファイル一式としては受領可能。
- ただし三面図再現性は `fidelity_hold`。ファイルの存在と見た目の再現性は分けて扱う。

重要ドキュメント:

- `docs/modeler-first-three-lines-order-2026-05-02.md`
- `docs/modeler-triview-handoff-2026-05-02.md`
- `docs/modeler-three-lines-fidelity-review-2026-05-02.md`
- `docs/modeler-delivery-coordinate-review-2026-05-03.md`
- `docs/modeler-part-delivery-audit-worktree-2026-05-03.md`

### 4. 監査基盤

追加済み:

- `tools/audit_modeler_part_delivery.py`
- `tests/test_audit_modeler_part_delivery.py`
- `docs/modeler-delivery-coordinate-review-2026-05-03.md`

監査の考え方:

- `technical pass`: GLB / `.modeler.json` / `.blend` / preview mesh が揃っている。
- `metadata_hold`: lineageや設計意図がsidecar/catalogから追えない。
- `fidelity_hold`: 技術的には存在するが、三面図再現性や意匠差の確認が未完。
- `missing`: 今回納品対象外、またはcatalog上あるが実ファイルがない。

直近のworktree監査:

- `metadata_hold: 72`
- `fidelity_hold: 30`
- `missing: 14`

解釈:

- `fidelity_hold: 30` は今回納品30variant。
- P1部位 `upperarm/forearm/hand/thigh` は今回納品外。全身スーツとしては次Waveで必要。

## 主要な未解決点

1. 三面図再現性
   - c01/c02/c15の違いがまだ弱い。
   - helmet/chest/back/waist/shoulder/shin/boot の形状差とcloseupが必要。

2. P1部位不足
   - upperarm / forearm / hand / thigh が3系統variant化されていない。
   - 全身ヒーロースーツとして隙間が残る。

3. Web/Quest視覚一致
   - 共通配置契約は入ったが、実機でどれだけズレが減ったか再確認が必要。
   - 特に back / boot / waist はQuestでズレやすい。

4. Webサービス化
   - ローカル動作からクラウドへ移す段階。
   - GCP/PlayCanvas/通常Web配信の役割を整理する。
   - まずはWeb Forge + Quest viewer の分離とAPI境界を安定化する。

5. 生成系
   - Nanobanana中心でテクスチャ/表面生成。
   - SakuraAI `gpt-oss-120b` はvariant選択/生成指示に使う前提。
   - さくらAI TTS鍵流用方針。

## 次スレッドでの最初の作業順

1. `docs/thread-handoff-2026-05-03.md` を読む。
2. `docs/modeler-delivery-coordinate-review-2026-05-03.md` を読む。
3. Web/Quest共通配置契約の差分を確認する。
4. ローカルサーバーを立ち上げ、Web ForgeとQuestを確認する。
5. モデラー納品30variantの三面図fidelityをパーツ別に確認する。
6. P1部位の3系統variant発注/受け入れ基盤を作る。
7. WebUI簡素化とWebサービス化の設計へ進む。

## 新スレッド冒頭に貼る指示文

```text
C:\dev\codex\gavai-henshin を作業対象にしてください。

このスレッドは前スレッドからの継続です。まず以下を読んで、現状を把握してから進めてください。

1. docs/thread-handoff-2026-05-03.md
2. docs/modeler-delivery-coordinate-review-2026-05-03.md
3. docs/modeler-part-delivery-audit-worktree-2026-05-03.md
4. docs/modeler-first-three-lines-order-2026-05-02.md
5. docs/modeler-triview-handoff-2026-05-02.md

プロジェクトの基準はロアを守りつつ、新規路線「Webでスーツ成立、Questで変身試験、Replayで体験を残す」です。

現状:
- Web Forgeは4桁コード発行、身長入力、variant選択、Quest導線が動いています。
- QuestはVR内コード呼び出し、変身、音声、鏡/第三者視点、鎧立てメニューが進行中です。
- Web/Questの表示ズレ対策として `runtime-render-placement.v1` を追加済みです。
- モデラー納品30variantはファイルとしてはpassですが、三面図再現性は `fidelity_hold` です。
- P1部位 upperarm/forearm/hand/thigh はまだ3系統variantが不足しています。

まずやってほしいこと:
1. 現状差分とテスト状態を確認
2. Web ForgeとQuestを再起動して実機確認できる準備
3. Web/Questで同じ4桁コードを呼び出し、パーツサイズ/位置ズレが改善しているか確認
4. モデラー納品30variantを1パーツずつ三面図基準で確認し、不備をdocsに残す
5. P1部位の発注/受け入れ基盤を作る
6. その後、WebUI簡素化とWebサービス化/GCP/PlayCanvas方針整理に進む

開発では既存の変更を勝手に戻さず、リファクタリングしつつ、テストとドキュメントを残してください。
```

