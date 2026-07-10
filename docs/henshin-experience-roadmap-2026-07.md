# 変身体験ロードマップ — 「成立が価値である」 (2026-07-05)

Status: Active / Product roadmap
Foundation: `Lore Bible.md` / `blueprint.md` / 展示会実績 (2026-05) / 2026-07-05 フルリポジトリ監査

> この世界の変身は、派手さではなく **成立** が価値である。
> 成立とは、設計され、適合し、承認され、記録され、封印されたということ。
> — Lore Bible §22

このロードマップは機能一覧ではない。**変身プロトコルの状態遷移そのもの**を、
プロダクトが世界へ出ていく工程に重ねる。フェーズ名は演出ではなく受け入れ条件を持つ「制度」である。
各フェーズの完了は宣言ではなくゲート通過で確定する — 通らなければ**起動拒否**。それは失敗ではなく、規格が維持された証左である。

---

## Phase 1 『公示』 POSTED — リポジトリが世界に姿を晒す

**いま、このプロジェクトは「誰にも見せられない金庫の中の傑作」だ。それを公示する。**

任命は公示から始まる(Canon 3)。コードと資産がgitに確定して初めて、このプロダクトは存在を主張できる。

- [ ] main クリーンアップ6レーンコミット(post-exhibition-main-cleanup-plan 継承)
  - node_modules 除去(origin/main に 1,711ファイル/197MiB — 公開前に filter-repo)
  - Playwright証跡57 + examples媒体7 の削除確定
  - **未追跡の tools 44本 / tests 57本 / バリアント資産86式 / variant_catalog.json のコミット**
- [ ] 30体ラインバリアントの復帰監査(救出済み: `gavai-henshin-local-archive/post-exhibition-cleanup-2026-05-12/` → model-readiness-2026-07.md 参照)
- [x] CI 修復(依存インストール + pytest 化) — 2026-07-05
- [x] テストスイート green(587/587) — 2026-07-05
- [x] 機微パス配信ガード / 定数重複解消 / dead code 除去 — 2026-07-05
- [ ] 鍵ローテーション(Gemini / Sakura / quest-lan 証明書)

**DoD**: `audit_repo_readiness.py --fail-on-blocked` が exit 0。GitHub push が「怖くない」。

---

## Phase 2 『適合』 FIT_AUDIT — 誰の手元でも成立する

**URLを送るだけで、友人がスーツを鍛造できる。適合審査は「あなたのPC」から「誰のブラウザでも」へ。**

- [ ] 認証境界 + CORS 実装(現状 API は無認証・CORS はデッド設定)
- [ ] Cloud Run Phase 0 デプロイ(Dockerfile / cloudbuild.yaml 追加済み — cloud-architecture-2026-07.md)
- [ ] 外部モード検証の初回実績(`validate_service_deployment_contract.py --mode external` — まだ一度も走っていない)
- [ ] suit-dashboard の remote-base 対応(shared/api-client.js 抽出)
- [ ] Quest クライアントの localhost:8021 排除(相対パス + proxy)
- [ ] SuitStore/TrialStore シーム → Cloud SQL / GCS ドライバ(Phase 1 移行)

**DoD**: 会場にいない人間が recall code を受け取り、自分の Quest で変身する。

---

## Phase 3 『蒸着』 DEPOSITION — 体験の核を最大火力にする

**ここがこのプロダクトの心臓。感情が原料になり、誓いが規律になり、装甲が定着する。**

- [ ] **テクスチャパス実装** — 全104 GLB が現在無テクスチャ。nano_banana ルート(契約定義済み)で mesh-UV 2K アトラスを流し込む。フラット素材の鎧が「その人の感情の色」を持つ瞬間。
- [ ] **エモルギー→スーツ 1:1 の手応え** — blueprint の EmolgiaSeed 6軸(高揚/闘志/哀傷/緊張/守護/受容)を Forge 入力に実装。「感情はそのまま着ない。制度を通して法定状態になる」を UI で体感させる。
- [ ] **SEALING を取り戻す** — 現在 Quest trial は DEPOSITION→ACTIVE と遷移し、**封印工程がスキップされている**。ロア上、封印は正規性の最終確定(§4.3)。エンブレム焼き付けの演出 + trial ledger 上の SEALING 状態を必須化する。
- [ ] **VRM head/neck マスクアダプタ** — `raw_vrm_disabled_until_head_neck_mask_adapter` を解き、「マネキン」ではなく「本人の身体」への蒸着にする。
- [ ] P1 リム24式の受け入れ — 腕と脚が変わると全身が変わる。
- [ ] mocopi Morphotype 同定(Scene B)の GO 昇格 — 体躯が合うことは「適合審査に通った」という物語的事実。

**DoD**: Weekly Wear Build で毎週1着、テクスチャ付きスーツが「立ち」、封印まで完走する。

---

## Phase 4 『封印』 SEALING — 制度がプロダクトになる

**このプロダクトの差別化は装甲の派手さではない。「監査可能な変身」という誰もやっていない体験設計だ。**

- [ ] **起動拒否を最高の体験にする** — REFUSED は失敗画面ではない。`REFUSED: RESONANCE_UNSTABLE` の公文書が発行され、「拒否は規格が維持された証左である」と表示される。再挑戦の動機はここから生まれる。
- [ ] **生成物 = 物証** — 認可書 / 型式番号 / 封印紋 / 蒸着ログ字幕(Lore §9.1 の生成スロット)を Gemini で発行し、セッションに封緘する。
- [ ] **誓い(Oath)選択の実装** — NO_OMISSION / REFUSAL_ACCEPTED 等の10誓い。誓いが封印紋の幾何と発光規律に効く(oath_modifiers)。感情は原料、誓いは規範。
- [ ] Firebase Auth — 運用者(operator console)と来訪者(visitor flow)の権限分界。
- [ ] audit_logs を全変異操作へ — 「ログは儀式の副産物ではなく、儀式そのもの」(§4.4)

**DoD**: 1回の変身から、監査に耐える物証一式(SuitID/ApprovalID/Blueprint/Emblem/Log/Clip)が自動発行される。

---

## Phase 5 『記録院』 ARCHIVED — アーカイブが世界を広げる

**変身は一瞬。記録は永遠。記録院がコミュニティの土台になる。**

- [ ] **公式アーカイブ映像(30秒)** — 展示の Replay を「持ち帰れる監査記録」として自動生成・共有可能に。
- [ ] **recall code の社会化** — 4桁コードで友人のスーツを召喚して隣に立たせる。「照合」が遊びになる。
- [ ] **スーツ系譜(suit_versions)** — 再鍛造(リフォージ)の履歴が残る。Rev が上がるたび、そのスーツの「歴史」が厚くなる。
- [ ] 展示会 v2 — クラウド + 会場ハイブリッド運用(会場PCは mocopi ブリッジに徹する)。
- [ ] NC イベント(将来構想) — ログ腐食・封印偽装をテーマにした期間限定チャレンジ。「照合可能性の回復」がゲームになる。

### トラッキングの将来線(2026-07-05 追記)

体躯同定(Morphotype)から「追従する蒸着」への三段展開:

1. **mocopi 連携** — Tポーズ校正→骨格比率→Morphotype(Scene B)は既存資産(UDPブリッジ
   `tools/serve_mocopi_body_sim_latest.py` + body-sim/latest 契約)。Phase 3 の GO 昇格で
   「自分の体格に適合審査された装甲」が成立する。
2. **Webカム AR 変身(Webサービス後)** — MediaPipe Pose Landmarker(2D+3D ランドマーク)で
   ブラウザ内ボディトラッキング → runtime-placement-resolver の web_preview_parity モードに
   ランドマーク由来のボーン推定を流し、カメラ映像に装甲を重畳。持ち帰り線(blueprint §4.3)の本命。
3. **Quest ラフトラッキング追従** — Quest のヘッド+ハンド6DoF から上半身IK推定(既存の
   live body pose 経路)で装甲がラフに体を追いかける。mocopi 併用時は精度が上がる、
   なくても成立する — local-pass 原則をトラッキングにも適用する。

**DoD**: 体験者が自分の意思でアーカイブを他者に見せに行く。

---

## 運用原則(全フェーズ共通)

1. **local-pass は絶対** — クラウドも PlayCanvas も mocopi も、ローカル完結ループの成立を覆せない(exhibition-service-mocopi-roadmap の統治を継承)。
2. **Weekly Wear Build を止めない** — 毎週1着立てる。モチベーションは工程に組み込む(blueprint §1.2)。
3. **文言は Lexicon に従う** — 公示/承認/拒否/封印/照合/記録院。UIの一行一行が世界の圧になる。
4. **Canon を壊す変更は起動拒否** — 手順違反の結果は常に REFUSED のみ。例外を作らない。

> 制度は冷たい。だからこそ、誓いだけが光る。
