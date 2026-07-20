# XRift スーツギャラリー構想 — 実現性評価と計画 (2026-07)

構想: 鍛造されていくスーツを **XRift** のワールドに随時アップロードし、ギャラリーとして
展示する。来訪者がその場で展示アバターに「変身」できたら理想。
(ワールドの設計自体は後回し。まず成立性の確認)

## 0. XRiftの基礎事実(2026-07調査)

- XRift = ブラウザで動くメタバース(Three.js / React Three Fiber + WebXR)。
  アバターは **VRM 0.x / 1.0 両対応** — 本プロジェクトのスーツVRMは
  **既にXRift上で動作実績あり**(2026-07-09のアバター検証)
- ワールドは**コードで作る**(R3F + Vite プロジェクト)。GUI派には非公式デスクトップアプリ
  [xrift-studio](https://github.com/WebXR-JP/xrift-studio)(作成〜プレビュー〜公開を一括)
- アップロード手段(公式):
  - [xrift-cli](https://github.com/WebXR-JP/xrift-cli): `xrift login`(ブラウザ認証、
    トークンは `~/.xrift/config.json`)→ `xrift upload`。**`-y --no-interactive` で
    CI/スクリプト利用可**。リポジトリ説明は「ワールドや**アバター**をアップロード」
  - **@xrift/sdk**: Node.jsから `uploadWorldFromDirectory('./proj', { token })` →
    `worldId` / `versionNumber` が返る。**ID指定で既存ワールドの更新(再アップロード)も可**。
    WorldsApi / ItemsApi、進捗コールバック、メタデータ設定あり
- [World Components](https://docs.xrift.net/world-components/components/): 13種
  (Interactable / Grabbable / Mirror / VideoScreen / SpawnPoint / Portal / TagBoard 等)。
  **アバター切替・ペデスタル系コンポーネントは現状なし**
- [Public API v1](https://docs.xrift.net/public-api/v1): APIキー(`xrift_sk_`)で
  read:worlds / read:users / read:instances — **読み取り専用**。書き込みはCLIトークン(`xrf_`)系

## 1. Q1「スーツを都度ワールドにアップロードしていける?」→ **できる**

2つのアーキテクチャ。**A案が本命**(再アップロード不要の自動ギャラリー):

### A案: 自己更新ワールド(マニフェスト参照)
ワールドは three.js コードなので、実行時に本プロジェクトの公開ギャラリー
(`suits/gallery.json` + 各`GAVAI-XXXXX/*.vrm`、Supabase public)を fetch して
展示を組み立てる。
- **鍛造するだけでワールドに反映**(ワールドの再アップロードは一切不要)
- 展示台・照明・世界観だけをワールド側に実装。表示数は直近N体+人気枠などで制御
- リスク: XRiftワールドの外部URL fetch がCSP等で制限される可能性(未文書)。
  → 最初の技術検証で「Supabaseから1体ロード」だけの最小ワールドを上げて確認する
- 負荷: スーツVRMは10MB級。同時表示は5〜8体+LOD/間引きが現実的
  (XRift公式の [avatar-optimizer](https://github.com/WebXR-JP/avatar-optimizer) も流用候補)

### B案: 鍛造時に再ビルド&自動アップロード
forge(Cloud Run)がスーツ完成時に `@xrift/sdk` でワールドを更新
(スーツを含めて再アップロード)。
- 公式SDKが想定している使い方そのもの。確実に動く
- コスト: ワールドサイズが体数に比例、鍛造ごとに数十MB転送
- A案がCSPで塞がれた場合のフォールバック

**必要な準備(ユーザー側)**: XRiftアカウントで `xrift login`(トークン発行)。
自動化する場合はそのトークンを Cloud Run の env へ(Vercelには置かない)。

## 2. Q2「ワールド内で展示アバターに変身できる?」→ **公式機能は現状なし。3つの回避路**

World Components / Public API のどこにも「ユーザーのアバターを切り替える」APIは
現状存在しない(VRChatのアバターペデスタル相当が無い)。

1. **XRiftアバターとしても並行アップロード+導線**(今できる・確実):
   スーツをワールド展示と同時に**XRiftアバターとしても登録**(xrift-cliの守備範囲)。
   ワールド内の展示台に「このスーツを着る」導線(アバターページへのリンク/QR)を置き、
   来訪者はXRift標準のアバター選択で装着。
   ※他人が着られる公開設定が可能かは要確認(アバター共有モデルが未文書)
2. **ワールド内の疑似変身**(演出として): ワールドコードで来訪者のアバターに
   鎧メッシュをボーン追従で被せる(=本プロジェクトのミラー技術のワールド版)。
   本当のアバター切替ではないが「その場で蒸着する」体験は作れる。
   他クライアントへの同期可否(ワールド状態同期API)は要調査
3. **公式への機能要望/コンポーネント寄贈**(中期): world-components はMIT。
   `AvatarPedestal` 相当を Discord で要望 or 実装コントリビュート。
   WebXR-JPコミュニティとの接点としても価値あり

## 3. 段階計画

| Phase | 内容 | 前提 |
|---|---|---|
| 1 | ✅実装済(2026-07-20): `xrift/gallery-world/` — gallery.json→最新3体VRMを実行時fetchして展示+ワールド内計測板が成否を表示。**ローカルDevEnvironmentでフルチェーン成立を確認済み**(Supabase CORS問題なし)。残り=主催アカウントで`xrift upload world`→本番XRift上で計測板の文言確認(ホストCSPの最終確定) | ユーザーのXRiftログイン |
| 2 | ギャラリーワールドv1: gallery.json駆動で直近N体を展示台+呼出符プレート表示。世界観(蒸着庫)デザイン | Phase 1でA案OK |
| 3 | 「着る」導線: スーツのXRiftアバター並行登録を forge に組み込み+展示台にリンク | アバター共有仕様の確認 |
| 4 | 疑似変身ギミック or 公式ペデスタル要望の進捗次第で本物の変身 | ワールド同期API調査 |

## 4. 未確認事項(Phase 1で潰す)

- [ ] ワールドからの外部URL fetch 可否(CSP) — A案の成否
- [ ] アバターの公開共有(他人が着られるか)の仕様
- [ ] ワールド内の状態同期(カスタムイベント)の提供有無
- [ ] xrift-cli のアバターアップロードの実コマンド(READMEはワールド中心)
- [ ] ワールド容量・ファイル数制限

## 参考リンク

- https://xrift.net/ / https://docs.xrift.net/
- CLI: https://github.com/WebXR-JP/xrift-cli / SDK: https://docs.xrift.net/sdk/overview
- Components: https://docs.xrift.net/world-components/components/
- Studio(非公式GUI): https://github.com/WebXR-JP/xrift-studio
- avatar-optimizer: https://github.com/WebXR-JP/avatar-optimizer
