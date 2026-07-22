# 蒸着執行録 — 引き継ぎ資料(2026-07-11時点の全体仕様)

Status: Active — このファイルが「いまのシステムの正」。次のセッション/開発者はまずここを読む。

## 1. コンセプトと全体像

**言葉(思い)→ 設計局AIが設計図として解釈 → Blenderが鎧を鍛造 → 呼出符で召喚 →
蒸着(変身)体験(Web/Webカメラ/VR)**。変身は法定プロセスというロア(Lore Bible.md)。
対象イメージ: 小学生の心を持った大人に刺さる特撮世界観。

```
[Vercel: web/]                     [Cloud Run: cloud/forge/]           [Supabase]
 / ....... 扉(鍛造/召喚の二択+鍛造記録)   forge_server.py                Storage: suits/<code>/
 /forge ... 言葉入力→工程トラッカー   ── POST /forge ──→  設計図(Gemini必須)      assembly.glb / vrm.vrm /
 /s/[code]  蒸着室(VRM+VRMA+メニュー)     │                Blenderヘッドレス鍛造    vrma.vrma / suit-package.json
 /mirror/.. Webカメラ変身(点群/実写AR)     │                適合審査→アップロード    gallery.json(鍛造記録)
 /ar/[code] VR蒸着チャンバー(埋め込み)  ← /job ポーリング   呼出符発行(乱数5桁)     Postgres: recall_codes
 /api/* ... プロキシ層(秘密鍵はサーバ側)
```

- **本番ブランチ**: `codex/new-route-canonical-identity-lock`(mainではない!Vercel Production Branchもこれ)
- リポジトリ: github.com/toM7x7/gavai-henshin(入れ子: D:\personal_dev\gavai-henshin\gavai-henshin)

## 2. デプロイ手順(いつもの)

**web/ だけの変更** → `git push` で Vercel 自動デプロイ。作業なし。
**cloud/forge, src/, tools/ の変更** → [cloud/forge/README.md](../cloud/forge/README.md) 冒頭の3段階
(`git pull` → `gcloud builds submit` → `gcloud run deploy`)。
**Vercel env変更** → Redeploy必須(NEXT_PUBLICはビルド焼き込み)。

⚠ 罠: web/ で devサーバ稼働中に `npm run build` すると .next が破損し全ページ500
→ devを止めて `rm -rf .next` → build。

## 3. 環境変数の台帳(どこに何があるか)

| 変数 | 置き場所 | 用途 |
|---|---|---|
| NEXT_PUBLIC_SUPABASE_URL | Vercel(公開可) | ビューアの読み出し先。**素のURL**(/rest/v1等を付けない — lib/suit.jsは付いていても除去する) |
| FORGE_URL / FORGE_TOKEN | Vercel(サーバ専用) | 鍛造工場プロキシ(/api/forge) |
| SAKURA_AI_ENGINE_TOKEN | Vercel(サーバ専用) | 音声認証Whisper(/api/stt)+TTS(sakura) |
| TTS_PROVIDER | Vercel | **aivis**(本命)/ sakura / gemini |
| AIVIS_API_KEY / AIVIS_MODEL_UUID | Vercel(サーバ専用) | Aivis Cloud TTS。**クレジット自動追加なし** — 402/429は「今日は喋らない日」: 利用者非通知・無音、ログ AIVIS_CREDIT_OUT で管理者確認 |
| GEMINI_API_KEY (+GEMINI_TTS_VOICE) | Vercel(TTS=geminiの時)/ Cloud Run(解釈・必須) | 設計図解釈=コンセプトの肝。モデルは GEMINI_TEXT_MODEL |
| SUPABASE_URL / SUPABASE_SERVICE_KEY | Cloud Run + ローカル.env **のみ** | 書き込み権限が強力なのでVercel禁止 |
| ローカル .env | リポ直下(gitignore済) | 上記の原本。**LAN配信期間があったためローテーション推奨(未実施)** |

## 4. 体験仕様(確定事項)

- **合言葉は「蒸着!」**。聞き間違い辞書(定着/常着/上着)+「変身」救済。lib/stt.js TRIGGER_RE
- **スタートは必ず未変身(素体)**。蒸着=閃光+SE+粒子+鎧マテリアライズ+henshin.vrma+TTS「蒸着、完了。」。解除で巻き戻し(何度でも)
- 鎧メッシュの判別は名前 `/armor/i`(VRMは結合済み `armor_suit`)— lib/suit.js armorMeshes
- **音声認証はハイブリッド**: Web Speech(Chrome)一次 / Sakura Whisper(/api/stt)フォールバック(Quest)
- **TTSは定型句ホワイトリスト制**(/api/tts ALLOWED — 句を増やす時はここに追加)
- SEスロット(web/public/se/README.md): henshin/deposit/click/forging-loop/stage(全て任意・置くだけ)
- 呼出符 = GAVAI-+乱数5桁(0O1I除外)。連番は推測可能なので禁止
- /forge完了は自動遷移しない(呼出符コピーの「間」)

## 5. 各画面の実装メモ

- **/s 蒸着室**: VRM+VRMAベース(質感はMToon)。メニュータイル: 蒸着(⚡primary)/VRで蒸着(🥽)/Webカメラで変身体験(📷)/VRMエクスポート(💾)。VRM無し旧パッケージはGLBフォールバック
- **/mirror**: トラッキングv4(Two-Bone IK+One Euro+可視性ゲート)。モード2つ:
  点群(既定) / **実写AR合成**(2026-07-11実装: カメラ映像を背景に、2Dランドマークをz=0平面へ逆投影して腰位置+肩腰スパンでVRMを整列。v1は遮蔽なし。**v2=MediaPipe Image Segmenterの人物マスクで前後合成**が次の本命)
- **/ar 蒸着チャンバー(VR)**: 自分の体への埋め込み。3点トラッキング(HMD=ルート+体yaw+頭、コントローラ=腕IK)。身長自動キャリブレーション。**首から上はfirstPerson.setup()で自分から不可視・鏡(全身クローンのミラー配置、material.side=DoubleSide必須)には映る**。空間内パネル(canvas)が全案内。右トリガー=蒸着の儀/左トリガー=解除。コントローラ実機モデル+色分けレイ表示。**Quest実機での頭回転の符号確認が未**
- **IWSDK採用計画**: 現状はthree標準で充足。空間ボタン(レイでクリック)やハンドトラッキングが欲しくなったら@iwsdk/core導入。参考実装=viewer/quest-iw-demo(旧展示: mocopi+IWSDK+Sakura)

## 6. 鍛造工場(Cloud Run)の仕様

- ルートB(Gemini解釈)**必須**: GEMINI_API_KEY無しで起動拒否。障害時のみルートAフォールバック(routeに記録・UI表示)
- ジョブ: stage(1解釈/2鍛造/3格納/4公示)+timings(秒)を/jobで返す。ログFORGE_DONEに計時
- 防御: X-Forge-Token(compare_digest)/64KBボディ上限/**キュー上限3で429**/Vercel側レート3回10分
- gallery.json(公開)を毎鍛造で更新→扉の「鍛造記録」
- **速度改善の本命=二段階納品**(README「次の一手」設計済み・未実装): GLB出現を監視して先に呼出符発行、VRMは後追いでmanifest差替え。体感5分→90秒級

## 7. エンジン(Blender)の現在地と次

- 詳細は docs/armor-blueprint-generator.md / armor-body-fit-rules-2026-07.md / hero-proportion-grammar-2026-07.md
- 直近: 襟甲(collar)による胴分節、腋下/脇腹の被覆audit+閉鎖、審査偽陽性3クラス修正
- **次の実装順(合意済み)**: ①二段階納品 ②武装モジュール(剣/盾/銃 — _GEAR_WORDS検出は稼働済み、文法延長のみ) ③クレスト増幅 ④設計局AI命名(suit_name)+焦点 ⑤非対称/マント ⑥テクスチャ・エンブレム(nano_banana)

## 8a. 体験課題ログ(2026-07-11 ユーザーテスト起点)

| # | 課題 | 状態 |
|---|---|---|
| T1 | 鍛造ループSEが数分同じ金属音=つらい | ✅ 20秒後に自動で音量を落とす+全画面SEミュートトグル実装 |
| T2 | SE全体のON/OFFが欲しい人がいる | ✅ 右下スピーカートグル(localStorage永続)実装 |
| T3 | /mirror起動直後「素体だけ+右上UIだけ」で迷う | ✅ 中央に大きな開始CTA(カメラ開始→蒸着の導線)実装 |
| T4 | VRで開くべきURLの案内が不親切 | ✅ /vr(Quest向け入口: 5文字入力→チャンバー直行)+扉にQuest導線 |
| T5 | 呼出符のGAVAI-は毎回打ちたくない | ✅ 入力欄をプレフィックス固定+5文字入力に(貼り付け時は自動正規化) |
| T6 | VR内音声認識が厳しすぎる/音声なしモードに落ちる | ✅ 緩照合(TRIGGER_LOOSE_RE)+真因修正: ページ読込時のgetUserMediaをQuestが無言拒否していた→**トリガーの瞬間(ユーザー操作内)に取得**。音声障害時も恒久降格せず「2度引きで強行」の明示2段階。儀式(唱える)は必ず通る |
| T7 | VR内がまだずんだもん | ✅ 真因=ブラウザキャッシュ(max-age 86400で旧声が残存)→ announce()にv=キャッシュバスター+max-age 3600。あわせてenv: TTS_PROVIDER=aivis + AIVIS_API_KEY 必須 |
| T8 | 下半身トラッキングがない | ✅ v1(しゃがみ+膝IK)+**WebXR Body Tracking API対応**(optionalFeatures body-tracking、frame.bodyのhips/left-foot/right-footで実関節駆動、無ければ手続き式へ自動フォールバック)— Quest実機で要確認 |
| T9 | VR内で自分のスーツが全く見えない(2Dでは首なしが見える) | ✅ 作り替え: three-vrm firstPersonレイヤ方式を廃止 → **首クリッピング平面**(自分のアバターは頭のすぐ下から上をclippingPlaneで刈る。素体ごと残るので指も見える。鏡クローンは無加工=頭込み全身) |
| T10 | VR内で呼出符を書き込みたい(3Dキーボード) | ✅技術確立: XRift分室の「照合盤」(T13)と同方式 — Interactableキー32字+表示板。/arチャンバーへの移植はロードマップLater |
| T11 | 「ギャバントリガー」的なコントローラUIアイテム | 未 — 空間内の持てる変身アイテム(掴む→構える→発声)として設計予定 |
| T12 | 実写AR合成の整列品質が未達(全然重ならない) | 🔧 精緻化v2実装済(dev限定のまま): ①真因=object-fit:coverのクロップ補正漏れ→coverMap写像 ②連続リスケール廃止→**奥行き配置**(スケール等倍固定、肩腰スパンpx→カメラ距離を算出しヒップをレイ上に置く) ③**ルートyaw**=腰ラインで体の向きごと回す ④腕+脚の**画面空間拘束IK**(手首/足首/肘/膝の2Dレイ上に目標を置く。横位置=画面精度、奥行きだけworld差分) ⑤AR中は`setBodyVisible(false)`で素体を隠し実写の体が素体を務める—「蒸着!」で鎧だけ装着(wornFlag) ⑥2Dアンカー用OneEuroバンク(euro2d) ⑦**映像がUI全部を覆う実機バグの真因**(2026-07-15): videoをbody直下に追加するとChromiumでは`position:fixed`のmainがstacking contextになり、後入れのvideoが**z指定に関係なく**main配下UI全体の上に描画される → videoは**mount内 z0**に移動(レイヤ規約: video0/WebGL1/debug3/HUD5/CTA6/計測7/nav10) ⑧**AR計測パネル(dev)**: 「体を撮れているか」と「モデルが追従しているか」を分離検証 — 骨格オーバーレイ(33点+辺、可視度で緑/黄/赤。実写に乗れば取得+写像OK)/モデル残差(マゼンタ○=モデル関節の投影、実写関節までのpx)/モデル表示OFF(骨格のみ検証)。捕捉✗・推論エラーをパネルに明示(detectForVideoの例外黙殺を廃止)、GPU→CPU推論フォールバック追加。⑨**実機計測ラウンド1**(2026-07-15、骨格は実写に乗る/60fps/残差 手L41・手R14px): (a)残差の真因=固定奥行き+腕長クランプでは腕を伸ばすと届かず画面上でズレる → **レイ×到達球の交差**(2Dレイ上で届く範囲のうち希望奥行きに最も近い点を目標に。届かない時はレイ上の最近点=画面ズレ最小) (b)**蒸着後は素体ごと出現**(空洞鎧の解消 — アンダースーツが隙間を埋める。AR待機中はモデル全隠し=素の自分だけ) (c)**実写マスク**: PoseLandmarkerのoutputSegmentationMasks(dev時のみ)で人物領域を取得し、蒸着後は自分をシルエットに沈める(blur10pxで広めに+brightness0.22 — 「変身した以上、素の自分が映ってはいけない」)。レイヤ: video0/マスクfx1/WebGL2 (d)ARでは缶詰VRMAモーションをスキップ(実写とズレて破綻するため追跡継続、演出は閃光+粒子+マスク)。⑩**実機計測ラウンド2**(2026-07-16、FB: 追従は良好/薄く見えるマスク=NG/モデルが背面+腕捻れに見える): (a)**ARは「撮影向き」固定**(Zoomアバター式) — ARをONにすると鏡像を強制OFF+チェック無効化。鏡像は「CSS反転×ランドマーク左右入替×座標x反転」の三重合わせで腕の左右食い違い・前後捻れの温床だった。映像に映る人間そのままの向き・左右にモデルを重ねる規約に一本化(スマホで他人を撮る将来ユースにも一致) (b)**マスク完全不透明化**: 「うっすら見える」は不可 → 暗色#0b1118のベタ塗り(source-in)+閾値0.3で内部を塗り切る+blur(6px)3度描きで広めに+**時間方向の粘り**(前フレームマスク×0.8とmax=輪郭ちらつき抑制) (c)体の向きyawを前方ベクトル(腰ライン×上)ベースに書き換え+devパネルに**「前後反転」トグル**(実機で背面に見えたらONにして報告→符号を恒久化する診断手順)。⑪**実機ラウンド3=真因確定**(2026-07-16、FB: 全然直ってない/背面+腕交差継続/黒塗り無意味): (a)**背面+腕交差の真の根本原因 = rotateVRM0()**。VRM0モデルはルート`rotation.y=π`で「カメラ正対」になるのに、AR配置コードはyaw0=正対と仮定→AR進入で常に180°逆(腕IKは正面目標へ背面から伸ばすので常時交差)。修正: `baseYaw=vrm.scene.rotation.y`をロード直後に実測し、rootYaw=baseYaw+偏差。applyArの非AR復帰も`rotation.set(0,baseYaw,0)`(0リセットは正対破壊バグだった) (b)**体験仕様確定: AR=鏡像固定**「鏡に映った自分がヒーローになっている」— AR ONで鏡像強制ON。左手を動かせば画面左側の手が動く(2Dミラーで実証済みの写像を再利用)。将来のスマホで他人を撮る形は左右判定を別途調整(その時は撮影向き) (c)**黒塗り廃止→背景置換=存在の消去**: 背景プレート(人物以外の画素でα0.12常時更新+「背景を記憶」ボタンで3秒後に無人背景を撮影)を人物マスク領域に流し込む。プレート未撮影時は育ち途中プレートのぼかし版で退避 (d)**指トラッキング**: HandLandmarker(dev限定・トグルあり)、21点の関節角実測→VRM指ボーンカール(Proximal/Intermediate/Distal、左z負/右z正)。左右はhandednessでなく**ポーズ手首との画面距離**で対応付け(規約取り違えを構造回避)。親指は控えめ。顔は不要(スーツで隠れる)方針。残: 実機で正対/鏡像対応/背景消去の検証、指カールの軸符号実機確認、録画、掛け声/ポーズ起動 |

| T13 | XRift分室: VRで呼出符を入力するとブラウザから弾かれて再入場になる | ✅真因特定+置換(2026-07-20): world-componentsのTextInputは`requestTextInput`で**プラットフォームのDOM/システム入力UI**を呼ぶ設計 — WebXRの没入セッションはDOMキーボード表示で中断される(仕様制約、ワールド側の不備ではない)。→ **呼出符 照合盤**(ワールド内3Dキーパッド: 字母32キー8×4+⌫/消去/照合、Interactableのみで完結)に置換。VR/デスクトップ共通で動き、採番規約と同じ字母(0/O/1/I除外)なので誤入力も構造的に排除 |

## 8. 未完・宿題リスト

> **優先順の正本は [ROADMAP-2026-07.md](ROADMAP-2026-07.md)**(世界観対応表つき)。以下は個別宿題のメモ。

1. 工場3段階デプロイ(乱数符/ギャラリー/キュー上限/計時が未反映の場合)
2. Quest実機テスト: チャンバーの頭回転符号・腕IK感触・鏡距離 → 符号はコード先頭付近の定数調整
3. Vercel env: TTS_PROVIDER=aivis + AIVIS_API_KEY(+必要ならAIVIS_MODEL_UUID)
4. .env実鍵のローテーション(Gemini/Supabase service/Sakura) — LAN配信期間あり
5. recall_codes の RLS有効化(SQL1行)
6. 実写ARトラッキング強化 — ar-tracking-roadmap-2026-07.md(Segmenter→heavy A/B→輪郭フィット→オフライン高品質パイプライン)
7. XRiftスーツギャラリー — xrift-gallery-plan-2026-07.md(Phase 1: 外部fetch可否の技術検証ワールド。変身は当面「アバター並行登録+導線」で代替)
6. main への統合 + node_modules 197MiB の filter-repo(公開前必須)
7. 実写ARのv2(Segmenterマスク合成)、蒸着演出の部位順次マテリアライズ化
8. Cloud Run env → Secret Manager移行(任意)

## 9. 重要な教訓(同じ穴に落ちないために)

- Blenderの拡張導入は `extension sync` 先行+`--online-mode`(新品プロファイルはオンライン許可OFF)
- **/healthz はGoogle予約パス**(run.appでGFEが404) → /health を使う
- 遅延import(jsonschema等)はローカルで捕まらない → コンテナにpip installを忘れない
- コンパイラにrng呼び出しを足すと**乱数列がずれて全部位の意匠が変わる**(見かけの回帰)
- 適合審査の偽陽性は「荷重を受けている」ことがある(内腿の誤検出票がrigid_shift暴走を抑えていた) — フィルタはスコープを絞る(crease_filterはwaist限定)
- HTML内埋込JSはast検査不能 — 識別子改名は全参照grep+ブラウザconsole実走
- SUPABASE_URLに/rest/v1付きを貼る事故 → lib/suit.jsは正規化済みだが.env側も素のURLで
