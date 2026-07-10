# Vercel体験動線 — 装着とアニメーションへ (2026-07-09)

Status: Active / フェーズ移行の設計図

エンジン(体に合う鎧)は基盤完成。ここからは**体験の動線**:
ローカルForge = 生成工場 / Supabase = 保管庫+呼出符 / Vercel = 体験面(ビューア・鏡・AR)。
既存の docs/cloud-architecture-2026-07.md(Cloud Run lift-and-shift)とは併存 —
生成バックエンドの将来像はCloud Runのまま、**表示面を先にVercelで立てる**。

## 全体動線

```
[ローカルForge]                    [Supabase]                  [Vercel]
言葉 → blueprint → assemble ──→ package_suit_for_web.py ──→ Storage: suits/<code>/…
  ├ assembly.glb (フル)            │                          Postgres: recall_codes
  ├ lod1/lod2.glb                  └ manifest(suit-package.json)
  ├ <label>.vrm (ポータブル)                                      │
  └ henshin.vrma (蒸着モーション)                                  ▼
                                                    /s/<code>      オービット+蒸着
                                                    /mirror/<code> Webカメラで体連携
                                                    /ar/<code>     Quest WebXRで装着
```

## パッケージ契約 (suit-package.json)

```json
{
  "package_version": "suit-package.v1",
  "recall_code": "GAVAI-XXXX",
  "blueprint_id": "ABP-...",
  "design_intent": "...",
  "palette": {"base_surface": "#..", "accent": "#..", "emissive": "#..", "trim": "#.."},
  "files": {
    "assembly": "assembly.glb",   // フル品質(デスクトップビューア)
    "lod1": "lod1.glb",           // Quest単体 / mirror
    "lod2": "lod2.glb",           // AR複数体
    "vrm": "suit.vrm",            // メタバース持ち出し
    "vrma": "henshin.vrma"        // 蒸着モーション(アバター非依存)
  },
  "triangles": {"assembly": 0, "lod1": 0, "lod2": 0},
  "fit_summary": {...}, "created_at": "..."
}
```

生成側は `tools/package_suit_for_web.py` がアセンブラ出力ディレクトリから束ねる
(ドライラン=ローカル webdrop/<code>/ へ集約、env があれば Supabase へ直接アップロード)。

## Supabase 最小構成

- Storage バケット `suits`(public read / service-key write)
- テーブル `recall_codes(recall_code pk, blueprint_id, manifest_path, status, issued_at)`
  — schema.sql の recall_codes の縮約版。将来Cloud SQL版と同型なので移行は写すだけ

## Vercel アプリ(Next.js App Router + three.js r164 + @pixiv/three-vrm)

| ルート | 体験 | 移植元 |
|---|---|---|
| `/s/[code]` | オービットビューア+**蒸着エフェクト**+パーツ検分ナビ | 検証コンソールの V3D(移植) |
| `/mirror/[code]` | **Webカメラ体連携**(体33点優先・鏡像・胴駆動) | tracking v3(移植: バインドポーズ実測レスト方向ごと) |
| `/ar/[code]` | **Quest WebXR装着体験**: パススルーAR→呼出符→蒸着 | 新規(下記シーケンス) |

### 装着アニメーション(/ar と /s 共通のヘンシン・シーケンス)

1. 呼出符入力(または URL 直) → manifest 取得 → lod選択ロード
2. **蒸着**: 粒子収束(V3D deposit移植)+部位順次フェード(足→腰→胸→腕→兜の下から上)
3. 同時にアバターが **henshin.vrma** を再生(構え→溜め→十字受け→展開→見得)
   — three-vrm の VRMAnimation で VRM に適用。suitはボーン追従で一緒に見得を切る
4. `SEAL: APPLIED` 演出 → 操作解放(mirror では続けて体連携)

## 環境準備 詳細ガイド(ユーザー側 — 全て無料枠でOK)

### Supabase(保管庫+呼出符)

**S1. プロジェクト作成** — https://supabase.com → Sign in with GitHub →
New project(Organization は個人でOK / Name 例: gavai-henshin /
Database Password は生成して保管※今回の動線では使わないが将来のDB直結用 /
Region: **Northeast Asia (Tokyo)** / Free プラン)。数分でプロビジョニング完了。

**S2. 値を2つ控える** — 左サイドバー最下部の歯車 **Project Settings**:
- **Project URL**: 「Data API」(旧UIでは「API」)ページの
  `https://<ref>.supabase.co`
- **秘密キー**: 「API Keys」ページ。新UIでは **Secret keys**(`sb_secret_…`、
  Reveal で表示)、旧UI/Legacyタブでは **service_role**(JWT)。
  **どちらの形式でもアップローダは動く**(Bearer+apikey 両ヘッダに同じ値を送る)。
  ⚠ anon / publishable(公開側)キーと取り違えないこと — 秘密キーはRLSを
  バイパスする管理者鍵。ローカルForge専用で、web/ や Vercel には絶対入れない

**S3. リポ直下 `.env` に追記**(gitignore済み。`.env.example`はコミット可):
```
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_KEY=<sb_secret_… または service_role JWT>
```
`package_suit_for_web.py --upload` が自動で読む(環境変数があればそちら優先)。

**S4. Storage バケット** — 左サイドバー **Storage** → New bucket →
Name: `suits` / **Public bucket: ON** → Save。
- 確認: バケット一覧の `suits` に「Public」バッジ
- Public の意味: URLを知っていれば誰でも**読める**(書き込みは秘密キー必須)。
  ビューアはキー無しで `/storage/v1/object/public/suits/…` を読む設計
- Storage → Settings の Upload file size limit は既定50MB(鎧は最大~20MBでOK)

**S5. recall_codes テーブル** — 左サイドバー **SQL Editor** → New query:
```sql
create table if not exists recall_codes (
  recall_code text primary key,
  blueprint_id text,
  manifest_path text,
  status text not null default 'ACTIVE',
  issued_at timestamptz not null default now()
);
```
Run → 確認: **Table Editor** に recall_codes が現れる。
「RLS disabled」警告が出たら `alter table recall_codes enable row level security;`
を追加実行してよい(書き込みは秘密キーなので影響なし。現行ビューアはこの
テーブルを読まず Storage のマニフェスト直読みなので動線も壊れない)。

**S6. 疎通確認(ローカルから)**:
```powershell
python tools/package_suit_for_web.py --assembly-dir output/blueprint-armor/fullbody --label <label> --code GAVAI-0002 --upload
```
- `UPLOADED: suits/GAVAI-0002/…` と `RECALL_CODE_ACTIVE` が出る
- Storage → suits → GAVAI-0002/ にファイルが並ぶ
- ブラウザで `https://<ref>.supabase.co/storage/v1/object/public/suits/GAVAI-0002/suit-package.json`
  を開いてJSONが返る(**これがビューアの読むURLそのもの**)
- Table Editor → recall_codes に1行入っている

### Vercel(体験面)

**V0. 前提** — `web/` をGitHubへ push しておく(node_modules/.next は
web/.gitignore 済み)。リポジトリはプライベートのままで良い(Hobbyプランで可)。

**V1. アカウント** — https://vercel.com → Continue with GitHub → Hobby(無料)。

**V2. プロジェクト作成** — Add New… → Project → Import Git Repository →
`gavai-henshin` を選択 → Configure Project 画面で:
- **Root Directory: `web`**(Edit を押して選択 — **ここが最重要**。
  リポ直下のままだと Next.js が見つからずビルド失敗)
- Framework Preset: Next.js(自動検出)。Build/Output/Install はデフォルトのまま

**V3. 環境変数** — 同じ画面の Environment Variables(作成後は
Settings → Environment Variables)に:
- Key: `NEXT_PUBLIC_SUPABASE_URL` / Value: `https://<ref>.supabase.co`
- Environment: Production / Preview / Development 全部チェック
- `NEXT_PUBLIC_` はブラウザに埋め込まれる**公開値**の印。URLは公開情報なのでOK。
  **秘密キーは絶対にここへ入れない**(入れる必要が生じる設計にもしない)
- 値を変えたら Deployments → 最新 → … → **Redeploy** で反映

**V4. デプロイ確認**:
- Deployments タブ → Status: Ready(失敗時は Build Logs)
- ドメインは Overview / Settings → Domains(`<project>.vercel.app`)
- `https://<project>.vercel.app/s/GAVAI-0002` で鎧が蒸着する
- 不調時は DevTools → Network で `supabase.co` へのリクエストのステータスを見る
  (CORSは Supabase public オブジェクトが全オリジンGET許可なので設定不要)

### ローカル開発の切替(web/.env.local)

- 無し → `/api/local` が `webdrop/` を配信(Supabase不要モード)
- `NEXT_PUBLIC_SUPABASE_URL=…` を書く → 本番と同じ Supabase 直読み。
  **書いた後は dev サーバ再起動**(Next.jsは起動時にenvを読む)。
  切替の確認は DevTools → Network の suit-package.json の取得先

**任意(後で)**: 独自ドメイン、Quest実機(M4のAR検証時)、
容量対策(無料枠 Storage ~1GB → 体数が増えたら M5 の meshopt/Draco 圧縮)

## マイルストーン

- **M1 パッケージ&アップロード**(実装済みの package_suit_for_web.py を運用に載せる):
  Supabaseプロジェクト作成 → バケット/テーブル → env設定 → 1体上げて公開URLで見える
- **M2 /s/[code] ビューア**: **実装済み(web/)** — Next.js 15 + three r164。
  呼出符入力 → manifest → GLB → 蒸着エフェクト → VRM持ち出し。env未設定時は
  /api/local が webdrop/ を配信(Supabase不要でローカル動作確認済み 2026-07-10)。
  残: Vercelデプロイ(要アカウント)、検分ナビ移植
- **M3 /mirror/[code]**: tracking v3移植。スマホ/PCカメラで体連携の実地検証
- **M4 /ar/[code]**: WebXR immersive-ar(Quest Browser, HTTPS必須=Vercel充足)。
  ヘンシン・シーケンス(蒸着+VRMA)実装
- **M5 配信最適化**: meshopt/Draco圧縮(GLB -30〜50%)、LOD自動選択、
  (テクスチャパス後)KTX2。エンジン側は既にLODチェーン/カリング済みで土台あり

## エンジン側の並行課題(2026-07-09ユーザーメモ起点)

1. **胴の分節再設計(板浮き感の根治)** — 腕・脚・頭は「着ている」が、胸・背は
   まだ「板を張っている」。方向: 胸を単一シェル+板ではなく**分節構造**へ —
   鎖骨/デコルテライン(首周りの襟甲)、胸郭、腹部を別セグメントとして構成し、
   セグメント間は重ね(瓦)で接続。首周りの襟(ネックガード)は新フィーチャ候補。
   рigid_shiftで前に浮く量も再点検(胸の奥行きをさらに体側へ)
2. **兜の座り** — VRM実機で口元が露出(ライダーマン化)→ 座りを-5%下げ+丈1.28へ
   (実装済み、実機再確認待ち)。プラットフォーム側の首ボーン差も注視
3. **足裏ソール** — closed_bottom キャップ実装済み(trimゾーン)
4. **トラッキング刷新 → v4 実装済み(2026-07-10、ラボで実地検証待ち)**
   - **Two-Bone IK**: 肩-肘-手首の位置から解析解(法余弦+ポールベクトル)。
     腕長は実ボーン長で剛体、肘ヒントは回旋にだけ効く — 深度ノイズ・遮蔽に強い
   - **One Euro Filter**: EMA置換。速度適応カットオフ(z帯域は低め)
   - **可視性ゲート**: フレーム外の腕は最後の姿勢で保持(画面外で暴れない)
   - **手首姿勢**: pose の小指+人差指の中点方向で近似
   - 残: MediaPipe HandLandmarker(21点×2の指)、BlazePose GHUM heavy 評価、
     (Quest段階)WebXR Body Tracking API
5. **ローカルでモーション確認** — ラボに「ヘンシン・モーション」ボタン実装済み
   (henshin.vrma を AnimationMixer で装着モデルに再生+蒸着同時発火)

## エンジン最適化の並行線(体験を軽くする側)

1. glTF圧縮(gltfpack/meshopt をパッケージ工程に挟む — ビルド後処理なのでエンジン無改造)
2. mirror/AR は lod1 を既定に(19.6万tris — Quest実測で調整)
3. 兜など重い部位の preview 品質を体験用途に合わせて再調整(既に90秒/体)
