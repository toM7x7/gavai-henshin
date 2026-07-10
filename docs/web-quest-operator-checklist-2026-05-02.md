# Web/Quest asset intake 運用チェックリスト

Date: 2026-05-02  
Scope: モデラー納品待ち中に Engineering が先回りで確認する Web Forge / manifest / Quest / fidelity gate の運用手順。

## 目的

このチェックリストは、モデラー納品を受け取ってから慌てて runtime を直すのではなく、受領前に Engineering 側の受け皿を固めるためのものです。

判断の主語を分けます。

- Engineering は、Web/Quest が納品物を正しい key、path、sidecar、4桁コードで扱えるかを見る。
- モデラーは、三面図・意匠・シルエット・配色・部位固有記号の再現性を担保する。
- Web/Quest で fallback 表示や古い code が成功しても、asset intake 成功とは扱わない。

## 0. 作業前ロック

- [ ] 対象納品の manifest path、delivery id、対象 line / module / variant / topping を記録する。
- [ ] 既存の `variant_catalog.json` の順序、`module:base`、canonical 18 module の解決を変えない前提にする。
- [ ] 新規 variant / topping は、承認前に runtime 本採用へ直結させない。まず staging / review 扱いにする。
- [ ] Web / Quest 確認で使う4桁コードは毎回今回発行分だけを使い、古い code を流用しない。
- [ ] Quest Browser は確認開始時に鎧が出ていない初期状態を確認する。

## 1. Manifest 検証

納品 manifest を受け取ったら、まず runtime 表示より先に契約違反を落とします。

```powershell
cd C:\dev\codex\gavai-henshin
python tools\validate_modeler_delivery_manifest.py --manifest <manifest.json>
```

Pass 条件:

- [ ] `contract_version == modeler-delivery-manifest.v1`。
- [ ] `asset_kind` が `canonical | variant | topping | base_suit_texture | reference` のいずれか。
- [ ] すべての path が repo-relative で、repository 外へ出ない。
- [ ] `activate_runtime` が `true` ではない。受領 manifest だけで runtime を有効化しない。
- [ ] canonical は既存18 module のみ。
- [ ] variant は `variant_key == <module>:<variant_asset_key>`。
- [ ] topping は `<module>/toppings/<topping_slot>/<choice_key>/...` と path / key が一致。
- [ ] `.glb` header が glTF 2.0 binary として読める。
- [ ] `.modeler.json` の `module` / `variant_key` / topping 情報が manifest と矛盾しない。
- [ ] `source_concept_ids`、review image、source blend の参照が追える。

追加で確認する sidecar 内容:

- [ ] `bbox_m`、`triangle_count`、`material_zones` が空ではない。
- [ ] `source_concept_ids`、`line_id`、`design_intent` または `fidelity_notes` が個別 sidecar に残っている。
- [ ] 左右ペアの module / key / bbox / slot が mirror として説明できる。

失敗時:

- [ ] validator fail は Web Forge に流さず、manifest / sidecar / path のどれが原因かを1行で返す。
- [ ] GLBだけが壊れている場合は `.glb` の差し戻し、sidecarだけなら `.modeler.json` の差し戻しに切る。
- [ ] catalog 変更が原因なら catalog を戻し、納品物自体は staging として残す。

## 2. Catalog / Intake 構造検証

manifest が通ったあと、既存 runtime の名前解決を壊していないかを見る。

```powershell
python tools\validate_armor_parts_intake.py --root viewer/assets/armor-parts
python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --include-delivered-assets
python tools\smoke_web_glb_load.py
```

期待値:

- [ ] `previewFallbackParts=0`。
- [ ] canonical armor は `previewGlbParts=18` を維持する。
- [ ] `module:base` は canonical GLB に解決し、`variants/` 配下へ逃げない。
- [ ] variant / topping の key は catalog、manifest、filesystem、sidecar で一致する。
- [ ] topping は parent module を置き換えず、add-on として解決される。
- [ ] bbox、mirror pair、attachment offset が fail しない。

注意:

- `--include-delivered-assets` がその作業ツリーで未対応なら、未対応であることを記録し、対応済み環境で再確認する。
- Web smoke が fallback に落ちた状態を「見た目は出たのでOK」と扱わない。

## 3. Web Forge 確認

PC 側で dashboard/API/static server を起動します。

```powershell
npm run dev
```

開く URL:

```text
http://localhost:8010/viewer/armor-forge/
```

確認すること:

- [ ] 初期表示で既存 canonical armor が壊れていない。
- [ ] variant の先頭が `自動選定` になっている。
- [ ] 入力後の生成で、LLM/SakuraAI 選定または fallback 選定の variant が UI に反映される。
- [ ] 手動で variant を変えたとき、再生成前でも Web プレビューの GLB が切り替わる。
- [ ] 選択された variant key が delivered GLB path へ解決している。
- [ ] 選択された topping が delivered GLB path へ解決し、parent module を消していない。
- [ ] selected variant key、selected topping count、conflict、readiness flag が UI またはログで追える。
- [ ] conflict warning が texture generation や Quest recall handoff より前に見える。
- [ ] 4桁コードが今回の選択状態に対して発行される。

Web visual QA:

- [ ] front / side / back / 3Q でシルエット、浮き、貫通、密度差を見る。
- [ ] helmet / chest / back / waist / shin / boot の最低6部位で、元案の固有記号が読める。
- [ ] chest / back / waist は平面 decal ではなく outer armor shell として読める。
- [ ] shoulders / upper arms / shins / boots は body volume を失っていない。
- [ ] topping の on/off で表示差があり、off 時に parent module が欠けない。

## 4. Quest 確認

Quest runtime は Web Forge とは別に Vite dev server で起動します。

```powershell
npm run dev:quest
```

Quest USB 確認では原則 `5173` を使います。別プロセスで `5174` などへ逃げた場合は、占有を解消してからやり直します。

ADB:

```powershell
adb devices
npm run dev:quest:adb
```

内部で期待する reverse:

```powershell
adb reverse tcp:5173 tcp:5173
adb reverse tcp:8010 tcp:8010
```

Quest Browser URL:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1
```

呼び出し前:

- [ ] ページを開いただけでは鎧が出ていない。
- [ ] `mockTrigger=1` のデモ表示を4桁コード成功の代替にしない。
- [ ] Quest Browser のタブ復元、キャッシュ、前回 code の残留を疑う。

4桁コード呼び出し後:

- [ ] Web Forge で今回発行した4桁コードだけを入力する。
- [ ] Web Forge と同じ variant / topping / module 構成が Quest 側に出る。
- [ ] helmet / chest / shoulder / shin / boot の主要部位が Web と同じ選択状態になっている。
- [ ] Quest 側の状態表示またはログが今回の code を参照している。
- [ ] 小さすぎる、浮く、骨からズレる、向きが違う場合は runtime scale だけで吸収せず、GLB寸法と sidecar を疑う。
- [ ] Web 側で選択を変えたら、古い4桁コードを再利用せず、新しい code を発行して呼び直す。

切り分け:

- [ ] Quest Browser のタブを閉じて開き直す。
- [ ] Web Forge を `Ctrl+F5` でハードリロードする。
- [ ] 必要なら新しい4桁コードを発行する。
- [ ] Quest 側に `RESET` がある場合は実行し、鎧が消えることを確認する。
- [ ] 状態が残る場合は Quest Browser の site data / cache を clear する。
- [ ] `npm run dev`、`npm run dev:quest`、`npm run dev:quest:adb` を順に再実行する。

## 5. 差し戻し基準

Engineering 差し戻し:

- [ ] manifest validator が fail する。
- [ ] GLB / sidecar / source blend / review image の必須 path が存在しない。
- [ ] `activate_runtime=true` で納品されている。
- [ ] `variant_key`、filesystem slug、sidecar の module / key が一致しない。
- [ ] topping が parent module を置き換える。
- [ ] canonical 18 module の表示、`module:base`、既存 catalog 順序を壊す。
- [ ] Web smoke が `previewFallbackParts=0` にならない。
- [ ] Web Forge の選択状態が4桁コードに保存されない。
- [ ] Quest が Web Forge と同じ code / variant / topping を再現できない。

Modeler 差し戻し:

- [ ] front / side / back / 3Q の review sheet がない。
- [ ] 元三面図と並べた `source_overlay_front.png` 相当の比較がない。
- [ ] grayscale でも line 差分が読めない。
- [ ] base suit color blocking が弱く、全体が同じ白い試作装甲に見える。
- [ ] 顔、胸、背面、脚部の固有記号が元案から離れている。
- [ ] sidecar に `source_concept_ids`、`line_id`、`design_intent`、`fidelity_notes` がない。

保留でよいもの:

- [ ] 既知の geometry tolerance warning は、runtime 契約を壊していなければ Wave 2.1 shape refinement として分離する。
- [ ] texture の最終品質は Nanobanana / texture工程の gate に送り、GLB intake の pass/fail と混ぜない。

## 6. Fidelity gate

技術 gate と fidelity gate は別判定にします。manifest が pass しても、元三面図再現性が弱ければ main runtime へ本採用しません。

Gate A: technical intake

- [ ] manifest pass。
- [ ] catalog / intake validation pass。
- [ ] Web GLB smoke pass、`previewFallbackParts=0`。
- [ ] Web Forge で selected variant / topping が delivered GLB を使う。
- [ ] Quest で今回の4桁コードから同じ装備を再現できる。

Gate B: visual fidelity

- [ ] 元三面図と front / side / back / 3Q を横比較できる。
- [ ] line ごとの silhouette が一目で違う。
- [ ] 顔と胸が主役として読める。
- [ ] 背面と側面に元案由来の情報量がある。
- [ ] base suit color blocking と外装色が分離している。
- [ ] helmet / chest / back / waist / shin / boot の最低6部位で固有記号が入っている。

Gate C: adoption decision

- [ ] Gate A と Gate B の両方が pass したものだけ staging から main runtime 候補へ進める。
- [ ] Gate A pass / Gate B fail は「技術受領済み、fidelity差し戻し」と記録する。
- [ ] Gate A fail は Web/Quest に流さず、manifest / path / sidecar / GLB の契約修正を先に返す。
- [ ] Quest でだけ破綻するものは Web pass でも adoption しない。

## 7. 最小エビデンス

受領レビューごとに残すもの:

- [ ] 実行したコマンドと結果。
- [ ] manifest path と delivery id。
- [ ] Web Forge の対象4桁コード。
- [ ] Web front / side / back / 3Q のスクリーンショットまたは保存先。
- [ ] Quest 呼び出し結果、code、確認端末、失敗時の切り分けメモ。
- [ ] pass / fail / hold の判断と、Engineering差し戻しかModeler差し戻しかの分類。

## 8. 運用の結論

納品待ち中の Engineering の仕事は、絵の良し悪しを先に決めることではなく、納品物が入ってきた瞬間に「契約違反」「Web Forge消費不良」「Quest recall不一致」「fidelity不足」を分離できる状態を作ることです。

最短の合格ルートはこれです。

```text
manifest pass
-> catalog/intake pass
-> Web Forge selected GLB pass
-> 4桁コード発行
-> Quest recall pass
-> source overlay / 4 view fidelity pass
-> staging から main runtime 候補へ昇格
```
