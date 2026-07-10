# 鍛造工場 (henshin-forge) — Cloud Run デプロイ手順

言葉 → 設計図 → Blender鍛造 → Supabase格納 → 呼出符発行 を行うジョブAPI。
Vercel の `/forge` ページ → `/api/forge`(プロキシ)→ ここ、という動線。

## 0. 前提

- GCPアカウント + 課金有効化(無料枠内でもカード登録必須)
- gcloud CLI(未導入なら https://cloud.google.com/sdk/docs/install)
- リージョンは `asia-northeast1`(東京)で統一

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
  --set-env-vars "SUPABASE_URL=https://<ref>.supabase.co,FORGE_TOKEN=<長いランダム文字列>" `
  --set-env-vars "SUPABASE_SERVICE_KEY=<service_roleキー>"
```

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
- ルートB(Gemini解釈)は未接続。`GEMINI_API_KEY` を渡して forge_server を
  compile_blueprint_llm に切り替えれば有効化できる(コスト方針が決まったら)
- ジョブ状態はメモリのみ(再起動で消える)。完成品はSupabaseにあるので実害は薄い
