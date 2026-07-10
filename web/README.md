# gavai-henshin web — 体験面 (Vercel)

呼出符で鎧を召喚するビューア。Next.js App Router + three.js。

## ローカル起動(Supabase不要)

```powershell
cd web
npm install
npm run dev   # http://localhost:3000
```

env 未設定のときは `/api/local` がリポジトリ隣の `webdrop/<code>/` を配信する。
鎧の登録はローカルForgeから:

```powershell
python tools/package_suit_for_web.py --assembly-dir output/blueprint-armor/fullbody --label <label> --code GAVAI-0001
```

→ http://localhost:3000/s/GAVAI-0001

## 本番(Supabase + Vercel)

1. `.env.local` に `NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co`
   (書き込みキーは**入れない** — ビューアは public バケットを読むだけ)
2. Vercel にリポジトリを接続 → Root Directory を `web` に →
   Environment Variables に同じ `NEXT_PUBLIC_SUPABASE_URL` を設定 → Deploy
3. アップロードはローカルから `package_suit_for_web.py --upload`
   (`SUPABASE_URL` / `SUPABASE_SERVICE_KEY` はリポジトリ直下の `.env`)

## ルート

| ルート | 状態 | 内容 |
|---|---|---|
| `/` | 済 | 呼出符入力 |
| `/s/[code]` | 済 (M2) | オービットビューア + 蒸着 + VRM持ち出し |
| `/mirror/[code]` | M3 | Webカメラ体連携 (tracking v4 移植) |
| `/ar/[code]` | M4 | Quest WebXR 装着体験 |
