# 展示PC移行・ローカルフォールバック運用マニュアル - 2026-05-05

目的: 展示PCで、ネット不調・mocopi不調でも Web Forge -> Quest 変身 -> Replay 確認の本体験を止めない。

基準:

- 必須レーン: 展示PCローカル実行。mocopiなし、外部ネットなしで成立させる。
- 推奨Quest接続: USB ADB reverse。会場Wi-Fiに依存しない。
- LAN接続: USBが使えない場合だけのfallback。
- mocopi: 体験強化レーン。接続できない日は使わない。URLから `mocopiLive` を外して通常体験に戻す。
- Webサービス/GCP: 安心レーン。ローカル展示PC pass の後に別QAで使う。

## 1. 体験モードの優先順位

### GO: ローカル展示PC基本モード

使うもの:

- 展示PC
- Quest
- USB-Cデータケーブル
- ローカルWeb/API `8010`
- Quest viewer `5173`
- ローカルGLB/VRM/Replay assets

使わなくてよいもの:

- mocopi
- GCP/Cloud Run
- 外部ネット
- 生成API
- 会場Wi-Fiの端末間通信

このモードが当日の本番baselineです。

### DEMO-ONLY: mocopi強化モード

条件:

- 基本モードが通っている。
- mocopi UDPが展示PCに届く。
- Quest debug が fresh `MOCOPI` を出す。
- 遅延とアーマー位置が許容範囲。

不調なら即座に基本モードへ戻します。mocopi不調を理由に本体験を止めません。

### FALLBACK: ネット不調モード

外部ネットが不安定な場合:

- 生成APIやクラウド保存を使わない。
- 既存ローカルアセットでWeb Forge/Questを動かす。
- QuestはUSB ADB reverseで `http://localhost:5173/...` を開く。
- 表面生成やGCP確認は「後日/展示外QA」に回す。

## 2. 移行方法

### 推奨A: GitHub整理後にcloneする

GitHubへ整理済みの状態をpushできた後は、展示PCでcloneします。

```powershell
cd C:\henshin-demo
git clone <REPOSITORY_URL> gavai-henshin
cd C:\henshin-demo\gavai-henshin
```

この方法が最終的には一番きれいです。

### 推奨B: 現時点の作業ツリーsnapshotをzipで運ぶ

現状は未追跡のdocs/assets/toolsが多いため、GitHub整理前に展示PCへ移すなら作業ツリーsnapshotを持っていきます。

開発PCでPowerShell:

```powershell
$src = "C:\dev\codex\gavai-henshin"
$stage = "C:\henshin-transfer\gavai-henshin"
$zip = "C:\henshin-transfer\gavai-henshin-local-snapshot-2026-05-05.zip"

Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $stage | Out-Null

robocopy $src $stage /E `
  /XD .git node_modules .venv venv .pytest_cache __pycache__ qa tests\.tmp .claude `
  /XF .env .tmp-* *.log

Compress-Archive -Path "$stage\*" -DestinationPath $zip -Force
```

注意:

- `.env` は運ばない。展示PCでは `.env.demo.example` から作る。
- `node_modules` や仮想環境は運ばない。展示PCで `npm install` / `pip install` する。
- `qa` は原則運ばない。展示PCでfresh QAを取り直す。
- もし特定の事前生成セッションを使う場合だけ `sessions/new-route/**` が含まれていることを確認する。

展示PCで展開:

```powershell
New-Item -ItemType Directory -Force C:\henshin-demo | Out-Null
Expand-Archive C:\path\to\gavai-henshin-local-snapshot-2026-05-05.zip C:\henshin-demo\gavai-henshin -Force
cd C:\henshin-demo\gavai-henshin
```

## 3. 展示PCの初期セットアップ

PowerShell:

```powershell
cd C:\henshin-demo\gavai-henshin

node --version
npm --version
python --version
adb version
```

不足していたら入れるもの:

- Node.js LTS
- Python 3.11以上
- Android Platform Tools または Meta Quest Developer Hub
- Git

依存インストール:

```powershell
npm install
python -m pip install -e ".[dev]"
Copy-Item .env.demo.example .env -Force
```

Python importで失敗する場合:

```powershell
$env:PYTHONPATH = "$PWD\src"
```

## 4. ローカル展示PCの確実な起動手順

まずmocopiを使わないbaselineで起動します。

```powershell
cd C:\henshin-demo\gavai-henshin
.\tools\start_exhibition_local_stack.ps1 -LaunchQuest -RequireAdbReverseSmoke
```

このコマンドが行うこと:

- Web/API server を `8010` で起動。
- Quest viewer を `5173` で起動。
- Quest USB ADB reverse を設定。
- Quest Browser を起動。
- ローカルサービス契約チェックを実行。
- smoke check を `qa\local-stack-*` に保存。

表示される重要URL:

```text
Web Forge:
http://127.0.0.1:8010/viewer/armor-forge/

Quest USB:
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1
```

## 5. Fresh codeで本番QAする

1. PCブラウザで開く:

```text
http://127.0.0.1:8010/viewer/armor-forge/
```

2. Web Forgeでスーツを成立させ、4桁コードを発行する。
3. Questに同じコードを渡す。

USBでQuestへURL投入:

```powershell
.\tools\start_quest_adb_reverse.ps1 -RecallCode <CODE> -CacheBust -LaunchBrowser
```

例:

```powershell
.\tools\start_quest_adb_reverse.ps1 -RecallCode 3601 -CacheBust -LaunchBrowser
```

手入力する場合:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1
```

Quest内で最新の4桁コードを入力します。

## 6. USB fallback / LAN fallback

### 第一選択: USB ADB reverse

会場ネットが不安定でも使えるため、当日はこれを第一選択にします。

確認:

```powershell
adb devices -l
adb reverse --list
```

OK:

```text
<device_id>    device ...
tcp:5173 tcp:5173
tcp:8010 tcp:8010
```

`unauthorized` の場合:

1. Questをかぶる。
2. "Allow USB debugging?" を許可する。
3. できれば "Always allow from this computer" を選ぶ。
4. 再確認:

```powershell
adb devices -l
```

プロンプトが出ない場合:

```powershell
adb kill-server
adb start-server
adb devices -l
```

その後、USBを抜き差しします。

### 第二選択: LAN fallback

USBが使えない場合だけ使います。PCとQuestが同一LANにいて、端末間通信が許可されている必要があります。

PCのIPv4確認:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "169.254*" -and $_.InterfaceAlias -notlike "*Loopback*" } |
  Select-Object InterfaceAlias,IPAddress
```

Quest Browserで開く:

```text
http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>
```

Windows Firewallが出たら、Node.js/Pythonのローカルネットワーク許可を入れます。

LAN fallbackが失敗しやすい条件:

- 会場Wi-Fiが端末間通信を遮断している。
- PCがゲストWi-Fi、Questが別SSIDにいる。
- Windows Firewallで `5173` / `8010` が遮断されている。

この場合はLANを追わずUSBへ戻します。

## 7. mocopiを使わない当日運用

mocopiが接続できない、遅い、座標が崩れる場合:

1. `mocopiLive=1` 入りのURLを使わない。
2. 通常URLへ戻す:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>
```

3. 変身、パーティクル、鏡、Replay確認を通常のBODY/static経路で進める。

判断:

- visitor体験では `mocopi無し = 失敗` ではない。
- mocopiは「体験向上」。本体験はWeb/Quest/Replayで成立する。
- mocopiが不安定なら、説明せず通常体験として運用する。

## 8. ネット不調時の運用

外部ネットが落ちている場合:

- 展示PCローカルサーバーはそのまま使う。
- QuestはUSB ADB reverseで使う。
- GCP/WebサービスURLは使わない。
- 表面生成やクラウド保存が必要な操作は避ける。
- ローカルにあるGLB/VRM/Replay assetsだけで進行する。

確認:

```powershell
Invoke-WebRequest http://127.0.0.1:8010/api/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:5173/viewer/quest-iw-demo/ -UseBasicParsing
```

これが通れば、外部ネットは本体験の必須条件ではありません。

## 9. 直前QAチェックリスト

展示PCで実行:

```powershell
cd C:\henshin-demo\gavai-henshin
.\tools\start_exhibition_local_stack.ps1 -LaunchQuest -RequireAdbReverseSmoke
```

PCチェック:

- [ ] `http://127.0.0.1:8010/api/health` が通る。
- [ ] `http://127.0.0.1:8010/viewer/armor-forge/` が開く。
- [ ] Web Forgeで4桁コードが発行できる。
- [ ] `http://127.0.0.1:5173/viewer/quest-iw-demo/?newRoute=1` がPCブラウザで開く。
- [ ] smoke report が `qa\local-stack-*` に出る。

Quest USBチェック:

- [ ] `adb devices -l` が `device`。
- [ ] `adb reverse --list` に `5173` と `8010` がある。
- [ ] Questで `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>` が開く。
- [ ] QuestにWeb Forgeと同じ4桁コードが表示される。
- [ ] 日本語UIが読める。
- [ ] 変身開始できる。
- [ ] パーティクル/蒸着感が見える。
- [ ] 基礎スーツ頭部が一人称の視界を邪魔しない。
- [ ] 鏡またはReplayで装着状態を確認できる。
- [ ] Replay/記録再生が操作できる。

フォールバックチェック:

- [ ] mocopiを起動しなくてもQuest体験が成立する。
- [ ] `mocopiLive=1` なしのURLで通常体験に戻せる。
- [ ] 外部ネットを使わずローカルURLだけでWeb/Questが開く。
- [ ] USBが使えない場合のLAN URLを一度だけ確認した。
- [ ] LANが遮断される場合はUSB運用に戻す、と運用判断が決まっている。

## 10. 当日トラブル判断表

| 症状 | 判断 | 対応 |
|---|---|---|
| mocopiが届かない | 本体験は継続 | mocopi無しURLへ戻す |
| mocopiが遅い/ズレる | 本体験は継続 | `mocopiLive` を外す。後で再QA |
| 会場ネットが不安定 | 本体験は継続 | USB ADB reverseへ固定 |
| QuestがLAN URLを開けない | LAN追跡しない | USB ADB reverseへ戻す |
| USBがunauthorized | 体験開始前に解決 | QuestでUSB debugging許可 |
| `5173`が起動しない | Quest体験不可 | 競合プロセスを止め、同じportで再起動 |
| Web Forgeでコード発行不可 | visitor flow停止 | API health/log確認。必要なら固定コード/既存sessionへ退避 |
| 表面生成が動かない | 本体験は継続 | ローカル既存材質で進める |

## 11. Webサービス化/GCPへ進む条件

GCP/Webサービス化は、次を満たした後に安心レーンとして進めます。

- 展示PCローカル `local-pass` が取れている。
- USB Questの本番QAが通っている。
- mocopi無しでも本体験が成立している。
- ネット無しでも最低限の体験が成立している。
- fresh code -> Quest recall -> transform -> Replay の証跡がある。

GCPはローカルbaselineの代替ではなく、展示会でネットやPC構成が読めない時の追加安全策として扱います。
