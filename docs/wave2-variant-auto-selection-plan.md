# Wave2 Variant/Topping Auto Selection Plan

Date: 2026-05-01

Scope: Wave2 variant/topping と LLM 自動選択方針の整理。検索エンジンは使わず、ローカル docs と現在のリポジトリ状況だけを前提にする。

## 1. 現状

Wave2 は「variant/topping の契約がある」段階から、「モデラー納品物を Web Forge に実際に食わせる」段階へ進んでいる。

- モデラー納品は 54 variant GLB / 32 topping GLB。
- canonical armor load は Web Forge 側で `previewGlbParts=18` / `previewFallbackParts=0` まで確認済み。
- Web Forge には variant UI / topping UI の入口があり、variant/topping の選択状態、conflict、visual-density、Nanobanana prompt linkage を扱う契約がある。
- ただし、ユーザーに見える体験としては「選択した variant/topping が本当に描画へ反映された」と断言できる QA evidence がまだ弱い。

ここでの重要な区別:

- `previewFallbackParts=0` は canonical 18 module の GLB 読み込み健全性を示す。
- 54/32 の variant/topping inventory が存在することは、選択 UI が見た目へ反映されることとは別問題。
- 次の milestone は「たくさん選べる」ではなく、「入力から自動で選ばれた構成が、Nanobanana 生成と同じタイミングで、見た目・manifest・prompt に一貫して反映される」こと。

## 2. ユーザーが見た問題の整理

ユーザーが見た「選択しても見た目が変わらない」は、現時点では単一原因と決め打ちしない。少なくとも次の 3 系統を分けて扱う。

### A. 描画反映の問題

UI state と renderer/asset resolver の間で、選択した `variant_key` / topping が GLB path へ解決されていない可能性。

- variant を選んでも canonical module GLB のまま表示している。
- topping を選んでも parent module の上に追加 import されていない。
- manifest や job payload には入っているが、preview scene の loader path が読んでいない。
- conflict や readiness flags は表示されるが、実物 mesh 差し替えが遅れている。

この場合は engineering issue。代表セットで selected path、loaded path、scene object name、visible object count をログ化すれば切れる。

### B. 起動プロセスの問題

古い dev server / 古い bundle / stale cache / 生成前の provisional preview を見ていた可能性。

- 最新の Web Forge bundle ではなく、前回起動したプロセスを見ている。
- asset catalog や sidecar が更新されたが、ブラウザ側 cache または dev server が古い。
- Nanobanana 完了前の `final_texture_ready=false` preview を最終結果として見ている。
- variant/topping GLB が存在する tree と、Web Forge が参照している working tree がズレている。

この場合は process issue。起動時に build hash、asset root、variant/topping inventory count、selected configuration id を画面または debug panel に出すと事故が減る。

### C. 差分が小さい問題

選択は反映されているが、ユーザー視点では差が小さく、正面カメラや半透明プロキシでは見分けにくい可能性。

- variant 名が意味する形状差と、実際の silhouette 差が弱い。
- topping が小さすぎる、または正面/通常距離では埋もれる。
- material が仮素材で、形状差より白/半透明/flat shading の印象が勝つ。
- camera angle が差分の出る側面・背面・3Q を見せていない。

この場合は art direction / QA issue。variant closeup、A/B toggle、差分が見えるカメラ、命名と silhouette の再設計が効く。

## 3. 方針: LLM/Sakura AI が自動構成する

ユーザーに variant/topping を手で選ばせる UI は主役にしない。主役は「入力情報から Sakura AI / LLM が変身構成を組む」体験にする。

入力:

- ユーザーの brief
- protect target / temperament / height / palette / motif
- 生成したいヒーロー性、かわいさ、重装感、速さ、神秘性、機械感などの design intent
- catalog metadata: `variant_key`, `part_family`, `base_motif_link`, `topping_slots`, `conflicts_with`, `texture_zone_notes`

LLM/Sakura AI の出力:

- canonical module ごとの selected `variant_key`
- parent module ごとの selected topping list
- 選択理由の短い design rationale
- conflict 解消結果
- Nanobanana prompt へ渡す `variant_prompt_summary`
- Web Forge preview と Quest recall へ渡す manifest metadata

反映タイミング:

- 画像生成 Nanobanana と同じ「構成確定」のタイミングで variant/topping を確定する。
- Nanobanana prompt は、確定済み variant/topping を final prompt constraints として読む。
- Web Forge preview は、同じ selected configuration を GLB path 解決と prompt linkage の両方に使う。
- 後から texture が完了した場合も、variant/topping selection は変えず、texture pointers だけを更新する。

つまり、variant/topping は「ユーザーが後でいじる装飾」ではなく、「AI が変身コンセプトを 3D 構成へ落とすための骨格」として扱う。

## 4. UX

基本 UX は、手動選択ではなく次の流れに寄せる。

1. ユーザーが入力する。
2. Sakura AI / LLM が variant/topping を自動構成する。
3. Web Forge が構成済みスーツを表示する。
4. Nanobanana が同じ構成を前提に texture / material を生成する。
5. 必要なら上級者だけが variant/topping を手直しする。

標準ユーザー向け:

- variant/topping の一覧選択を最初から見せない。
- 「軽快」「重装」「神秘」「機械」「かわいい」「鋭い」など、意味レイヤーの操作を優先する。
- 自動構成結果は、見た目と短い理由で伝える。
- 選択 UI より、before/after、A/B、3Q view、closeup を優先する。

上級者向け:

- selected `variant_key` と topping を edit panel で修正できる。
- conflict や slot overflow は警告として出す。
- 手直し後は Nanobanana prompt と manifest を再同期する。
- 「手動変更が AI rationale と矛盾している」場合は、再提案または rationale 更新を行う。

UX の判断基準:

- ユーザーが気にするのは `helmet:sleek` というキーではなく、「自分の入力が見た目に反映されたか」。
- したがって UI は catalog 操作ではなく、意図 -> 構成 -> 視覚差分の確認を中心に組む。
- variant/topping UI は開発 QA と上級者補正のために必要だが、通常体験の入口にはしない。

## 5. 自動選択ロジックの最小契約

最初の実装は、複雑な最適化よりも「説明可能で壊れにくい」ことを優先する。

### Selection Plan

LLM/Sakura AI は JSON で次を返す。

```json
{
  "selection_version": "wave2-auto-selection.v1",
  "selected_variants": {
    "helmet": "helmet:sleek",
    "chest": "chest:bold"
  },
  "selected_toppings": {
    "helmet": [
      {
        "topping_slot": "crest",
        "topping_key": "base"
      }
    ]
  },
  "design_rationale": [
    "helmet:sleek keeps the silhouette fast and readable.",
    "crest/base adds a clear hero marker without replacing the helmet."
  ],
  "conflict_status": "resolved",
  "variant_prompt_summary": "Fast readable silhouette with a sleek helmet crest and bold torso armor."
}
```

### Guardrails

- canonical module ID は変えない。
- variant は同じ module slot の置換として扱う。
- topping は parent module の local slot 追加として扱い、parent の代替にしない。
- `conflicts_with` に当たる組み合わせは選ばない。
- topping 数は最初は少なめにし、視認性が高い slot を優先する。
- selected configuration は Web Forge preview、Nanobanana prompt、Quest recall manifest で同じ ID を共有する。

### QA Logging

ユーザーの「変わらない」を潰すため、最低限これを debug 表示または log に残す。

- selected `variant_key`
- resolved variant GLB path
- loaded scene object name
- selected topping slot/key
- resolved topping GLB path
- `previewFallbackParts`
- `final_texture_ready`
- configuration id / generated-at timestamp

## 6. モデラー向け依頼観点

LLM 自動選択を成立させるには、catalog 上の名前と実物の見た目が対応している必要がある。モデラーへの依頼は「もっと数を増やす」より、「選ばれた時に視認できる差を作る」に寄せる。

### Variant Naming

- 名前から silhouette と役割が想像できること。
- `sleek`, `heavy`, `spike`, `core`, `wing`, `shield`, `blade`, `wide`, `compact` など、LLM が design intent と対応づけやすい語にする。
- 同じ module 内で、名前だけ違って見た目が近い variant を避ける。
- `variant_prompt_summary` に入れても破綻しない短い意味を持たせる。

### Silhouette

- 正面だけでなく、side/back/3Q で差が出る形にする。
- helmet crest、chest core、back ridge、shoulder volume、shin/boot edge など、遠目でも読める外形差を優先する。
- 小さな panel line の違いだけを variant の主差分にしない。
- Web Forge の通常距離で見た時に、「選んだ意味」が 1 秒以内に分かる差を作る。

### Topping Slot

- topping は parent module の成立を壊さない add-on として設計する。
- slot 名は意味で安定させる: `crest`, `visor_trim`, `chest_core`, `back_fin`, `shoulder_spike`, `belt_buckle`, `shin_fin`, `boot_toe` など。
- topping は ON/OFF で差が読める bbox と配置にする。
- slot transform が inferred のままだと preview 差分の責任分界が曖昧になるため、優先 slot から local transform を確定する。
- 左右 mirror の扱いは、LLM が片側だけを選んで事故らないように `mirror_of` / pair rule を明示する。

### Evidence

- representative set は closeup front/side/back/3Q を用意する。
- 「ユーザーが見たら差が分かる」ことを acceptance に含める。
- 形状差が小さい variant は、名前変更・用途変更・統合・廃止の候補にする。

## 7. 次の実装順

1. Web Forge で selected variant/topping が resolved GLB path に到達しているかを debug 表示する。
2. LLM/Sakura AI の `wave2-auto-selection.v1` JSON 契約を定義する。
3. Nanobanana job payload と Web Forge preview が同じ selected configuration を読むようにする。
4. 代表セットで A/B toggle と 3Q/closeup を確認する。
5. 差分が弱い asset をモデラー依頼へ戻す。

最初のゴールは、全 54/32 を完璧に自動選択することではない。代表的な 1 セットで「入力 -> AI 構成 -> GLB 見た目反映 -> Nanobanana prompt 反映 -> manifest 保存」まで一本につながることを証明する。
