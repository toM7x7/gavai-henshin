# Reference Map (2026-03-02)

## 目的

- 外部情報を「実装判断に使える粒度」で固定する
- Track A（Suit Forge）/ Track B（Transform Stage）/ WebCam再変身に紐づける
- 採用候補と監視対象を分け、毎週更新しやすくする

## 1. 近縁サービス・体験（市場文法）

- ナレルンダー！仮面ライダードライブ（画面内変身 + 記録導線）
  - https://www.narerunda.jp/drive/
  - https://www.unrealengine.com/ja/blog/narerunda-kamen-rider-drive-now-an-amusement-park-attraction-in-japan
- Marvel's Iron Man VR（Suit Up体験を中心にしたVR文法）
  - https://www.playstation.com/en-us/games/marvels-iron-man-vr/

判断メモ:

- 変身体験そのものは既存市場あり
- 差別化点は「生成 -> 蒸着 -> 封印 -> 再変身」のプロトコル統合

## 2. Track B（Quest/Unity）一次情報

- Meta XR All-in-One SDK（配布・更新点の確認先）
  - https://assetstore.unity.com/packages/tools/integration/meta-xr-all-in-one-sdk-269657
- Unity開発開始
  - https://developers.meta.com/horizon/documentation/unity/unity-getting-started/
- Unityプロジェクト設定
  - https://developers.meta.com/horizon/documentation/unity/unity-project-setup/
- Meta Quest Link（Windows要件を含む）
  - https://developers.meta.com/horizon/documentation/unity/unity-link/
- Interaction SDK サンプル
  - https://github.com/oculus-samples/Unity-InteractionSDK-Samples
  - https://github.com/oculus-samples/Unity-Avatars-InteractionSDK-Samples

## 3. モーション入力（mocopi/Movement）

- mocopi Receiver Plugin for Unity（公式GitHub）
  - https://github.com/Sony-Honda-Mobility/mocopi-receiver-plugin-for-unity
- mocopi Receiver Plugin ドキュメント
  - https://www.sony.net/Products/mocopi-dev/jp/documents/Download/ReceiverPluginDoc/index.html
- mocopi SDKオープンソース化ニュース
  - https://www.sony.net/Products/mocopi-dev/jp/documents/News/SDKOpenSource.html
- Meta Movement SDK（Body tracking）
  - https://github.com/oculus-samples/Unity-Movement
  - https://developers.meta.com/horizon/documentation/unity/move-gs/
  - https://developers.meta.com/horizon/documentation/unity/move-body-tracking/

## 4. Track A（生成）一次情報

- Gemini Image Generation（Nano Banana/Nano Banana Pro）
  - https://ai.google.dev/gemini-api/docs/image-generation
- Gemini Models（`gemini-3-pro-image-preview`）
  - https://ai.google.dev/gemini-api/docs/models#gemini-3-pro-image-preview
- Thought Signatures（編集ループ時の注意点）
  - https://ai.google.dev/gemini-api/docs/thinking
- Vertex AIモデル仕様（解像度等）
  - https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-pro-image

運用注意（2026-03-02時点）:

- `Gemini 3 Pro Preview`（推論モデル）は 2026-03-09 に終了予定と告知あり。画像系モデルを含め、モデルID変更を前提に `config/provisional_rules.json` 側で切替可能に維持する。
- 画像編集の多ターン運用は Thought Signatures の戻し忘れで品質劣化しやすい。REST直叩き時は署名の往復を必須ルールにする。

## 5. WebCam再変身の近道（Try-On/Pose）

- MediaPipe Pose Landmarker (Web)
  - https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/web_js
- Snap Lens Studio Clothing Try-On
  - https://developers.snap.com/lens-studio/features/try-on/clothing-try-on
- Snap Lens Studio Try-On Guide
  - https://developers.snap.com/lens-studio/4.55.1/references/guides/lens-features/tracking/body/try-on
- Snap Lens Studio Cloth Simulation Try-On
  - https://developers.snap.com/lens-studio/features/try-on/cloth-simulation-try-on

## 6. 三面図 -> 3D 接続（R&D）

- Hunyuan3D-2（公式）
  - https://github.com/Tencent-Hunyuan/Hunyuan3D-2
  - https://huggingface.co/spaces/tencent/Hunyuan3D-2
- TripoSR（公式）
  - https://github.com/VAST-AI-Research/TripoSR
  - https://arxiv.org/abs/2403.02151

## 7. 採用評価テンプレ（週次更新）

- 実装コスト: `S`（0.5日以内） / `M`（2日以内） / `L`（3日以上）
- 既存Track衝突: `none` / `low` / `high`
- 体験価値: `儀式感` `固有性` `再変身性` の3軸で 1-5 点
- 判定:
  - `adopt-now`: 今週導入
  - `spike-next`: 次週スパイク
  - `hold`: 保留（理由を1行）
