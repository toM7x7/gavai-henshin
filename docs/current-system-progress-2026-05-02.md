# Current System Progress - 2026-05-02

このメモは、現時点の全体進行を「Web Forge」「Quest VR」「モデル/パーツ」「SakuraAI」「クラウド化」の5領域で整理するための作業ログです。

## 全体方針

主線は `Webで装着する武装を成立させる -> Questで4桁コードから呼び出して変身装着する -> Trial/Replayとして体験を残す` です。

ロア上の基準は「生成した鎧をただ置く」のではなく、「ユーザーの入力から守る対象・気質・色・モチーフを読み、基礎スーツ、外装パーツ、発光ライン、変身体験まで一貫した武装として扱う」ことです。

## Web Forge

- `viewer/armor-forge` は `POST /v1/suits/forge` 経由で4桁 `recall_code`、SuitSpec、manifest、preview data を返す流れまで進んでいます。
- Web preview は VRM表面を基礎ボディスーツとして扱い、GLB外装パーツを重ねる構成です。
- canonical armor は `previewGlbParts=18` / `previewFallbackParts=0` まで到達しています。
- Wave 2 で variant/topping catalog が入り、部位ごとに複数案を選べる土台ができています。
- 次のWeb側の焦点は、LLM選択結果を `selected_variant_key` / topping / Nanobanana prompt / manifest に一貫反映することです。

## Quest VR

- Quest runtime は `viewer/quest-iw-demo`、Vite port `5173` で動きます。API/dashboard は port `8010` です。
- 2026-05-02対応で、呼び出し成功後に鎧を常時表示する動作を止めました。
- 鎧は原則として「変身装着中」に表示します。
- メニューから明示的に `鎧立て` を押した場合だけ、離れた観察用の鎧立て表示に入ります。もう一度押すと収納します。
- 失敗コードや未呼び出し状態では、VR内に鎧meshを残さない契約に寄せました。
- GLB外装がQuestで小さく見える問題に対して、GLBの正規化bboxを保持し、Quest側でも部位別ターゲット寸法へスケールする初期対処を入れました。

残課題:

- Web Forge は VRMボーン実測から `targetCenterForPart` / `targetSizeForPart` を計算します。
- Quest は HMD/Controller推定位置と固定寸法から live pose を作っています。
- つまり、同じ SuitSpec を読んでいても「装着poseの決め方」はまだ共通化されていません。
- 次の根本修正は `RuntimeArmorPose` 契約を作り、Webで解いた装着位置/回転/スケールをQuestへ渡すことです。

## モデル/パーツ

- canonical 18 module の GLB、blend、modeler sidecar、mesh preview は格納済みです。
- Wave 2 では variant GLB と topping GLB が入り、部位別の選択肢を増やせる構成になっています。
- まだスーツとしての完成度は不足しています。現状は「機構の検証」と「モデラー向けパーツ仕様の橋渡し」が主目的です。
- 背面の薄さ、胸/腰/肩の連続性、細かい顔/体パーツ、特撮スーツらしい密度は Wave 2.1 以降で詰めます。

## SakuraAI

- 音声/TTSは従来通り Sakura AI 系を前提にします。
- LLMは `gpt-oss-120b` を SakuraAI 側で接続する前提です。
- Web Forgeでは、ユーザー入力をもとに LLM が variant/topping を選び、同時に Nanobanana向け表面生成プロンプトを作る流れに寄せます。
- 現時点ではアダプタ設計とローカルmockが主で、本番鍵・実API接続は次段階です。

## クラウド化

クラウド化は、ローカル実装を丸ごと置くだけではなく、体験IDと生成物を durable に扱う方向です。

想定分割:

- Cloud Run: API / Web backend
- Cloud SQL PostgreSQL: suit, manifest, recall_code, trial, replay の正本
- GCS: GLB, texture, replay JSON, generated artifacts
- Firestore: Quest/operator のライブ状態、短命セッション
- Cloud Tasks: Nanobanana生成、GLB処理、重い非同期処理
- Secret Manager: SakuraAI / Nanobanana / service credentials

まずは `GET /health`、`GET /v1/catalog/parts`、`POST /v1/suits`、`GET /v1/suits/:id`、`GET /v1/quest/recall/:code` の最小APIから切ります。

## 直近の優先順位

1. Questで今回の表示契約を実機確認する。呼び出し成功後に常時鎧が出ないこと、変身中だけ出ること、メニューの `鎧立て` で観察表示できることを確認する。
2. QuestでGLBパーツの大きさが以前よりWeb previewに近づいたか確認する。
3. `RuntimeArmorPose` 最小schemaを定義し、Web Forgeの装着計算結果をQuestへ渡す。
4. Web ForgeのLLM variant/topping選択を SakuraAI `gpt-oss-120b` 前提のadapterに接続する。
5. クラウド skeleton を Cloud Run + Cloud SQL + GCS の最小構成で切り出す。

## 検証

- `node --check viewer/quest-iw-demo/quest-demo.js`
- `python -m pytest tests/test_quest_recall_render_contract.py -q`
- `python -m pytest tests/test_quest_recall_render_contract.py tests/test_dashboard_server.py tests/test_new_route_api.py -q`
- `python -m pytest -q`

2026-05-02時点で `python -m pytest -q` は `240 passed, 89 subtests passed` です。
