# 鍛造工場 (henshin-forge) — Cloud Run デプロイ手順

言葉 → **設計局AI(Gemini)による設計図解釈** → Blender鍛造 → Supabase格納 →
呼出符発行 を行うジョブAPI。Vercel の `/forge` → `/api/forge`(プロキシ)→ ここ。

**言葉の解釈はコンセプトの肝であり、Gemini解釈(ルートB)が必須本線**(2026-07-11方針)。
`GEMINI_API_KEY` なしでは工場は起動しない。Gemini側の一時障害時のみ規範解釈
(ルートA)へ自動フォールバックし、その事実は route として記録・表示される。

## 環境変数一覧(Cloud Run に設定するもの)

| 変数 | 必須 | 値の出どころ |
|---|---|---|
| `SUPABASE_URL` | ✅ | Supabaseプロジェクト設定(リポ直下 `.env` と同じ) |
| `SUPABASE_SERVICE_KEY` | ✅ | 同上(service_role / sb_secret) |
| `GEMINI_API_KEY` | ✅ | https://aistudio.google.com/apikey (`.env` と同じでOK) |
| `FORGE_TOKEN` | ✅ | 自分で生成する合言葉(0c参照。Vercelにも同じ値) |
| `GEMINI_TEXT_MODEL` | 任意 | 解釈モデルの差し替えノブ。未設定なら `gemini-2.5-flash`。上位モデル(例: gemini-3系flash/pro)へ自由に変更可 — 設計図の方言修復レイヤが吸収する |

**Vercel側に置くのは `FORGE_URL` / `FORGE_TOKEN` / `NEXT_PUBLIC_SUPABASE_URL` の3つだけ。**
GeminiキーとSupabase秘密キーは工場(Cloud Run)にしか置かない。

## 0. 前提

- GCPアカウント + 課金有効化(無料枠内でもカード登録必須)
- gcloud CLI(未導入なら https://cloud.google.com/sdk/docs/install)
- リージョンは `asia-northeast1`(東京)で統一

### 0a. gcloud CLI の導入(Windows・未導入の場合)

1. https://cloud.google.com/sdk/docs/install から `GoogleCloudSDKInstaller.exe` を実行
   (または `winget install Google.CloudSDK`)
2. インストール後、**新しい PowerShell を開いて** `gcloud --version` が通ることを確認

### 0b. PROJECT_ID の確認/作成

- https://console.cloud.google.com → 画面上部のプロジェクト選択 → 「ID」列が PROJECT_ID
  (表示名ではなく `xxxx-123456` のような英数字ID)
- 新規なら「新しいプロジェクト」→ 名前 gavai-henshin → 作成後にIDを控える
- 「お支払い」でプロジェクトに請求先アカウントがリンクされていること
  (リンクが無いと Cloud Build/Run が有効化できない)

### 0c. FORGE_TOKEN の生成(合言葉。自分で決めるランダム文字列)

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
出力された文字列を控える(Cloud Run と Vercel の両方に同じ値を設定する)。

## 1. 初回セットアップ(1回だけ)

```powershell
gcloud auth login
gcloud config set project <PROJECT_ID>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
gcloud artifacts repositories create forge --repository-format=docker --location=asia-northeast1
```

## 2. イメージのビルド(リポジトリルートから)

```powershell
gcloud builds submit --config cloud/forge/cloudbuild.yaml `
  --substitutions=_IMAGE=asia-northeast1-docker.pkg.dev/<PROJECT_ID>/forge/henshin-forge:latest
```

Blender本体(~350MB)のダウンロードとVRMアドオン導入が走るので初回は10分前後。
`extension list | grep -i vrm` の行が通ればVRMエクスポート可能なイメージ。

## 3. デプロイ

```powershell
gcloud run deploy henshin-forge `
  --image asia-northeast1-docker.pkg.dev/<PROJECT_ID>/forge/henshin-forge:latest `
  --region asia-northeast1 --memory 4Gi --cpu 4 --timeout 900 `
  --max-instances 1 --min-instances 0 --no-cpu-throttling `
  --allow-unauthenticated `
  --set-env-vars "SUPABASE_URL=<SupabaseのURL>,FORGE_TOKEN=<0cの文字列>,SUPABASE_SERVICE_KEY=<.envのservice_roleキー>,GEMINI_API_KEY=<.envのGeminiキー>"
```

⚠ `--set-env-vars` は**1回のフラグに全部まとめる**(2回書くと後の指定が前を上書きする)。
成功すると最後に `Service URL: https://henshin-forge-....run.app` が出る — これを控える。

解釈モデルを差し替える場合(いつでも・再ビルド不要):

```powershell
gcloud run services update henshin-forge --region asia-northeast1 `
  --update-env-vars "GEMINI_TEXT_MODEL=<モデルID>"
```
使えるモデルIDは https://ai.google.dev/gemini-api/docs/models で確認
(flash系=数秒・1体1円未満 / pro系=解釈が濃くなるが数十秒+数円)。

重要なフラグの意味:
- `--no-cpu-throttling`: 応答を返した後もビルドスレッドがCPUを使い続けられる(ジョブ方式の要)
- `--max-instances 1`: ジョブ状態はメモリ保持なので1インスタンス固定
- `--allow-unauthenticated` + アプリ層の `FORGE_TOKEN` 検証: VercelサーバだけがTOKENを知る
- 秘密鍵をコマンド履歴に残したくない場合は Secret Manager 連携
  (`--set-secrets SUPABASE_SERVICE_KEY=...`)に後で移行

## 4. 疎通確認

```powershell
# ヘルスチェック
curl https://henshin-forge-xxxx.a.run.app/healthz
# 鍛造(2〜4分)
curl -X POST https://henshin-forge-xxxx.a.run.app/forge `
  -H "Content-Type: application/json" -H "X-Forge-Token: <TOKEN>" `
  -d '{"text": "蒼雷を纏う疾風の剣士"}'
# → {"ok": true, "job_id": "..."} を控えて
curl "https://henshin-forge-xxxx.a.run.app/job?id=<job_id>"
# → status: queued → forging → uploading → done { code: GAVAI-XXXX }
```

## 5. Vercel側の接続

Vercel → Settings → Environment Variables に(**NEXT_PUBLIC_を付けない** — サーバ専用):
- `FORGE_URL` = `https://henshin-forge-xxxx.a.run.app`
- `FORGE_TOKEN` = デプロイ時と同じ値

→ Redeploy 後、`/forge` ページから言葉入力→鍛造→自動で `/s/<呼出符>` へ。

## コストの目安

- Cloud Run無料枠: 月180,000 vCPU秒 / 360,000 GiB秒。1体 ≈ 4vCPU×3分 ≈ 720 vCPU秒
  → **月200体程度まで実質0円**、以降1体あたり数円
- コールドスタート(数十秒)は「鍛造炉の点火」演出として /forge ページが吸収する

## 制約と今後

- レンダビュー(PNG)とVRMサムネイルはGPU無し環境でEEVEEが立たない場合スキップ
  (`--render-views soft`)。スーツ本体・GLB・VRMは影響なし
- **Gemini解釈は必須本線**: /forge の全リクエストが設計局AIを通る。Gemini障害時のみ
  規範解釈へ自動フォールバックし、完了画面に「規範解釈で鍛造されました」と明示される。
  キーの置き場所は**Cloud Runのみ** — Vercel には置かない(Vercelは表示とプロキシだけ)
- ジョブ状態はメモリのみ(再起動で消える)。完成品はSupabaseにあるので実害は薄い
