# 蒸着庫 — GAVAI SUIT GALLERY(XRift技術検証ワールド)

Phase 1(xrift-gallery-plan-2026-07.md)の検証実装。
目的: **XRiftワールドから外部URL(Supabase鍛造ギャラリー)を実行時fetchできるかの確定**。

- 成立(A案) → 鍛造するだけでこのワールドに新スーツが並ぶ。XRift再アップロード不要
- 不成立 → B案(鍛造時に@xrift/sdkでワールド再アップロード)へ切替

## 仕組み

入場すると中央の計測板が接続結果を表示する:

1. `suits/gallery.json`(公開バケット)をfetch → 登録数を表示
2. 最新3体の `suit-package.json` → VRM を実行時ロードして展示台に立たせる
3. 各体の成否も計測板に追記(`✓ GAVAI-XXXXX VRM表示成功` / `✗ ...`)

ワールドはModule Federationのremote(`World`コンポーネントをexpose)。
three/react等はXRiftホスト提供、`@pixiv/three-vrm` だけワールド側にバンドルされる。

## ローカル確認

```bash
cd xrift/gallery-world
npm install
npm run dev   # http://localhost:5173 (DevEnvironmentハーネス)
```

## アップロード(主催アカウントで一度だけ)

```bash
npm install -g @xrift/cli   # 未導入なら
xrift login                  # ブラウザ認証(トークンは ~/.xrift/config.json)
cd xrift/gallery-world
xrift upload world           # ビルド→検証→アップロードまで一括
```

アップロード後、XRiftでワールドに入り**計測板の文言を確認**するのがPhase 1の完了条件。
`✗ 外部fetch失敗` が出た場合はその文言(HTTPコード等)を記録して報告。

## 注意

- Supabase URLは公開バケット(秘密情報ではない)。書き込み系の鍵は一切含まない
- スーツVRMは10MB級 — 展示は最新3体に絞っている(増やす時はLOD/間引き検討)
- `xrift upload` 前の再ビルドはCLIが自動実行(`buildCommand`)
