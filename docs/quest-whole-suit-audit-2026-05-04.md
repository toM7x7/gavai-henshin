# Quest全身アーマー静的監査メモ

`tools/audit_quest_armor_whole_suit.py` は、Questを起動せずに全身アーマーの組み立てをJSONで確認する軽量監査です。部品単体のローカル配置ではなく、Questランタイム内の最終全身配置を読み、人体に対する距離感・左右対称・欠品・明らかな貫通を先に潰すためのCI向け土台です。

## 使い方

通常実行:

```powershell
python tools\audit_quest_armor_whole_suit.py
```

CIや保存用:

```powershell
python tools\audit_quest_armor_whole_suit.py --output tests\.tmp\quest-whole-suit-audit-current.json --fail-on fail
```

監査対象は主に次のQuestランタイム定数です。

- `ARMOR_PARTS`
- `VR_BODY_PART_POSES`
- `QUEST_ASSEMBLY_ADJUSTMENTS`
- `QUEST_GLB_TARGET_SIZES`

出力の見る場所:

- `status`: `pass` / `warn` / `fail`
- `missing_*`: 欠品、姿勢、サイズ契約の不足
- `global_extents_m`: 全身の高さ・幅・奥行き
- `human_fit_distances_m`: 頭、胴、腰、腕、脚などの主要な隙間
- `symmetry_checks`: 左右パーツの中心点とサイズ差
- `obvious_interpenetrations`: 非隣接パーツの明らかなAABB貫通

## passが保証すること

`pass` は、静的な全身配置契約として次を満たすという意味です。

- 期待される18部品がQuest用の姿勢・サイズ・アセットを持っている
- 全身の高さ、幅、奥行きが人型スーツとして大きく破綻していない
- 左右ペアの中心・サイズが許容範囲内にある
- 主要な人体フィット距離が硬い閾値内にある
- 非隣接パーツ同士の明らかな箱貫通がない

## passが保証しないこと

この監査はAABB中心の静的チェックです。`pass` でも次は保証しません。

- 実メッシュ表面の細かなめり込み、浮き、角の刺さり
- Quest実機での見え方、視差、ライティング、解像感
- モーション中の貫通や、手首・膝・肩の可動時破綻
- 観客視点でのかっこよさ、密度、シルエットの説得力
- 1cm未満のマイクロ調整の良し悪し

つまり、これは「事故を先に検知するゲート」であり、「最終の見た目OK判定」ではありません。

## Quest写真フィードバックとの組み合わせ

おすすめ順序:

1. まず `audit_quest_armor_whole_suit.py` を通し、欠品・大きなズレ・明らかな貫通を潰す。
2. Questで正面、左右、背面、斜めの写真を撮る。
3. 写真で、浮き・刺さり・隙間・左右差・シルエット崩れを部位ごとに見る。
4. 写真の違和感を `QUEST_ASSEMBLY_ADJUSTMENTS` 相当のマイクロ調整候補に落とす。
5. 調整後に再度この静的監査を通し、大きな破綻を再発させていないか確認する。

写真で見るべき優先点:

- helmet: 頭に浮いていないか、胸と近すぎないか
- chest/back/waist: 胴体が箱ではなく、前後左右で体に巻いて見えるか
- shoulder/upperarm/forearm/hand: 肩から手首までの流れが切れていないか
- thigh/shin/boot: 膝と足首でめり込みすぎず、足元が接地して見えるか

静的監査で大事故を消し、Quest写真で「人が着ている感じ」を詰める。この2段構えで、部品別チェックだけでは拾えない全身の違和感を減らします。
