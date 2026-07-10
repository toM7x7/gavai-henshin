# Quest Workshop Armor Stand Interaction Spec - 2026-05-04

## 0. 目的

Quest内に「Tony Starkのワークショップで、自分のスーツを台座ごと手で観察する」体験を追加する。Web Forgeで成立したスーツを、変身前後の演出だけでなく、展示物として触れる・回す・分解する・部品を見る・戻す、という短い発見体験にする。

この仕様は、Quest runtimeのワークショップ/armor stand interactionだけを対象にする。Web Forge、SuitManifest生成、GLB品質改善、音声認識モデル、Replay保存形式は対象外。ただし、既存のQuest変身導線と音声変身コマンドを壊さないための入力調停はP0対象に含める。

## 1. 体験の核

訪問者は、変身コマンドを唱える前に、目の前のアーマースタンドへ手を伸ばす。右グリップで鎧全体を一体オブジェクトとして掴み、手を動かすとスーツ全体が自由に回る。両グリップで持つと模型のように大きさを変えられる。右トリガーを押すとパーツが少し外側へ展開し、もう一度押すと全身へ戻る。

重要なのは「自由に触れるが、展示の本筋を迷子にしない」こと。ワークショップは観察モードであり、鎧立て中は音声変身を開始しない。音声変身は、鎧立てを出て`変身へ`進んだ時だけ有効にする。特に「鎧立てから戻れない」はP0 UX不具合として扱い、右手だけで鏡/変身導線へ戻れる逃げ道を常に出す。

### 1.1 最新フィードバック反映

今回の追加方針は次の3点に集約する。

| フィードバック | 仕様上の扱い | P0判定 |
| --- | --- | --- |
| 鎧立てから戻れない | 右トリガー長押し、または右手側の`戻る`で鎧立てを閉じる。左手メニュー探索を必須にしない。 | 戻れなければP0 fail。 |
| 単一リグで掴みたい | 鎧全体を`ArmorStandRigRoot`のような単一rootとして掴む。各GLB/パーツはその子として動く。 | 右グリップで動く対象は常に鎧全体。 |
| 人体理解で位置決めしたい | 鎧立てもmirrorも、同じ人型anchor frameから部位位置を決める。見た目の補正だけで人体を作らない。 | chest/back/limb/bootが人体部位として説明できる。 |

スタッフ向けの短い説明は「鎧はひとつの人型リグとしてつかみます。右グリップで全体を回し、右トリガーで開閉し、長押しで戻ります。」とする。

## 2. 成功条件

| 項目 | 必須条件 |
| --- | --- |
| 自由回転 | 右グリップ長押し + 手の移動で、スタンド全体を連続的に回転できる。 |
| 両手拡縮 | 両グリップ長押しの手幅変化に応じて、スタンド全体を中心基準で拡大/縮小できる。 |
| パーツ展開 | 右トリガーで主要パーツが外向きに展開し、元の装着関係が読める距離で止まる。 |
| 復帰/組立 | 右トリガーをもう一度押す、またはresetで全体を初期装着状態へ戻せる。 |
| 鎧立て終了 | 右手中心の戻る操作で、鎧立てからmirror/replayまたは`変身へ`導線へ戻れる。 |
| 音声競合なし | スタンドを掴む、回す、分解する、検分する操作では音声変身が開始しない。 |
| 展示運用 | スタッフが30秒以内に説明でき、失敗時にリセットできる。 |

展示判定の強いルール:

- 鎧立て表示は「スーツを観察できる」証拠であり、「変身が成功した」証拠ではない。
- `armorStandPreview=true`, `playing=false`, `progress=0` の写真は、必ず鎧立て/observer待機として扱う。
- 変身成功の展示証拠は、mirror/replayまたはtransformで `playing=true` または `progress>0` を確認してから採用する。

## 3. モードと状態

Quest runtimeは少なくとも次の状態を持つ。

| 状態 | 説明 | 音声変身 |
| --- | --- | --- |
| `armor_stand_observer_idle` | スーツがスタンド上に表示され、観察待ち。 | 無効。明示的な変身開始UIだけ有効。 |
| `armor_stand_grabbed_one_hand` | 片手でスタンドまたはスーツのgrab handleを保持。 | 無効。 |
| `armor_stand_grabbed_two_hand` | 両手でgrab handleを保持。 | 無効。 |
| `armor_stand_exploded` | 全体分解表示。 | 無効。 |
| `armor_part_inspecting` | 1パーツを選択/検分中。 | 無効。 |
| `armor_stand_returning` | 右手操作で鎧立てを閉じ、mirror/replayまたは変身導線へ戻る遷移中。 | 無効。 |
| `transform_arming` | 変身開始を明示し、音声待機している状態。 | 有効。 |
| `transform_active` | 変身演出中。 | 追加開始は不可。 |
| `archive_replay_mirror_active` | Replay/mirror確認中。 | 無効。 |

入力調停の原則:

- 観察系状態では、trigger/grip/pinchはワークショップ操作に割り当てる。
- 音声認識は`transform_arming`の時だけ録音/判定する。
- `voiceState=complete`のような過去の音声状態は、現在のUX状態の根拠にしない。`uxState`を常に優先する。
- `mockTrigger=1&mic=0`のdebug/recovery URLでは、音声の合否を評価しない。
- 観察中に訪問者が「変身」と発声しても、UIは「変身ボタンを押してから唱える」状態を示すだけで、変身を開始しない。

## 4. 入力設計

### 4.0 Quest操作表

展示スタッフは次の割当だけを来場者へ説明する。ここにない操作はdebug/開発者向けとして扱う。

| 操作 | 鎧立て中の挙動 | 注意 |
| --- | --- | --- |
| 右グリップ長押し + 手を左右/上下へ動かす | スーツ全体を自由回転 | 角度固定のステップ回転ではない。音声変身も開始しない。 |
| 両グリップ長押し + 手幅を広げる/狭める | スーツ全体を拡大/縮小 | 大きくしすぎないよう`0.65`から`1.35`へクランプ。 |
| 右トリガー | パーツ展開/全身へ戻す | 鎧立て中はvoice shortcutではない。押すたびに展開と戻しを切り替える。 |
| 右トリガー長押し、または右手側の`戻る` | 鎧立てを閉じてmirror/replayまたは`変身へ`へ戻る | P0必須。左手メニューを探さなくても戻れること。 |
| 左手メニューの`鎧立て`/`収納`/`鏡へ` | 鎧立て表示へ入る、またはmirror/replay導線へ戻る | 変身証拠を撮る前にmirrorへ戻す。 |
| `Reset Stand`または鎧立て再表示 | 回転、scale、展開状態を初期化 | 迷ったらまずこれ。スーツデータは再生成しない。 |
| `変身へ` | 鎧立てを出て音声待機へ進む | real mic URLでだけ音声合否を評価する。 |

### 4.1 Grab target

スーツ本体の各メッシュを直接grab判定に使わず、見えない大きめのgrab handleを使う。掴む対象は常に鎧全体のrootであり、パーツ単体ではない。

実装上の概念名は`ArmorStandRigRoot`とする。これは来場者に見せる名前ではなく、開発/QAで「どこを掴んでいるか」を揃えるための呼称。

- `ArmorStandRigRoot`は鎧全体の移動、回転、scale、戻る状態を持つ。
- 各GLBパーツはroot配下の子であり、右グリップ操作で独立回転しない。
- パーツ展開はroot配下の局所offsetとして扱う。展開中でもrootを掴めば全体が回る。
- reset/returnはroot状態を初期化し、パーツの局所展開offsetも戻す。

| Handle | 範囲 | 目的 |
| --- | --- | --- |
| `stand_core_handle` | 胸から腰を覆う縦長カプセル | 鎧全体を一体オブジェクトとして掴む主ターゲット。 |
| `left_scale_handle` | スタンド左側、肩から腰の外側 | 両手スケール開始。 |
| `right_scale_handle` | スタンド右側、肩から腰の外側 | 両手スケール開始。 |
| `part_handles[*]` | 各主要パーツの外接bboxを少し拡張 | hover/inspect用。掴み回転には使わない。 |

Handleはデバッグ表示時のみ薄いワイヤーで確認できる。通常展示では見せない。

### 4.2 片手自由回転

操作:

1. 右グリップを押して`stand_core_handle`を掴む。これは鎧全体のrootを掴む操作であり、胸/腕/脚などのパーツ単体を掴む操作ではない。将来のhand trackingではpinchを同じ意味に割り当てる。
2. 掴んだ瞬間のスタンド姿勢、手のpose、pivotを保存する。
3. 右手の移動量をスタンド回転へ反映する。
4. 離すとその角度で停止する。慣性回転はP1以降。P0では停止優先。

制約:

- pivotはスーツの腰/胸の中間ではなく、スタンド全体bboxの中心とする。ヘルメットや足先が大きいスーツでも回転が暴れにくい。
- pitch/rollは自由回転に見せつつ、P0では各軸最大45度にソフトクランプする。完全に上下逆さになると展示スタッフの説明と復帰が難しくなるため。
- yawは無制限。訪問者が背面/側面を自然に見られることを優先する。
- 回転対象は常に鎧全体。パーツ単体を独立回転させない。
- 鎧立て中の右グリップ/右トリガーはワークショップ操作専用にし、音声変身へ渡さない。

### 4.3 両手スケール

操作:

1. 右グリップ中に左グリップも押す。
2. 両手間距離の初期値と現在値の比率からscaleを計算する。
3. scaleはスタンドpivot中心で全パーツ、ラベル、handleに同じ係数をかける。
4. 片手を離すと片手回転へ戻る。両手を離すと停止する。

推奨範囲:

| 値 | 意味 |
| --- | --- |
| `minScale=0.65` | 卓上模型のように全体を見渡せる下限。 |
| `defaultScale=1.0` | 変身プレビューと同じ読み。 |
| `maxScale=1.35` | 細部を見やすい上限。来場者の視界を塞ぎすぎない。 |

アクセシビリティ設定で`one_hand_mode=true`の場合、左/右のUIボタンまたは親指スティック上下で同じscale範囲を操作できる。

### 4.4 分解表示

分解は「爆発」ではなく「整備台の展開」。Tony Stark的な派手さは光/音/軌跡で出し、パーツ位置は読める範囲に留める。

操作:

- 初期状態または回転/スケール後に右トリガーで「展開」する。
- もう一度右トリガーを押すと初期装着位置へ戻る。
- 展開中も右グリップ自由回転と両グリップ拡縮は可能。
- 展開中でも、右グリップで回るのは鎧全体。個別パーツだけを回さない。
- 鎧立て中の右トリガーは展開/戻す専用で、音声変身には使わない。

展開方向:

| 部位 | 方向 | 備考 |
| --- | --- | --- |
| helmet | 上 + 前少し | 顔/バイザーが見えるようにする。 |
| chest | 前 | 胸コアと装甲面を見せる。 |
| back | 後 | 回転すればバックパック構造が見える。 |
| shoulders | 左右外 + 上少し | 腕と干渉しない。 |
| forearms/hands | 左右外 + 前少し | 手甲を選びやすくする。 |
| waist | 下 + 前少し | 胸/脚の中間で埋もれない。 |
| thighs/shins/boots | 左右外 + 下少し | 脚ラインを読める距離にする。 |

距離:

- P0/P1共通で、各パーツbbox対角の`0.6x`から`1.2x`を目安にする。
- 小物は最小`0.12m`、大物は最大`0.45m`。
- 展開後も人型の記憶が残ること。全部が球状に散らばると「組み上がる快感」が落ちる。

### 4.5 パーツ検分

スタッフ説明上の扱い:

- P0/P1の来場者説明では「右トリガーでパーツを開いて、見たい角度へ回して観察できます」と伝える。
- 個別パーツ選択や詳細カードは追加演出であり、展示スタッフの基本説明には含めない。
- パーツ単体を回す体験ではない。来場者には「鎧全体を回して、開いたパーツを見る」と説明する。

将来の個別パーツ検分を追加する場合:

1. 分解表示または通常表示で、ray hoverまたはdirect touchでパーツを狙う。
2. hover中は輪郭線/軽い発光で対象を示す。
3. 右トリガーとは別の明示的な選択操作で`armor_part_inspecting`へ入る。
4. 対象パーツは少し手前へ寄り、他パーツは透明度を下げる。
5. 「戻す」で分解表示へ戻る。「組み立て」で全体を装着状態へ戻す。

表示情報:

| 表示 | 内容 |
| --- | --- |
| 部品名 | 例: `ヘルメット`, `胸部装甲`, `右前腕`, `ブーツ`。 |
| スロット | manifest上のslot/module名。スタッフ向けdebugでは英語IDも併記。 |
| 状態 | `loaded`, `fallback`, `quality_warning`, `ready`など。 |
| 見どころ | 1行。例: `胸部コアと肩ラインを確認`。 |
| 操作 | `戻す`, `組み立て`, `変身へ`。 |

禁止:

- 検分パネルに生JSONを出さない。
- 来場者向けに`runtime-render-placement.v1`などの内部IDを主表示しない。
- パーツを掴んでワールド遠方へ投げられるようにしない。検分は近接移動まで。

### 4.6 鎧立てから戻る

「鎧立てから戻れない」は、見た目の問題ではなくP0 UX不具合として扱う。来場者もスタッフも、左手メニューを探さず右手中心で戻れる必要がある。

P0の戻る導線:

- 右トリガー短押し: パーツ展開/全身へ戻す。
- 右トリガー長押し、または右手側の`戻る`: 鎧立てを閉じてmirror/replayまたは`変身へ`へ戻る。
- 戻る操作中は音声変身を開始しない。鎧立てを閉じた後、`変身へ`で初めて音声待機へ入る。
- 戻った直後は、鎧全体の回転、scale、展開状態を初期化する。
- 戻る操作が失敗した場合は、UIに`鎧立てを閉じられませんでした`を出し、`Reset Stand`を右手側にも提示する。

スタッフ向けの言い方:

```text
開いたパーツを見る時は右トリガーを短く押します。
鎧立てを終わる時は右トリガーを長押し、または右手の戻るを押します。
鎧立て中に声を出しても変身は始まりません。
```

### 4.7 人体理解ベースの位置決め

鎧立ての配置は「パーツを空間に並べる」ではなく、「人型を理解した単一リグに装甲を載せる」として扱う。

P0/P1の考え方:

- stand、mirror、replayは別々の座標hackを持たず、同じ中立人型frameから部位位置を得る。
- `helmet`はhead/neck、`chest`はsternum、`back`はspine/back、`waist`はpelvis、腕脚はbone segmentに結びつける。
- `runtime-render-placement.v1`は人体anchor後のasset-local補正であり、人体そのものを作るための主情報にしない。
- 右グリップで掴むroot pivotは人体frameの中心、原則はpelvisからchestの中間に置く。単一パーツのbbox中心へ寄せない。
- 写真評価で位置がおかしい場合、先に`anchor source`, `body height`, `chest/pelvis/limb anchors`を確認し、個別GLB offsetを直接いじらない。

## 5. 音声変身コマンドとの競合回避

音声変身は展示の強い山場だが、ワークショップ操作と同じtrigger/gripに載ると誤爆する。入力を次のように分離する。

| 状況 | controller | microphone | 期待挙動 |
| --- | --- | --- | --- |
| 鎧立て観察待ち | 右グリップ=自由回転、両グリップ=拡縮、右トリガー=展開/戻す | 監視しない | スタンド操作だけ。 |
| 右グリップ回転中 | 手の移動=自由回転 | 監視しない | 音声開始不可。 |
| 両グリップ拡縮中 | 手幅=拡大/縮小 | 監視しない | 音声開始不可。 |
| パーツ展開中 | 右トリガー=全身へ戻す | 監視しない | 音声開始不可。 |
| 鎧立て終了中 | 右トリガー長押し/右手`戻る`=鎧立てを閉じる | 監視しない | mirror/replayまたは`変身へ`へ戻る。 |
| 変身へボタン押下後 | confirm/hold | 監視する | `transform_arming`へ入り、音声UIを出す。 |
| 変身中 | 無効またはcancel長押し | 監視しない | 二重開始を防止。 |

Debug mockとreal micの扱い:

| URL/状態 | マイク | 右手デバイス色 | 展示判断 |
| --- | --- | --- | --- |
| `mockTrigger=1&mic=0` | 実マイク無効 | `green -> cyan` など中間を省略可 | rendering、鎧立て、mirror/replay確認用。音声認識成功として採用しない。 |
| `mockTrigger=1`なし、`mic=0`なし | 実マイク有効化を期待 | `green -> orange -> purple -> cyan`、失敗は`red` | real voice検証用。許可promptとtelemetryを記録する。 |

UI文言:

- 観察中: `スーツをつかんで回す`
- 分解可能: `展開`
- 分解中: `組み立て`
- 検分中: `戻す`
- 変身開始前: `変身へ`
- 音声待機中: `合図を唱えてください`

音声競合のP0要件:

- `uxState`が`armor_stand_*`の間は、録音開始API/処理へ入らない。
- 既存の右triggerショートカットがある場合、armor stand active時は展開/戻すなど鎧立て操作へ優先割当する。
- 音声が誤って`complete`になっても、`transform_arming`でなければ変身演出へ遷移しない。
- 現行snapshotで `armorStand.active=true` かつ `armorStand.rightTriggerMode=explode_toggle` を確認できる。

## 6. アクセシビリティ

| 課題 | 要件 |
| --- | --- |
| 座位利用 | スタンド高さを`seated` presetへ下げる。UIは胸の高さに追従する。 |
| 片手利用 | one-hand modeで、片手grab + スティック上下/ボタンでscale、ボタンで展開/組立。 |
| 握力/長押し困難 | toggle grabを用意する。押し続けなくても再押下で解除。 |
| 回転酔い | rotation sensitivityを`low/default/high`から選択。P0 defaultは低め。 |
| 手ぶれ | grab poseに軽いsmoothingを入れる。細部検分時はさらに強める。 |
| 色覚差 | hover/selected状態は色だけでなく輪郭線/サイズ/ラベルで示す。 |
| 聴覚差 | 音声待機/成功/失敗は字幕、色、振動で示す。音だけに依存しない。 |
| 発話困難/騒音 | スタッフ用に非音声の「変身開始」fallbackを残す。ただし通常展示では音声導線を主役にする。 |
| 子ども/身長差 | スタンド距離と高さをスタッフが即時リセットできる。 |

## 7. 展示スタッフ運用

### 7.1 来場者への30秒説明

1. `右グリップでつかむと、スーツを好きな角度に回せます。`
2. `両方のグリップで持つと、大きさを変えられます。`
3. `右トリガーでパーツが整備台みたいに開きます。`
4. `終わる時は右トリガー長押し、または右手の戻るで戻れます。`
5. `鎧立て中は声では変身しません。変身は戻ってから合図を唱えます。`

### 7.2 スタッフが見ておく状態

| 見るもの | OK | NG時の対応 |
| --- | --- | --- |
| Quest URL | fresh code入り、debug/recovery URLかreal voice URLか把握済み | 古いcodeならWeb Forgeで新規発行して再投入。 |
| `uxState` | 観察なら`armor_stand_*`、mirrorなら`archive_replay_mirror_active` | 鎧立て写真を変身成功として採用しない。 |
| 音声 | real voice評価時は`mockTrigger=1&mic=0`なし | debug URLなら音声評価として採用しない。 |
| パーツ数 | major partsが欠けていない | fallback/asset failureを記録し、最後の安定packageへ戻す。 |
| リセット | `組み立て`またはstaff resetで初期姿勢へ戻る | 同じ失敗が2回続いたら設定変更せず記録して切替。 |

### 7.3 リセット手順

最短復旧:

1. 右グリップ/左グリップを離す。
2. パーツが展開中なら右トリガーを1回押して全身へ戻す。
3. 右トリガー長押し、または右手側の`戻る`で鎧立てを閉じる。
4. 戻れない場合だけ`Reset Stand`を押す。ない場合は左手メニューで一度`収納`し、再度`鎧立て`を開く。
5. `armorStand.scale=1`, `armorStand.exploded=false`, `armorStand.yawDeg`が正面近くであることを確認する。
6. 変身証拠を撮る場合は、mirror/replayまたは`変身へ`へ戻り、replay/transformを開始して `playing=true` または `progress>0` を確認する。
7. 同じ失敗が2回続いたら設定変更を止め、URL、code、`uxState`、写真を残して最後の安定packageへ切り替える。

スタッフ用の即時復旧操作:

- `Reset Stand`: 回転/スケール/分解/検分を初期化。スーツデータは再読込しない。
- `Reload Suit`: 現在のrecall codeからmanifest/assetを再読込。
- `Exit Workshop`: 変身/Replay導線へ戻る。

## 8. 実装ステップ

### P0: 戻れる鎧立てにして、入力競合を潰す

目的: 展示で「鎧立てから戻れない」「右手操作が音声変身に化ける」を起こさない最低限のワークショップ体験を作る。

1. 右手中心の戻る導線を実装する。
   - 右トリガー短押しはパーツ展開/全身へ戻す。
   - 右トリガー長押し、または右手側の`戻る`で鎧立てを閉じる。
   - 戻った後はmirror/replayまたは`変身へ`へ迷わず進める。
   - `armor_stand_returning`または同等の状態をdebug snapshotで判定できる。
2. `uxState`ベースの入力調停を実装する。
   - `armor_stand_observer_idle`, `armor_stand_grabbed_one_hand`, `armor_stand_grabbed_two_hand`を追加。
   - armor stand active時は音声録音/判定/変身遷移を抑止。
   - `armorStand.active`, `armorStand.rightTriggerMode`, `experience.voiceStateIsHistorical` をdebug snapshotへ出す。
3. 鎧全体rootの右グリップ自由回転を実装する。
   - yaw自由、pitch/rollソフトクランプ。
   - 両手/片手の遷移が破綻しないこと。
   - パーツ単体ではなく、鎧全体を一体オブジェクトとして回すこと。
4. 両手スケールを実装する。
   - `0.65`から`1.35`の範囲。
   - scale後もpart placementとhandleが一致すること。
5. `Reset Stand`/`組み立て`を実装する。
   - 回転、scale、選択、分解予約を初期化。
6. 日本語ラベルをvisitor pathへ出す。
   - `つかんで回す`, `変身へ`, `組み立て`。

P0 acceptance:

- 鎧立て中に右トリガー長押し、または右手側の`戻る`で10秒以内にmirror/replayまたは`変身へ`へ戻れる。
- 右グリップで10秒回しても音声変身が開始しない。
- 右グリップで回るのは鎧全体であり、パーツ単体だけが回らない。
- 両手スケール後に全パーツが同じ比率で維持される。
- `Reset Stand`で初期姿勢、scale、状態へ戻る。
- Quest real voice laneでは、`変身へ`後だけ音声待機へ入る。

### P1: 分解とパーツ検分を入れる

目的: Tony Stark workshopらしい「整備台で開く」見せ場を作る。

1. `armor_stand_exploded`を追加する。
   - 部位ごとの展開方向と距離をmanifest slotから決める。
   - 展開/組立は300から600msで補間する。
2. part hover/selectを実装する。
   - ray hover、direct touchの両方に対応。
   - hover outline、selected highlight、非選択パーツdimを追加。
3. `armor_part_inspecting`を追加する。
   - パーツ名、slot、状態、見どころ、戻す/組み立て/変身へを表示。
4. one-hand modeとseated presetを展示設定に追加する。
5. スタッフ用debug overlayに現在状態、選択part、voice suppression理由を表示する。

P1 acceptance:

- 主要パーツを展開しても人型の関係が読める。
- 任意の主要パーツを選択し、戻す/組み立てが効く。
- 個別パーツ選択中でも、右グリップ回転の対象は鎧全体のまま。
- one-hand modeで回転、scale、展開、戻すが完結する。
- debug overlayがvisitor viewを邪魔しない。

### P2: 体験密度と演出を上げる

目的: ただのモデルビューアから、記憶に残るワークショップ体験へ引き上げる。

1. 慣性回転、手元吸着、微細hapticを追加する。
2. 分解/組立に短い光跡、金属音、部品ごとのmicro delayを入れる。
3. パーツ検分に素材/variant/品質メモを追加する。
4. スタッフ用tablet/PC mirrorに選択中パーツと状態を表示する。
5. Replayに「ワークショップで見た角度/選択パーツ」を軽量イベントとして残す。
6. hand tracking対応を検討する。ただしcontroller pathを展示baselineから外さない。

P2 acceptance:

- 演出を入れてもP0/P1の入力競合テストが落ちない。
- 60fps目標を大きく崩さない。重い場合は演出を自動で落とす。
- スタッフが演出をoffにできる。

## 9. テレメトリ要件

現行実装とP0追加後のQuest debug snapshotでは、次フィールドを展示判定の基準にする。個人情報、音声本文、来場者の実名は入れない。

| Field | 見る理由 |
| --- | --- |
| `uxState` / `experience.uxState` | 現在の体験状態。`voiceState`より優先する。 |
| `experience.voiceStateIsHistorical` | 過去の`voiceState=complete`を誤読しないため。 |
| `route.playing`, `route.progress`, `route.playbackSource`, `route.armorStandPreview` | 鎧立て、mirror replay、変身中を分けるため。 |
| `xr.session`, `xr.viewMode`, `xr.archiveViewMode` | 物理Quest上のself/mirror/observer判定。 |
| `query.href`, `query.code`, `query.mockTrigger`, `query.mic` | fresh code、debug mock、real micの切り分け。 |
| `microphone.captureEnabled`, `microphone.mockTrigger` | 実マイク評価かmock評価かの判定。 |
| `armorStand.active`, `armorStand.yawDeg`, `armorStand.pitchDeg`, `armorStand.scale` | 鎧立ての姿勢と拡縮状態。 |
| `armorStand.exploded`, `armorStand.interactionMode`, `armorStand.rightTriggerMode`, `armorStand.interactionCount` | 右トリガーが展開/戻すに割り当たっている証拠。 |
| `armorStand.returnRequested`, `armorStand.returnSucceeded`または同等field | 鎧立てから戻れないP0不具合の切り分け。 |
| `armorStand.floorLiftM` | 足が床下へ沈む再発確認。 |
| `meshes.loaded`, `meshes.visibleCount`, `runtimeDiagnostic` | 見た目の問題がasset不足かmode問題かを切り分ける。 |

将来の分析イベントはP2で追加する。P0/P1の展示判定では、まず上のsnapshotが読めればよい。

集計で見る指標:

- 鎧立て操作回数: `armorStand.interactionCount`。
- 分解利用: `armorStand.exploded` と `armorStand.interactionMode`。
- reset/復旧頻度: スタッフログと `armorStand.scale/yawDeg/exploded` の戻り。
- 音声誤読防止: `query.mockTrigger`, `query.mic`, `microphone.captureEnabled`, `experience.voiceStateIsHistorical`。

## 10. テスト要件

### 10.1 単体/ロジック

- `uxState=armor_stand_*`では、trigger/grip/pinchが音声開始へ到達しない。
- 鎧立て中の右手戻る操作で、`armorStandPreview=false`またはmirror/replay/`変身へ`相当へ遷移する。
- `transform_arming`でのみ音声開始が許可される。
- `voiceState=complete`が残っていても、`uxState`が観察系なら変身しない。
- 右グリップ回転は鎧全体rootにだけ適用され、パーツ単体の独立回転を作らない。
- scale clampが`0.65`未満/`1.35`超過を防ぐ。
- resetでrotation, scale, selectedPart, explodedが初期化される。

### 10.2 ブラウザ/Quest runtime smoke

- Quest viewerを`code=...&mockTrigger=1&mic=0`で開き、観察操作が可能なこと。
- 同URLではreal voice合否を評価しないこと。
- real voice laneでは`mockTrigger=1&mic=0`を外し、`変身へ`後にだけ音声待機へ入ること。
- `uxState`とdebug overlayが現在モードを正しく示すこと。
- 鎧立てから右手操作で戻れること。戻れない場合はP0 fail。
- 分解/組立を10回繰り返して、part transformがドリフトしないこと。

### 10.3 手動展示リハーサル

スタッフ2名以上で次を実施する。

1. 初見スタッフが30秒説明だけで来場者役に操作させる。
2. 座位モードで回転、scale、展開、検分、組立を完了する。
3. 片手モードで同じ操作を完了する。
4. 騒音環境で観察中に「変身」と言い、誤爆しないことを確認する。
5. 鎧立てから右手操作だけでmirror/replayまたは`変身へ`へ戻れることを確認する。
6. `変身へ`後にだけ音声変身が成立することを確認する。
7. 失敗時にstaff resetから30秒以内に次の来場者へ戻れることを確認する。

合格基準:

- 操作説明に迷いが出た箇所はUI文言またはスタッフ台本へ反映する。
- 同じ誤操作が3回以上出たら、実装ではなく仕様の曖昧さとして扱い、入力割当を見直す。
- 展示当日はP0/P1 passをbaselineとし、P2演出はoff可能なenhancementに留める。

## 11. 未決事項

| 論点 | 推奨初期判断 |
| --- | --- |
| 完全6DoF回転にするか | P0はyaw自由 + pitch/rollソフトクランプ。展示安定後に完全自由化。 |
| パーツ単体を手で移動できるか | P1では不可。検分位置へ自動移動のみ。P2で短距離grabを検討。 |
| 音声変身のwake word常時監視 | 不採用。展示騒音とgrab競合を避けるため、明示的な`変身へ`後だけ。 |
| hand tracking baseline | 不採用。controllerをbaselineにし、hand trackingはP2検討。 |
| パーツ情報の詳細度 | 来場者向けは短く、スタッフdebugでslot/asset statusを確認する。 |

## 12. 最終判断

このワークショップ体験のP0は、派手な分解よりも「鎧立てから必ず戻れる」「触っても変身が誤爆しない」「鎧全体を一体として掴める」ことを最優先にする。P1で分解と検分を入れ、P2でTony Starkらしい演出密度を足す。展示の主役はあくまで自分のスーツを呼び出し、観察し、最後に変身する一連の流れである。ワークショップはその山場を奪わず、山場へ期待を貯める装置として設計する。
