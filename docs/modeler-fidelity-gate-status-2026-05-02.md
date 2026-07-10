# Modeler Fidelity Gate Status - 2026-05-02

Date: 2026-05-02

## Conclusion

最新のモデラー納品は **technical pass / fidelity hold** として扱う。

`.claude/worktrees/jovial-cohen-4bf60f` には `first-three-lines-2026-05-02` の30アセット納品、manifest、レンダー画像が存在する。manifest validation、catalog validation、pytest は通っているが、元の三面図に対する再現性がまだ足りないため、main runtime、Web Forge本表示、Quest装着表示には採用しない。

この納品は「手続き生成とvalidator土台の確認サンプル」として保持する。ユーザー体験に出す装備ラインとしては未合格。

## Latest Delivery Location

```text
.claude/worktrees/jovial-cohen-4bf60f
```

主な確認対象:

- `docs/modeler-handoff-three-lines-2026-05-02.md`
- `docs/modeler-deliveries/first-three-lines-2026-05-02.delivery-manifest.json`
- `docs/_three_lines_renders/line_rescue_knight/`
- `docs/_three_lines_renders/line_royal_insect/`
- `docs/_three_lines_renders/line_final_oath/`
- `viewer/assets/armor-parts/*/variants/*`

## Why It Is Not Merged Into Main

- 技術的にはGLB、sidecar、source blend、manifestの形式が揃っている。
- ただし、三面図から読み取れるヒーロースーツの色面、顔、胸、背面、脚部、ブーツの意匠差がまだ弱い。
- 3系統 `line_rescue_knight` / `line_royal_insect` / `line_final_oath` のシルエット差が、Web/Quest上で来場者に伝わる密度に届いていない。
- Web/Questへ入れると、スケール問題、装着位置問題、造形問題が混ざって原因切り分けが難しくなる。

そのため、今回は main へ取り込まず、次回納品に対して fidelity gate を明確にする。

## Required Rework Items

次回のモデラー再納品では以下を必須にする。

1. `source_overlay_front.png`
   - 各ラインごとに、元三面図frontと納品render frontを横並びまたは半透明overlayで比較できる画像を付ける。
   - 完全一致ではなく、シルエット、顔、胸、背面、脚部、ブーツの読みが確認できることを目的にする。

2. Base suit color blocking
   - 単色ボディではなく、人体表面に沿った特撮ボディスーツの色面分割を入れる。
   - 例:
     - `line_rescue_knight`: 白/青/シアン発光
     - `line_royal_insect`: 緑/白/金、複眼・甲殻の読み
     - `line_final_oath`: 白/金/シアン、最終フォームらしい密度

3. Stronger silhouette difference across the 3 lines
   - `line_rescue_knight`: compact、救助騎士、青いvisor、胸coreは読みやすく。
   - `line_royal_insect`: compound-eye、crest、emerald V、背面に羽または甲殻のニュアンス。
   - `line_final_oath`: crown visor、大きめcore、白金シアンの高密度最終フォーム。
   - grayscaleでもhelmet、chest、shoulder/back、bootの違いが判別できること。

4. Boot closeup
   - 各ラインごとに `boot_closeup_side.png` を追加する。
   - 足首、ソール、つま先、すねからブーツへの接続、色面分割を確認できる距離にする。

5. Top-level sidecar metadata
   - 個別 `.modeler.json` のトップレベルに最低限以下を入れる。
     - `source_concept_ids`
     - `line_id`
     - `design_intent`
     - `fidelity_notes`
   - manifestだけでなく、asset単体を見ても「どの三面図の何を再現したか」を追える状態にする。

## Next Intake Procedure

次回受領時は以下の順で扱う。

1. モデラーworktree上で manifest を検証する。

```powershell
cd C:\dev\codex\gavai-henshin\.claude\worktrees\<delivery-worktree>
python tools\validate_modeler_delivery_manifest.py --manifest docs\modeler-deliveries\<delivery>.delivery-manifest.json
```

2. catalogとdelivered assetの整合を確認する。

```powershell
python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots
```

3. `source_overlay_front.png`、`boot_closeup_side.png`、front / side / back / 3q render を人間の目で確認する。
4. Engineering staging branchへ、runtime activationなしで assets / sidecar / review images だけを取り込む。
5. Web Forgeで元三面図と横比較し、fidelity pass後にだけ `variant_catalog.json` mappingとruntime表示を許可する。
6. Web表示が通ってからQuest smokeへ回す。

## Why Quest Comes Later

Questでは距離、解像度、装着姿勢、頭部/手元の視界、コントローラー操作が加わり、見た目の問題とruntimeの問題が混ざる。

Web上で三面図fidelityが弱い状態のままQuestへ入れると、原因が「造形」「スケール」「attachment」「material」「VR内表示タイミング」のどれなのか判断しづらい。まずWeb stagingで元三面図、overlay、closeupを見て、ヒーロースーツとして識別できる状態を確認してからQuestへ送る。
