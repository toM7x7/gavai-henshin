# Web版 / Quest USB確認手順

更新日: 2026-05-01

この手順は、PCのWeb Forgeで生成とプレビューを確認し、その4桁コードをQuest BrowserのVR体験で呼び出すためのものです。

## 1. PC Webを起動する

リポジトリ直下で dashboard/API/static server を起動します。

```powershell
cd C:\dev\codex\gavai-henshin
npm run dev
```

PCブラウザで開くURL:

```text
http://localhost:8010/viewer/armor-forge/
```

確認すること:

- パーツvariantの先頭が `自動選定` になっている。
- 入力後に生成すると、LLM/SakuraAI選定またはfallback選定のvariantがUIへ反映される。
- 手動でvariantを変えると、再生成前でもWebプレビューのGLBが切り替わる。
- 4桁コードが表示される。

## 2. Quest runtimeを起動する

Quest側のVRページは Vite dev server の `5173` で動きます。dashboardの `8010` とは別に起動します。

別ターミナルで:

```powershell
cd C:\dev\codex\gavai-henshin
npm run dev:quest
```

`5173` が埋まっていると `5174` などへ逃げる場合があります。Quest USB確認では原則 `5173` を使いたいので、別プロセスが占有していないか確認してください。

## 3. QuestをUSB接続してADB reverseを張る

QuestをUSB接続し、ヘッドセット内でUSBデバッグ許可を承認します。

確認:

```powershell
adb devices
```

`device` と表示されればOKです。

ADB reverse:

```powershell
npm run dev:quest:adb
```

内部では次を張ります。

```powershell
adb reverse tcp:5173 tcp:5173
adb reverse tcp:8010 tcp:8010
```

## 4. Quest Browserで開く

Quest Browserで開くURL:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1
```

Web Forgeで発行された4桁コードを、Quest内のコード入力UIから呼び出します。

確認すること:

- 4桁コードでWeb側と同じ装備が呼び出される。
- variant自動選定の結果がQuest側の装備にも反映される。
- Web側で手動variantを変えた場合、新しい4桁コードを発行してからQuestで呼び直す。

## 5. Quest実機確認観点

呼び出し前の状態:

- Quest Browserでページを開いただけの状態では、鎧が出ていないことを確認する。
- `mockTrigger=1` は入力導線や発火確認用であり、4桁コード呼び出し成功の代替判定にしない。
- 以前の確認で残った古いcodeを使っていないか確認する。Web Forgeで今回発行した4桁コードだけを使う。

4桁コード呼び出し後の状態:

- Web Forgeで表示されているvariantと同じvariantが、Quest側の装備にも反映されていることを確認する。
- helmet/chest/shoulder/shin/bootなど、Web Forgeで生成または選定されたパーツ構成とQuest側の表示が一致していることを確認する。
- Web Forgeでvariantやパーツを変更した場合は、古い4桁コードを再利用せず、新しく発行された4桁コードでQuest側を呼び直す。
- 見た目が合っているだけでなく、コード入力後の状態表示やログが今回のcodeを参照していることを確認する。

誤認防止:

- 古いcodeで成功した表示を、今回のWeb Forge結果として扱わない。
- `mockTrigger=1` で表示されたデモ状態を、4桁コード経由の実機確認完了として扱わない。
- Quest Browserのタブ復元やキャッシュで前回の鎧が残る場合があるため、呼び出し前に鎧がない初期状態を一度確認する。

失敗時の切り分け:

- Quest Browserのタブを閉じて開き直し、同じ4桁コードで再実行する。
- Web Forge側を `Ctrl+F5` でハードリロードし、必要なら新しい4桁コードを発行し直す。
- Quest側の入力UIに `RESET` がある場合は実行し、鎧が消えることを確認してから再度4桁コードを入力する。
- 状態が残り続ける場合は、Quest Browserのサイトデータやキャッシュをclearしてから開き直す。
- `npm run dev`、`npm run dev:quest`、`npm run dev:quest:adb` を順に再実行し、`adb reverse` と両サーバーの接続を張り直す。

## 6. よくある詰まり

### `adb` が見つからない

```powershell
adb version
```

が失敗する場合、Android Platform ToolsまたはMeta Quest Developer HubのADBにPATHが通っていません。インストール後に新しいPowerShellを開き直してください。

### Questで `localhost:5173` が開けない

- `npm run dev:quest` が起動中か確認する。
- `npm run dev:quest:adb` を実行し直す。
- `adb devices` が `device` になっているか確認する。
- Quest内でUSBデバッグ許可が出ていないか確認する。

### Questで404になる

`localhost:8010` はWeb Forge/dashboard用です。Quest Browserでは基本的に `localhost:5173/viewer/quest-iw-demo/` を開きます。

### 古い画面が残る

- PCブラウザは `Ctrl+F5` でハードリロードする。
- Quest Browserはタブを閉じて開き直す。
- `npm run dev` と `npm run dev:quest` を両方再起動する。
