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

## 8. 未完・宿題リスト

1. 工場3段階デプロイ(乱数符/ギャラリー/キュー上限/計時が未反映の場合)
2. Quest実機テスト: チャンバーの頭回転符号・腕IK感触・鏡距離 → 符号はコード先頭付近の定数調整
3. Vercel env: TTS_PROVIDER=aivis + AIVIS_API_KEY(+必要ならAIVIS_MODEL_UUID)
4. .env実鍵のローテーション(Gemini/Supabase service/Sakura) — LAN配信期間あり
5. recall_codes の RLS有効化(SQL1行)
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
