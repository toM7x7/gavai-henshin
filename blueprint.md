了解。方針、めちゃくちゃ良いです。

**mocopi＝モーションより「体躯（Morphotype）同定の精度」**に寄せる
2ライン並走（スーツSIM/生成ラインとXR変身ライン）
まずは スーツ生成の精度を上げる（SIM的に） → そこからXRへ
途中途中で「できた鎧を着る」＝モチベ爆上げの“試作着装”ゲートを用意する

この前提で、エンジニアに渡せる形に **仕様書・青写真・開発計画（v0.2）**を作り直しました。 （※展示会に“ロアや登場人物を出さない”前提も織り込み済み。ロアは内部用の思想として、工程・ログ・文言の圧に落ちるだけ。）


変身・蒸着体験 開発仕様書 / 青写真 / 計画書（SIM-first / 2ライン並走）
Version: 0.2（エンジニア叩き台） 目的：エンジニアと揉むための“共通言語”を作る（実装チケット化しやすい粒度）


1. 結論：開発戦略（今回の勝ち筋）
1.1 戦略は「SIM-first + 2ライン + データ契約先行」
Track A（Suit Forge / SIM & 生成）

NanoBananaPro中心に「鎧立て（アーマースタンド）」を早期に回す
3面図/青写真生成 → スーツ構造（SuitSpec）へ落とす → 3Dプレビューで“着る”

Track B（Transform Stage / XR & 体躯同定）

Quest Link運用で、変身工程（B→C→D→蒸着→封印）を安定させる
mocopiは「モーション」より Morphotype（体躯）同定に振る

重要：2ラインを最終的にマッチさせる鍵は「共通データ契約（SuitSpec/Morphotype）」 → ここを最初に固めないと、Aがコンセプトアート地獄、BがXR演出地獄になって合流できない。
1.2 モチベ設計（“試作を着る”を工程に組み込む）
各スプリント（または各ゲート）で必ずこれをやる：

新しいスーツを1着“立てる”（鎧立て）
それを3Dで“着る”（非XRでもOK）
できればXRで“蒸着する”（最終目標）

これを **「Wear Build」**と呼んで、進捗の可視化とチームの笑顔を強制発生させる。


2. システム青写真（全体像）
2.1 コンポーネント
A. Suit Forge（生成・SIM）

画像生成：青写真、3面図（前/横/後）、エンブレム
構造化：SuitSpec（JSON）生成
アーマースタンド表示：Armory Viewer（Unity/PCでOK）

B. Transform Stage（XR）

体躯同定：Morphotype生成（mocopi/手入力/将来Web推定）
変身工程：仮組み（モックアップ）→ 投影試着 → 蒸着 → 封印

C. Archive（記録）

Session保存：画像・JSON・ログ・動画
後からWebカムで同じSuitIDを呼び出す
2.2 図（合流ポイントを明示）
          ┌───────────────────────────┐

          │ Track A: Suit Forge (SIM)  │

          │  - 3面図/青写真/エンブレム │

Prompt →  │  - SuitSpec生成            │  → SuitPackage

          │  - Armory Viewerで試着      │

          └───────────┬───────────────┘

                      │ (共通データ契約)

                      ▼

          ┌───────────────────────────┐

          │ Track B: Transform Stage XR │

          │  - Morphotype(体躯)同定     │

          │  - 仮組み→投影→蒸着→封印    │

          │  - 収録/保存                │

          └───────────────────────────┘


3. データ契約（最初に固める：A/Bを繋ぐ“骨”）
3.1 SuitSpec（スーツ仕様JSON）
目的：生成物（画像）だけで終わらず、必ず実装可能な構造に落とす。

最低限のフィールド（v0.2）：

suit_id（型式番号）
style_tags（鎧の方向性：メタル/昆虫/バイザー等）
modules（ヘルメット/胸/肩/背中…：モジュール合成前提）
palette（主/副/発光）
blueprint（画像パス + 投影方式）
emblem（画像パス + 貼り位置）
effects（蒸着時間、粒子密度、ワイヤ→金属カーブ）
text（蒸着ログ字幕、名乗り字幕）
generation（プロンプト、seed、モデル名など）

NanoBananaPro（Gemini 3 Pro Image Preview）のモデルIDは gemini-3-pro-image-preview として提示されている。 (Google AI for Developers) 画像生成の仕様はVertex AI側ドキュメントにまとまっており、Gemini 3 Pro Imageは最大 4096px の生成が可能と説明されている。 (Google Cloud Documentation)
3.2 Morphotype（体躯プロファイル）
目的：スーツが“その人の体躯に合う”を作る。mocopiはここに寄与。

最低限のフィールド（推定でOK）：

height（手入力可）
shoulder_width
hip_width
arm_length
leg_length
torso_length
scale（全体スケール）
source（manual / mocopi / webcam など）
confidence（推定信頼度：演出値でもOK）

mocopiの位置づけ： 「リアルタイムモーション」より、Tポーズ校正で得られる骨格比率の推定に価値を置く。 （mocopi Receiver PluginはUnityでモーションデータ受信→アバター適用ができる前提を押さえる。 (ソニー株式会社) この“受信してアバターへ流す”導線があるので、そこから体躯パラメータ推定へ拡張しやすい。）


4. 機能仕様（MVP → 展示会）
4.1 Track A：Suit Forge（SIM & 生成）仕様
A-1. 鎧立て（アーマースタンド）＝最初の快感ポイント
入力：タグ + 誓い（内部用） + 色 + 形状（スライダーでもOK）

出力：

3面図（前/横/後）のコンセプトシート（1枚にまとめるのが理想）
青写真（Blueprint）（投影用）
エンブレム
SuitSpec.json

Gemini 3系の画像生成は「画像生成・編集」を扱い、会話的な編集では thoughtSignature が重要と説明されている。 (Google AI for Developers) → 3面図の整合性を上げるために「最初の1枚→編集で側面/背面」など、反復編集を前提にしたパイプラインを検討する価値がある（最初から完璧な3面図を一発で狙わない）。
A-2. 構造化（SuitSpec生成）は「画像→自動」じゃなくても良い
MVPの現実解：

画像はAI生成（見た目の興奮）

SuitSpecは **半自動（テンプレ+選択）**で早く安定化

モジュールはキット化
生成画像は「投影/刻印/デカール」として利用

→ “SIM精度を上げる”の定義は、まず **「3Dでそれっぽく成立する」**に置く。
A-3. Armory Viewer（Unity PC）＝「途中で都度着る」場所
Unityの非XRモードで、即座に試着できる

機能：

モックアップ体（マネキン）表示
Morphotypeスライダーで体型を変える（後でmocopi入力に置換）
スーツを装着（モジュール合成 + Blueprint投影）
蒸着演出を簡易再生（XRに入る前でも気持ちいい）
1クリックで「このスーツをパッケージ化（SuitPackage出力）」

ここが“モチベ燃料”の工場になる。


4.2 Track B：Transform Stage（XR）仕様
B-1. QuestはPC Link運用前提（展示会安定）
UnityのMeta OpenXRのドキュメントでは Quest Link/Horizon LinkはWindowsのみサポートと明記されている。 (Unity マニュアル) → 展示会用ノートPCはWindowsが前提条件（要件に書く）。
B-2. 変身工程（B→C→D→蒸着→封印）
Scene B：Morphotype同定（Tポーズなど）
Scene C：モックアップ体に仮組み（Dry Fit）
Scene D：本人へ投影試着（Fit確定）
Scene E：蒸着（ワイヤ→粒子→金属化）
Scene F：封印（エンブレム焼き付け）
Scene G：記録（保存/特典映像）
B-3. mocopiは「体躯推定」に寄せる
mocopiのリアルタイム姿勢は最初は使っても使わなくてもOK

価値は 校正→骨格比率推定→Morphotype生成の部分に置く

Tポーズ数秒保持 → 関節距離を平均化 → 比率を算出 → Morphotypeとして保存


4.3 WebカムTry-on（持ち帰り線）は“別ゲート”として残す
ユーザーの今回の優先は「SIM→XR」なので、Webは後ろに回してOK。 ただし後で繋がるよう、SuitSpec共通は守る。

将来の技術候補として、MediaPipe Pose LandmarkerはWebで姿勢ランドマーク（2D + 3D）を出力できる。 (Google AI for Developers)


5. ロードマップ（2ライン並走 + 合流ゲート）
時間ではなく「ゲート（到達条件）」で管理。 各ゲートで必ず **Wear Build（試作着装）**を実施。


Gate 0：データ契約と“鎧立て最小快感”の成立（最初の合意）
Track A（必須）

SuitSpec v0.2確定
Armory Viewer（マネキン+装着+回転+保存）最小実装
“ダミー画像”でも良いので鎧立てが1回成立

Track B（並行）

Unity XRプロジェクト作成（Quest Linkで起動できるまで）

DoD

SuitIDを作り、Armory Viewerで1着「着れる」
そのSuitSpecを保存できる


Gate 1：NanoBananaProで「3面図/青写真」生成が回り始める（モチベ点火）
Track A

生成UI（社内ツールでOK）で

青写真生成
3面図シート生成（まずは“それっぽい”でOK）
エンブレム生成

生成結果をSuitSpecに紐づけ、Armory Viewerで投影できる

DoD

「生成 → すぐ鎧立て → すぐ着る」が1分〜数分で回る
失敗時フォールバック（過去の生成を再利用）あり


Gate 2：SIM精度を上げる（“成立する鎧”の型が固まる）
Track A

モジュールキット（最低4部位）を作る

生成画像は

Blueprint投影（刻印）
Emblem貼り付け の2点で“実装に落ちる表現”を確立

Morphotypeはスライダーで調整可能

DoD

10パターンの鎧が安定して“立つ/着れる”
体型を変えても大破綻しない（関節の逃げ設計）


Gate 3：XR変身（蒸着）が完成し、SuitPackageを着られる
Track B

XRでB→C→D→蒸着→封印を完走
Track AのSuitPackageをXRでロードできる

DoD

“1着の鎧”がXRで蒸着できる（モジュールでもOK）
モニター出し（A画面）で観客に見せられる


Gate 4：mocopiでMorphotype推定を入れて「体躯フィット感」を上げる
Track B

mocopi受信 → Tポーズ校正 → 骨格比率推定 → Morphotype保存
Armory ViewerにもMorphotypeを適用できる（AとBの一致）

DoD

同じ人が、Armory ViewerとXRで“同じ体型”になる
体躯差で鎧のクリアランスが自然に見える


Gate 5：記録（特典映像）と保存が揃う
Track B

Sessionフォルダに成果物一式

SuitSpec / Blueprint / Emblem / Log / Video

DoD

体験後に「持ち帰れる」状態（ローカルでOK）
後でWebカムTry-onに繋げられる構造（未実装でもよい）


6. エンジニアに渡すタスク分解（チケット例）
6.1 Track A（Suit Forge）
[A-01] SuitSpec v0.2 定義（JSON Schema + サンプル10件）
[A-02] Armory Viewer（Unity PC）最小：読み込み/回転/保存
[A-03] モジュールキット設計（Helmet/Chest/Shoulder/Back）
[A-04] Blueprint投影（Decal/Projector/Triplanarのどれか）
[A-05] NanoBananaPro生成CLI or 小UI（画像生成/保存/紐づけ）
[A-06] 生成→SuitSpec自動埋め（半自動でもOK）
[A-07] Wear Build手順（1着作って着るまでの最短手順書）
6.2 Track B（Transform Stage XR）
[B-01] Unity XRプロジェクト（Quest Linkで再生できる）
[B-02] 変身ステートマシン（B→C→D→蒸着→封印）
[B-03] 蒸着シェーダ（ワイヤ→粒子→金属化）
[B-04] SuitPackageロード（A成果物の取り込み）
[B-05] mocopi受信導入（Receiver Plugin統合） (ソニー株式会社)
[B-06] mocopi→Morphotype推定（Tポーズ平均→比率算出）
[B-07] 記録出力（JSON/画像/動画の整理）
6.3 共通
[C-01] セッション管理（ID発行、保存、再読み込み）
[C-02] フォールバック設計（生成失敗時に“落ちない”）


7. リスクと“展示会で死なない”対策
生成が荒れる / 遅い

→ 生成は「見せる成果物（青写真/エンブレム/ログ）」に限定して、3Dはモジュール合成で守る
→ 失敗時フォールバック（過去アセット・テンプレ）を必ず用意

2ラインが合流しない

→ Gate 0でデータ契約（SuitSpec/Morphotype）を固定する

mocopiが狙い通り“体躯”に効かない

→ まずはスライダーMorphotypeで成立させ、mocopiは“精度を上げる追加”にする
→ 測れない寸法（胸厚など）は無理せず「見た目の逃げ（関節スライド/装甲の余白）」で吸収


8. “癖の強い笑顔”で揉むための運用ルール（おすすめ）
Weekly Wear Build（毎週1回）

新しい鎧を1着生成 → Armoryで着る → XRで蒸着（できたら）
これがその週の成果物（客観評価が簡単）

Forge Review（15分）

3面図の整合性、関節の逃げ、封印の視認性だけをチェック（項目固定）

二者択一ルール

迷ったら「実装に落ちる表現（投影/刻印）」を優先、完全生成3Dは後回し


9. いま決め打ちして良い前提（ズレたら差し替え）
開発PCは Windows（Quest Link/Horizon Linkの制約） (Unity マニュアル)
スーツ3Dは モジュール合成が正（生成は画像・ログ・文言で魅せる）
mocopiは Morphotype精度向上のために使う（モーションは後でいい）


10. 次の一手（あなたがエンジニアに渡す“初回指示”テンプレ）
「2ライン並走でやる。まずGate0を切る」

SuitSpec v0.2 と Morphotype v0.2 を確定
Armory Viewerで“1着着る”までを最短で作る（ダミーでもOK）
並行してXRプロジェクトを立ち上げ、蒸着演出の最小を作る
Gate1でNanoBananaPro生成を回し始める（モチベ燃料）


参考（公式ドキュメント）
Gemini 3 Pro Image Preview モデル仕様（gemini-3-pro-image-preview） (Google AI for Developers)
Gemini 3の画像編集における thoughtSignature（会話編集） (Google AI for Developers)
Vertex AIの画像生成（Gemini 3 Pro Image 最大4096px等） (Google Cloud Documentation)
Unity Meta OpenXR の Quest Link / Horizon Link（Windowsのみ） (Unity マニュアル)
mocopi Receiver Plugin for Unity（Unityで受信→アバター適用） (ソニー株式会社)
MediaPipe Pose Landmarker（Webで姿勢ランドマーク） (Google AI for Developers)


付録：Unity素人（あなた）向け“今ここだけ分かればOK”メモ
Armory Viewer：Unityを“ただの3Dビューワ”として使う。XRより先にここで勝つ。
Prefab：ヘルメット/胸/肩…を部品化して差し替える仕組み。モジュール合成の心臓。
Material/Shader：蒸着の気持ちよさはここで作る（ワイヤ→金属）。
ScriptableObject（任意）：SuitSpecをUnity側で扱いやすくする器（最初はJSON直読みでもOK）。



---

## 1つだけ、あなたの熱を増幅させる提案（決め打ち）

「SIM精度を上げる」＝ **“鎧が立つ”**の判定基準を、最初に3つに絞りましょう（エンジニアと揉むときの共通指標になる）。

- **Silhouette（シルエットが強い）**：遠目に鎧だと分かる  

- **Joint Safety（関節が破綻しない）**：膝/肘/肩に逃げがある  

- **Seal Readability（封印が読める）**：胸の決めポイントが潰れてない  

この3つを満たす限り、生成の自由度は無限に広げてOK。  

満たさないなら「生成の良し悪し」ではなく「規格外（設計不成立）」として潔くリフォージ（再鍛造）する。

---

必要なら次の返信で、**Gate0を即実装に落とすための「SuitSpec v0.2 JSON Schema（例）」「Armory ViewerのUIワイヤー」「Wear Build手順（5分で回す）」**まで具体化して渡せる形にします。

::contentReference[oaicite:14]{index=14}

