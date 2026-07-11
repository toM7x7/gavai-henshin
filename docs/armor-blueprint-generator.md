# ArmorBlueprint ジェネレータ — 思いから装甲を、プログラムの速度で (2026-07-05)

Status: Active / v1 実装済み・動作実証済み

## 何をするものか

「設定した思い・欲しい意匠」から、**滑らかで緻密、エッジの効いた特撮ヒーロー装甲**を
プログラムが数秒〜数十秒で生成する機構。LLMの役割は「思い→設計図JSON(ArmorBlueprint)」の
解釈**1コールのみ**。ジオメトリ生成にLLMは一切関与しないため、時間もトークンも消費しない。

```text
思い/意匠テキスト
   │
   ├─ (A) ルールコンパイラ  src/henshin/armor_blueprint.py  … LLMなし・ミリ秒・決定論的
   └─ (B) LLM解釈           llm_prompt() を Gemini/Sakura に1回投げる … 豊かな解釈
   │
   ▼
ArmorBlueprint v1 JSON (schemas/armor-blueprint.v1.schema.json で検証)
   │
   ▼
tools/generate_armor_from_blueprint.py  →  Blender headless (~10秒/部位)
   │
   ▼
<module>.glb + modeler-part-sidecar.v1 + preview mesh.v1 + 3/4レンダPNG
(既存の armor-parts 納品契約と同一形式 — Web Forge / Quest にそのまま載る)
```

## なぜカクカクしないのか(生成技法)

ハードサーフェス作家の手法をそのままパラメトリック化している:

1. **超楕円断面ロフト** — 断面形状は指数1本で「sharp(鋭い)/ rounded(英雄的)/ squared(重装)」
   を連続的に変化。プロファイル曲線(Catmull-Rom)がシルエットの痩せ・張りを作る。
2. **溝はケージに直接編み込む** — パネルラインは後加工ではなく制御ケージの行・列として挿入
   (リング溝・子午線溝)。ゾーン(accent/emissive)も面単位でこの時点で確定。
3. **クリース + Subdivision Surface** — 溝の縁・バイザー境界・ブレードの刃にクリースを打ち、
   サブディビジョンで曲率連続の滑らかな面と「尖り」を同時に得る。
4. **Solidify + 角度ベベル** — シェルに実厚、機械加工的なエッジハイライト。
5. **フィーチャーメッシュ** — crest_fin(クレスト刃)/ horn_pair(角)/ visor / v_core は
   独立パラメトリックメッシュとして生成し結合。

## 使い方

**作業ディレクトリはすべてリポジトリルート**(このファイルの2階層上)。ターミナルを開いたら必ず:

```powershell
cd D:\personal_dev\gavai-henshin\gavai-henshin
```

以降のコマンドは全部ここから実行する(相対パス `examples/…` `output/…` はこの位置基準。
出力はすべて `output/blueprint-armor/` 以下 = gitignore 済みのローカル作業領域)。

```powershell
# サンプル設計図から生成(ヘルメット+胸+肩、レンダ付き)
python tools/generate_armor_from_blueprint.py `
  --blueprint examples/armor-blueprint.sample.json `
  --out-dir output/blueprint-armor --quality runtime --render

# 思いから直接(LLMなしのルートA)
python -c "
import sys, json; sys.path.insert(0, 'src')
from henshin.armor_blueprint import compile_blueprint
bp = compile_blueprint('たとえ独りでも仲間を守る盾になる。闘志は牙となる。')
open('my.blueprint.json','w',encoding='utf-8').write(json.dumps(bp, ensure_ascii=False))
"
python tools/generate_armor_from_blueprint.py --blueprint my.blueprint.json --render
```

Blender は自動発見(`HENSHIN_BLENDER_EXE` env → PATH → Program Files)。検証は
`henshin validate --kind armor-blueprint`(validators に登録済み)。

### 全身装着ビュー(VRMフィット確認)

生成した18部位を default.vrm の実ボーン位置に装着し、正面/斜め/側面をレンダする:

```powershell
# 単一の設計図を全身装着してレンダ
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --factory-startup `
  --python tools/blender/armor_fullbody_assembler.py -- `
  --blueprint output/blueprint-armor/intent-demo.blueprint.json `
  --out-dir output/blueprint-armor/fullbody --quality preview --label demo
```

装着スケールは Quest ランタイムの装着契約(QUEST_GLB_TARGET_SIZES)+ 素体クリアランス表
(`WORN_SIZE` / `CLEARANCE` in armor_fullbody_assembler.py)。関節の逃げ(膝・肘のギャップ)は仕様。

`--save-blend 1` を付けると組み上げ済みシーンを `<label>.assembly.blend` に保存する。
Blenderで開けばフルスーツをその場で回して検分できる(モックアップ操作)。
実装メモ: glTFインポータはボーンtailを合成(+Z)するため、手足の向きは
関節チェーン(UpperArm→LowerArm→Hand 等)から取ること(NEXT_JOINT 表)。

**適合審査(Fit Audit)**: 装着時に各パーツの体貫通を BVH 距離で実測し、貫通頂点を
体表法線方向へ自動押し出し(conform)して収束させる。合否は貫通率≤1%・深さ≤4mm。
収束したルール(WORN_SIZE / gap / 関節reveal / conform vs enclose)は
[armor-body-fit-rules-2026-07.md](armor-body-fit-rules-2026-07.md) に「物理設計図ルール」として固定。
`assembly.json` の各パーツ `fit_audit` に実測値が残る。

### 検証コンソール(ブラウザUI・リアルタイム構築)

メッセージを打って「生成」ボタンで、①設計図の即時解読(感情軸・パレット・部位意匠)→
②ボタンで3Dビルド → ③レンダがギャラリーに順次表示、をブラウザで見られる:

```powershell
python tools/armor_lab_server.py            # http://localhost:8020/
```

技術構成(依存ゼロの stdlib http.server):
- `POST /api/compile` — テキスト→設計図(即時・Blender不要)。感情軸/パレット/各部位の意匠を返す
- `POST /api/build` / `POST /api/assemble` — Blenderジョブを別スレッドで起動、job_id を返す
- `GET /api/job?id=…` — ジョブ状態をポーリング(ブラウザが1.6秒間隔で確認)。完了でレンダURLを返す
- `GET /r/<path>` — レンダPNGを配信(lab-ui配下のみ・パストラバーサル遮断)

Blenderは重いので `_BLENDER_LOCK` で1ジョブずつ直列化。出力は
`output/blueprint-armor/lab-ui/<設計図ID>/` に階層で残る(設計図JSON・GLB・sidecar・レンダ)。

### バリエーションラボ(仮説設計図の比較)

「LLM/ルールが返しうる複数の仮説設計図」をランダムサンプリングして都度生成し、
全身装着レンダのコンタクトシートで生成差を一覧する:

```powershell
python tools/armor_variation_lab.py --count 3 --quality preview          # 完全ランダム
python tools/armor_variation_lab.py --count 4 --seed 7                   # 再現可能なラン
python tools/armor_variation_lab.py --count 3 --intent "守護と誓い"       # 意図固定・軸だけ変動
```

出力: `output/blueprint-armor/lab/<run>/contact-sheet.png` + 各 variant の blueprint JSON とレンダ3面。

## 変奏の仕組み(同一個体を出さない) — 2026-07-08

「別の言葉でも形が似る」を解消するため、コンパイラは3つのレバーで分岐させる:

1. **意図シードRNG** — `sha256(意図文)` を種にした決定論PRNG。同じ文言は完全同一、
   違う文言は同じ支配軸でも別個体になる。プロファイル制御点・溝の本数と位置・特徴の
   パラメータ・非対称量をこのRNGで揺らす。
2. **キーワード辞書** — 色語(赤青緑紫金銀黒白橙桃…→ base/glow を直接決定、`光`系語で発光色を優先)と
   形状語(鋭/丸/重/細/棘/角/翼/冠/昆虫/獣/速)を検出し、断面指数・棘/翼/角の有無・エッジ様式に反映。
3. **連続断面(cross_section)** — 3択(sharp/rounded/squared)ではなく 1.4〜3.6 の連続指数を
   軸+語彙+RNGで決める。同じ「守護」でも「静か」1.73 と「鋼鉄」2.05 で箱っぽさが変わる。

新ジオメトリ: `spike_row`(棘列)・`wing_pair`(背の翼)。ポリゴン密度は各ロフトの rows/cols を
約1.4倍に増やし、マテリアルはゾーン別に metallic/roughness/coat を分け、発光は暗拡散+飽和発光で
色として読ませる。パレットは全チャンネルに微小ジッターを掛けるので二着として同じ配色は出ない。

検証例(実測): 「守護。青い盾」→ base #223F72、「守護。赤い盾」→ base #7E1F22。
「獣の闘志、牙と棘」→ 赤メタル・鋭角兜・脛に棘、「王の守護、翼と冠」→ 銀・丸兜・背に翼、
「緊張の甲殻、昆虫」→ 紫黒・口元ベント。同じ文言は常に同一、違えば必ず別個体。

## 層構造アーキテクチャ(総構造)— 2026-07-08

「色しか変わらない」問題の根治。コスプレ/戦闘スーツの実設計と同じく、**部位=複数の板パーツの重ね**にした:

- **overlay_plate** — 基底シェルの上に浮く装甲板。position/t_span/angle_deg/arc_deg(位置と大きさ)、
  lift_m(浮き量)、corner(0=角板〜1=レンズ板)、mirror(左右対)。縁は自動でシェルへ潜り「取付部品」として読める
- **edge_blade** — 流線の刃フィン(疾風・スピード意匠)。razor クリースの外縁
- **プレート・スタイル**(コンセプト族): `bulwark` 重装=大判角板2-3枚 / `lamellar` 甲殻=細レンズ板3-6枚 /
  `aero` 疾風=低い長板+edge_blade / `brutal` 獣=非対称チャンキー板+棘 / `hero` 標準。
  語彙+軸で決定、胸・肩・四肢・兜(頬ガード)に適用

実証: 「鋼鉄の重装」→白い要塞(胸に積層スラブ)、「疾風の流線」→クロムの細身+脛の刃フィン。
構造レベルで別コンセプトと分かる。サイズ修正: 兜 worn 0.30h/クリアランス1.15、腰 1.22(頭・腰の過大を解消)。

## 板割り写経 (2026-07-08) — examples/armor-blueprint.plate-study.json

参照 `examples/Gemini_Generated_Image_ (2).png`(150kg重装型)の全身パネルレイアウトを
**35枚超の板として手で転写**した演習。5ラウンドの反復で得た学びと拡張:

- **taper 追加**(overlay_plate: -0.7〜0

全身装着ジョブが `<label>.assembly.glb` を出力し、UIに **three.js オービットビューア**が出る
(ドラッグ回転・ホイールズーム、vendored three を `/vendor/` で配信、依存なし)。
読み込み時に**蒸着エフェクト**が自動再生: 粒子が収束→装甲が部位ごとに順次フェード+発光フラッシュ→
`SEAL: APPLIED — 蒸着完了`。「蒸着リプレイ」ボタンで何度でも。

## 微細ディテール文法 v4 — 「ツルツル」の根治(2026-07-09)

「今のやつはツルツルで全然かっこよくない」への構造対応。参照三面図の**製造痕**
(パネル段差の縁・ボルト・ベント・リム)を文法化し、頂点密度を約2倍に引き上げた:

- **panel_step** — シェル自体のセクター隆起(position/t_span/angle_deg/arc_deg/raise -1〜1/mirror)。
  境界に行/列を自動注入+クリースで、プレス板の継ぎ目段差がナイフエッジで出る
- **vent_slats** — 凹ポケット+ルーバー(slats 2-8/depth/mirror)。口元・脇腹・脛の機械ベント。
  凹部は自動で trim ゾーン(暗色)
- **rivet_row** — 六角ボルト頭の列(count/arc_deg、along:'meridian'で縦列)。シェル表面に直接打つ
- **overlay_plate 拡張** — rim(0-1: 縁の補強リッジ)+ bolts(true: 四隅に締結ボルト)。
  板が「置いてある」から「取り付けてある」に変わる
- **キャビティ陰影の頂点カラー焼き込み** — 最終メッシュのエッジ凹凸から凹=汚れ暗部/凸=鈍い光沢を
  'wear' カラー属性へ焼く。glTFの COLOR_0 × baseColorFactor に折り込まれ、three.js でも
  Blenderレンダでも溝・段差・ベントに影が乗る(テクスチャ不要のAO)
- **ロフト密度 約2倍**(兜 26×68 等)+ ディテール境界の適応注入。1部位 20-40万tris(runtime)
- **V字バイザーの幾何ワープ化** — 斜め境界をゾーンで切るとサブサーフで波打つ(実測)。
  バイザー帯はパラメータ空間で矩形(=材質境界は常にメッシュ行)に保ち、V字は
  シェル自体の眉ワープ(_visor_geo_warp)で出す。境界スナップより一段クリーン
- 発光は Emission Strength 2.4(大面積バイザーの白飛び対策)

ルートAは `_details_for`(部位×スタイル×感情軸で段差/ベント/リベットを自動配置)、
ルートBは llm_prompt に「各部位に製造痕を最低1つ」の規範を追加。スキーマは
features maxItems 16 / count≤24 / raise/slats/rim/bolts/along を追加。

## 参照画像アーカイブと新文法 — 2026-07-09

`D:\personal_dev\gavai-henshin\samplephoto`(リポジトリ外)にユーザー生成の参照シート15枚:
- **三面図×3ヒーロー**: 銀×紺×金スペースシェリフ / マゼンタ×黒ライダー「PARADOXIS」/ 赤ポリス「PATROL UNIT 01」
- **パーツ分解図×2**(コスプレ設計図形式: 取付方法・素材ガイド付き)— 板割りの答え合わせに最適
- **ディテール接写**(兜45°・胸エンブレム・籠手ギミック)
- **素材・仕上げ仕様書×2**(カラーコード付き: 銀 #C9CDD2 / 金 #D4AF57 / 紺 #0E1422 / 発光 #1E90FF 等 —
  パレットに直接使える実測値)

**写経v2の収穫② — 白い体の真因(2026-07-09)**: アンダースーツが全レンダで白かったのは
ライティングではなくバグ。Blender 5.xの新規マテリアルは「Principled BSDF」という**名前**の
ノードを持たず `nodes.get()` が None → 設定が黙ってスキップされ、素体はデフォルト0.8グレーの
まま出荷されていた(GLBのbaseColorFactor実測で発見)。型検索(BSDF_PRINCIPLED)+生成
フォールバックへ修正し、質感もマット黒(metallic .05 / rough .85)に。教訓:
**ノードは名前でなく型で引く/材質の検証はレンダでなくエクスポート実データで行う**。

**写経v2(PATROL UNIT 01)で見つけた穴 → palette_override(2026-07-09)**:
衣装の配色は部位で変わる(ベルトは黒・手袋は黒)が、全身共通パレットでは表現不能だった。
partに `palette_override {base_surface/accent/emissive/trim}` を追加 — スーツパレットに
部分マージされ、マテリアル名は色ごとにユニーク化(armor_<zone>_<HEX>)されるので
他部位の材質を上書きしない。ルートB出力の修復レイヤも hex 検証付きで通す。
写経本体は examples/armor-blueprint.patrol-unit-01.json(11部位・パトランプ=emissive buckle、
腿ホルスター=深いbuckle、肩ストラップ=縦sash、白縁取り=rim付きaccent板)。

これを受けた新文法: **sash(斜め帯・襷)** — 肩線から逆腰へシェル上を走るストラップ。
`band_top/band_bottom/from_deg/to_deg/width_m/lift_m`、mirror=trueで**ライダーX字クロス**。
端はシェルへダイブ(取付部品として読める)。ポリス文法(肩のパトランプ・腿ホルスター・
胸バッジ)は既存の buckle/pad_dome の配置で表現可能。
残: 帯の捻れ最小化(rotation-minimizing frame)、PATROL UNIT 01 の全身写経。

## 胴の分節文法 — collar(襟甲)ほか(2026-07-10)

「胸・背が板を張って浮いている」の根治(ユーザーメモ 2026-07-09)。ルートAの胸は
**collar + デコルテ panel_step + 腹部 overlay_plate 2段(瓦)** を標準発行し、
鎖骨/胸郭/腹部が別セグメントに読める構造になった。

**collar(襟甲・ネックガード)** — `position≈0.94 / height_m / flare / curve(pull) /
center_deg / sector_deg / zone`。シェル上縁から首軸へ絞り上がる**漏斗状の襟**。
学んだこと:
- **パーツの外側に置く**: chest はローカル外側= angle 0、back は angle 180。
  内側(体側)に置くと conform で体表に潰されて消える(第1試作の失敗)
- **シェル縁をなぞるだけでは肩幅のロールバーになる**(第2試作)。`curve`(pull)で
  縁→首軸へ lerp(base=pull×0.7、top=pull×1.25)して初めて「襟」に読める
- 端は smoothstep で高さテーパ(開放端が刺さらない)。開いた帯なので Solidify 対象

背面の大型バックル(双丘に見えた)は vent_slats(放熱ルーバー)に置換。

## 蒸着モーション(.vrma)— 2026-07-09

`tools/blender/make_henshin_vrma.py` が **VRM Animation(VRMC_vrm_animation 1.0)** を生成:

```
blender --background --python tools/blender/make_henshin_vrma.py -- --out output/blueprint-armor/henshin.vrma [--stills 1]
```

- キーポーズ5つ(構え→溜め→十字受け→展開の一閃→右拳の見得、4.5秒/30fps)。
  ポーズは `world_rot()`(アーマチュア空間でボーン頭周り回転)で定義 — **軸の知見**:
  横向きの腕はXベクトルと平行なのでX回転が効かない(前へ振るのはZ回転→持ち上げはX)。
  脚の開きはY回転で左は負・右は正
- アバター非依存: どの生成スーツVRMでも再生可能(VRoid Hub / three-vrm 等のVRMA対応先)
- 54ヒューマノイドボーンマッピング+37チャンネル、~130KB。VRMベンチへ自動ミラー
- **factory-settingsリセット禁止**(ユーザープロファイルのVRMアドオンが無効化される)
- ロードマップ: ①ラボビューアでの蒸着エフェクト+VRMA同期再生 ②スーツ個性(重装=どっしり/
  俊敏=キレ)でキーポーズをパラメトリック変奏 ③Quest AR空間で呼出符→蒸着モーション再生

## VRM出力とWebカメラ・トラッキング実験 — 2026-07-08

**装着状態のVRM出力: 可能(実証済み)。** アセンブラが装甲18枚を各アンカーボーンへ
リジッドスキニング(ウェイト1.0)し、2形式を出力する:

- `<label>.skinned.glb` — スキン+アーマチュア込みGLB(three.jsで直接ボーン駆動可能)
- `<label>.vrm` — **正規のVRM 1.0**(VRMC_vrm拡張・humanoid 54ボーン)。VRMアドオン
  (Blender拡張 `vrm`)経由。未導入なら `blender --command extension install vrm --enable` 一発。
  VRM出力時は素体を `import_scene.vrm` で読み直すため `--factory-startup` を付けずに起動する
  (検証コンソールの assemble ジョブは対応済み)

CLI: `--export-skinned-glb 1 --export-vrm 1`。注意: bpy.ops の属性は遅延スタブなので
アドオン有無は hasattr では判定できない — 呼んで AttributeError を拾う。

**Webメタバース互換パス(2026-07-09)** — 「サービスで赤い箱になる」対策3点セット:
1. **VRM 0.x で出力**(`spec_version = "0.0"` に切替えてからexport)。VRM1.0(VRMC_vrm)しか
   持たないファイルは旧仕様のみ対応のサービスでパース不能=エラープレースホルダになる
2. **ポリゴン予算のデシメート**: 装甲77万trisはアバター上限を桁で超える。VRMだけ
   Decimate(collapse)で `--vrm-budget-tris`(既定9万)へ削減。GLB類はフル解像度のまま。
   実測: 33.1MB/77万tris → 10.1MB/10.9万tris
3. **メタの書き換え**(_apply_vrm_meta): 素体から継承した `onlyAuthor/再配布禁止` メタは
   サービスが**表示自体を拒否**する。allowed_user=Everyone に(ライセンスは再配布禁止のまま)
   ※VRM0エクスポータは頂点カラー(wear)を落とすためポータブル版はフラット色。ラボ内は影響なし

**MToonプロファイル適合(2026-07-09追補)** — 上記3点でも実サービス(xrift等)で
`VRMデータが見つかりません` が出た。**動くVRoid製VRMとの構造diff**で確定した残り3差分:
1. **全マテリアルを VRM/MToon に**(_mtoonify_material)。`VRM_USE_GLTFSHADER` は
   VRM0仕様上は合法だがUniVRM系実装が未対応=エラーマゼンタ(赤箱)の直接原因。
   Principledの色(wear_mix A入力)を mtoon1.pbr_metallic_roughness へ移植、
   shade=×0.55、emissiveはemission strength>0のマテリアルのみ
2. **サムネイル埋め込み**: 正面レンダを512²に縮小して vrm0.meta.texture へ。
   統計リーダ(vrmStatistics系)はサムネイル無しで例外を投げるものがある
3. **装甲18メッシュを1メッシュに結合**(skins 20→3)。VRoid構造(メッシュ3-5/skin同数)に一致
4. **UV必須**: アセンブラは高速化のため unwrap=False でパーツを組む→装甲にTEXCOORD_0が無く、
   サービスのアバター最適化(テクスチャアトラス化)が「UVアトリビュートが存在しません」で
   ハードフェイルする。結合+デシメート後の armor_suit に smart_uv を1回だけ実行して解決
検証コマンド: 動くVRMと `compare_vrm.py` 流の構造diff(shaders/meta.texture/skins/images/
プリミティブattributes)。出力VRMは自動で `<repo親>/VRM/`(git外の検証ベンチ)へミラーされる

**兜キャリブレーション(2026-07-09)** — 「首から差し替えるサイズ感」:
- WORN定数を廃し、素体の頭部bbox実測(headボーンz以上の頂点)×薄マージン
  (幅1.16/高1.22/奥1.12)で worn を導出(calibrate_helmet_to_head)
- encloseの合否は**貫通率のみ**(バイザー窓の顔=設計上のリビールが深さルールを
  永遠に満たせず1.42倍まで膨張していた)。加えて emissiveゾーン頂点(バイザー面)と
  **首ラインより下**(肩の上空を僧帽筋への貫通と誤検出する)を計測から除外
- さらに**enclose-hybrid化**: 実測でキャリブレーション後の残貫通は頬の浅い擦れ
  (≤12mm・±30-60°)だけと判明 → 粗い不適合(率>8%)のみ均等スケール、
  残りは他部位と同じ conform で局所解決。兜は頭サイズのまま(スケール1.0)収束する

**トラッキング実験(検証コンソール)**: 全身装着ジョブ完了後に「トラッキング実験」カードが出現。
- カメラ映像は**一切表示しない**(hidden videoで処理のみ)。黒キャンバスに
  **顔478点(シアン微細点)+体33点(オレンジ)+腕の骨格線**の高密度点群だけを描画
- MediaPipe Tasks Vision(CDN, FaceLandmarker+PoseLandmarker, GPU delegate)
- 3Dビューアの装着モデル(skinned GLB)の頭ボーンを顔の変換行列で、両腕
  (UpperArm/LowerArm)をポーズのworld landmarksで駆動 — 装甲はリジッドスキンで100%追従
  (構造検証済み: 前腕装甲頂点が J_Bip_L_LowerArm にウェイト1.00でバインド)
- カメラ許可はブラウザ側で必要。初回はMediaPipeのwasm+モデル(~15MB)をCDNから取得

**トラッキング v2(2026-07-08 改良)** — 「腕の向きが変・奥行き把握不足・腰固定で矛盾」への対応:
- **鏡像モード**(既定ON、チェックボックスで切替): 点群キャンバスを左右反転し、
  被写体の右腕→モデルの左腕へマッピング。鏡を見る感覚でチェックできる
- **EMA平滑化**(α=0.45): 33点のworld landmarksを指数移動平均で平滑化。
  MediaPipeのz(奥行き)はノイズが大きく、生値だと腕が前後にバタつくため
- **胴体駆動**(チェックボックスで切替): 肩線+腰線から胴のyaw/roll、背骨方向からpitchを推定し、
  Chest(0.8/0.7/0.8倍)とHips(yaw 0.3倍)に分配 — 体の傾き・ひねりが装甲ごと動く
- **肩すくめ**: 肩の上下(shrug)を J_Bip_L/R_Shoulder の rotation.z(±0.35クランプ)へ —
  肩アーマーの紐づきが見える
- **親チェーン対応 worldToLocal**: ボーン駆動をワールド回転→親の逆回転で局所化(slerp)。
  胴が回っても腕の向きが破綻しない
- ポーズモデルを lite→**full** へ(奥行き精度向上、初回DLは+6MB程度)
- **VRMダウンロードボタン**: assemble 完了時に `.vrm` が出力されていればビューア横に
  「VRMダウンロード」リンクが出現(VRoid Hub / VSeeFace / cluster 等へそのまま持ち込める)

**トラッキング v3(2026-07-09)** — 「頭に腕が刺さる」「体優先」への対応:
- **腕はバインドポーズ実測**: モデル読込時に UpperArm→LowerArm→Hand のボーン実位置から
  レスト方向を測り、`delta×bindWorldQ` の合成で駆動。T/Aポーズどちらでも破綻しない
  (旧実装は「レスト=±X(Tポーズ)」決め打ち+バインド姿勢無視が腕刺さりの原因)
- **駆動順序**: 頭→胴→肩すくめ→ `updateMatrixWorld(true)` →腕。親チェーンの行列を
  同フレームの胴回転込みで参照する
- **体優先**: 顔478点メッシュは「顔詳細」チェック(既定OFF・遅延ロード)。頭の向きは
  体ランドマークの鼻+両耳から推定(変身後はマスク=表情は不要、首の向きが分かれば十分)
- 再開時はボーンをバインドポーズへ戻してから再計測(restart-safe)

**パーツ検分ナビ(2026-07-09)**: 全身装着後、ビューア上に「全身/兜/胸/…」ボタン列が出現。
パーツを選ぶと他の装甲を隠してカメラがそのパーツへフォーカス(素体は表示のまま)。
「全身」で復帰。GLTFの多マテリアルパーツは Group(armor_X_abp)+子メッシュ(データ名)に
展開されるため、パーツ判定は**親チェーンを遡って** armor_X_abp を探す。

**3Dビューアの質感強化(2026-07-08)**: RoomEnvironment ベースの IBL(PMREM)+
ACESFilmicToneMapping(exposure 1.1)を導入。金属装甲に環境反射のグラデーションが乗り、
「プラスチックの照り」から「金属の映り込み」へ。`/vendor/examples/jsm/environments/` に
RoomEnvironment.js を vendored(three r164 ビルドと互換確認済み)。
ディレクショナル光は 1.4/0.7、環境光 0.15 に減光(IBLが主光源)。

## ルートB(Gemini実結線)— 2026-07-08 稼働開始

`compile_blueprint_llm(intent)` が **Gemini 1コール**(既定 `gemini-2.5-flash`、env `GEMINI_TEXT_MODEL` で変更可)で
思い・言葉を設計図JSONへ解釈する。ジオメトリは常に決定論ビルダー。信頼性の設計:

- **多層ガードレール**: ①方言修復(`type`→`kind`、`position_deg`→`angle_deg`、count→左右/等間隔展開、
  絶対m→割合換算)②階層修復(素のcross_section等をsilhouette/surfaceへ)③許可キー剪定
  ④数値クランプ(範囲逸脱は拒否でなく補正)⑤**兜閉鎖規範**(profile終端≤0.52で頭頂を必ず閉じる)
  ⑥欠落部位はルート A で補完 → スキーマ検証
- **失敗時は必ずルートAへフォールバック**(タイムアウト/ネットワーク/квота/JSON破損すべて)。
  route タグ(`llm:model` / `rule_fallback:理由`)が返るので観測可能。舞台の上でフォージは死なない。
- 使い方: `python tools/forge_from_text.py --text "…" --llm` / 検証コンソールの
  「生成AI解釈(ルートB)」チェックボックス。

実証: 「黄昏の空を守る誓い。琥珀色の装甲に夕陽の光…翼のように」→ Gemini が
base `#CC8800`(琥珀)+ emissive `#FFA500`(夕陽)を自ら選び、背に `wing_pair` を設計。
全身組み上げ 17/18+関節4/4 PASS。

## 体格(physique)— 言葉が体型を変える

blueprint に `physique`(torso/shoulder/limb/helmet の bulk 0.85-1.6)を追加。
アセンブラが装着スケールの幅/奥行に乗算(高さは関節スパン準拠、適合審査は従来通り)。
「重装・剛・巌」→ 戦車体型(実測 shoulder 1.54)、「俊敏・細・疾風」→ 細身(limb 0.90)。
ルートAは語彙+守護軸から自動導出、ルートBはGeminiが直接指定。

## 感情6軸 → 意匠(ルートAのマッピング)

blueprint.md の EmolgiaSeed 6軸をそのまま実装:

| 軸 | 断面/エッジ | 意匠 | 色相帯 |
| --- | --- | --- | --- |
| 高揚 exalt | rounded | crown↑・バイザー広く・emissive溝 | 黄-橙 |
| 闘志 fighting | sharp/razor | **horn_pair出現**・front_bias↑ | 赤 |
| 哀傷 sorrow | rounded/organic | クレスト後方スイープ | 青-藍 |
| 緊張 tension | sharp | 溝の本数・深さ↑・背面emissive線 | 紫-黒 |
| 守護 guard | squared | シェル厚↑・重装断面 | 緑-青緑 |
| 受容 embrace | rounded/organic | 曲線・front_bias↓ | 桃-紅 |

同じ入力は必ず同じ装甲になる(決定論)。LLMルートBは `llm_prompt(intent)` の指示文を
そのまま投げれば、スキーマ準拠のJSONが返る想定(範囲外の値はスキーマ検証で**起動拒否**)。

## メッシュ品質パス — 検品・隠れ面カリング・LOD(2026-07-09)

「いい鎧=いいメッシュ」。適合審査の隣に**ジオメトリ品質**の計測と削減を常設した:

1. **mesh_audit(検品)** — 部位ごとに退化面(面積~0)/スリバー三角形(quality<0.05)/
   零長エッジ/非多様体エッジ/境界エッジ/浮き頂点を計数し assembly JSON に記録。
   ルールより計測が先。初回実測(patrol-01): 退化4,837・スリバー55,067(12.7%、
   境界注入の細帯とconform潰れが主因 — 次の掃除パスの標的)・非多様体0
2. **cull_hidden_faces(隠れ面カリング)** — 法線+傾斜7レイのプローブが**全て**5cm以内で
   遮蔽される面だけ削除(1本でも抜ければ残す: ベント/溝/バイザー凹みは法線が開口から
   抜けるので安全)。ソリッドの内壁・板の下のシェル・スタッド底が消える。
   実測: **69.8万→43.5万tris(-37.7%)、GLB 21.1→15.4MB、レンダ無変化**。
   `--cull-hidden 0` で無効化可
3. **LODチェーン** — `--export-lods "0.45,0.15"` で `<label>.lod1.glb / .lod2.glb` を出力
   (カリング後の土台に積むので lod1=19.6万 / lod2=6.5万tris)。Quest/WebAR の複数体
   シーンはこれを配信する。assembly JSON の `lods` にパスとtris記録

4. **cleanup_mesh(退化掃除)** — dissolve_degenerate(0.12mm)+浮き頂点掃除。
   実測: 退化4,837→ほぼ0。**やってはいけない実測**: dissolve_limit(coplanar統合)は
   0.5°でもサブサーフ出力を壊す — 滑らか曲面の面間角度は~0.2°しかなく、バイザー凹みや
   襟の曲率が「平面」と誤判定されてngonの破片に潰れる(レンダで確認)。スリバー削減は
   出力後の統合ではなく**上流(境界注入バンドの幅設計)**で行うこと

教訓: bpy系モジュール(bmesh)のimport漏れはtry/exceptで静かにスキップされ「全部0」に
見える — 検品はまず検品自身の稼働をログ(CULL_FAILED/MESH_AUDIT_FAILED)で確認する。

**防御ガード(2026-07-09追補)**: カリング/掃除は設計上の凹み(発光面)を壊し得るため、
①emissive面はcull対象外+周囲2リング膨張保護 ②cleanupはemissive隣接頂点の縮退エッジを
温存 ③encloseのconformはバイザー窓(ガラスのz範囲×角度範囲+マージン)を除外。
**調査の教訓**: 「レンダが壊れた」と感じたらまず新旧GLBの実データ比較(emissive tris数・
emissiveFactor・材質値)— パトロール兜の「二葉バイザー」は4回のパイプライン修正で
ピクセル不変=パイプライン無実で、帯バイザー+眉溝+front_biasによる**ブループリント固有の
造形**だった(builder単体・runtime品質ではきれいに出る)。評価用レンダの照明忠実度
(スタジオ300Wが暗いグロスを灰に飛ばす)が次の整備候補。

**finish_override(2026-07-09)**: partごとに `finish_override {ゾーン: {metallic, roughness}}`。
黒い装甲・布・マット樹脂は「暗い色×高metallic」では作れない(空を映して銀になる)—
PARADOXISの黒 = #0E0E13 + met0.4/rough0.38(グロス黒)等。マテリアル名は色+質感で
ユニーク化(armor_<zone>_<HEX>_m<met>r<rough>)。GLBのbaseColorFactor/metallic/roughness
実測で検証済み(スタジオレンダ上は灰色に見えるがアセットは正しい — IBLビューアでは黒く出る)。

## 品質プリセットと三角形予算

| quality | SubD | 目安tris/部位 | 用途 |
| --- | --- | --- | --- |
| preview | 1 | 6-15k | Quest実機・高速確認 |
| runtime | 2 | 25-75k | Web Forgeプレビュー・展示 |
| hero | 3 | 100k+ | キービジュアル・アーカイブ映像 |

## アーキテクチャ方針 — 車輪の再発明とAIの噛ませどころ(2026-07-09)

「今の仕組みのままでいいのか」への評価。結論: **コアは独自車輪(再発明ではない)、
周辺は借りる。AIは限界費用ゼロの場所にだけ噛ませる**。

**独自価値(ここは自作が正しい)**: 「言葉→パラメトリック設計図→決定論ビルド→実測の
装着適合(体・比率・部品間)→VRM」の一気通貫は既製ツールに存在しない。LLMは設計時
1コールのみで限界費用ほぼゼロ — この構造は既に理想形で、AIメッシュ生成(Meshy/Hunyuan等)
への置換は決定論・無料・数秒という核心と相反する(胸エンブレム等の一点物のみ既定路線)。

**借りるべき車輪**: Blender標準(Subsurf/Solidify/Decimate/BVH — 既に全面活用)。
Geometry Nodesへの移植は「ビルド時間が壁になったら」のみ(現状preview 4-6分は許容)。

**AIを噛ませる価値がある箇所(いずれも都度コストほぼゼロ)**:
1. **オフライン資産ライブラリ** — 都度生成ではなく、一度だけ画像AIで作った再利用資産
   (エンブレム集・デカールシート・素材アトラス)をエンジンが合成する。テクスチャパスの
   現実的な第一歩で、限界費用ゼロのままリッチ化できる
2. **VLM品質審査員** — レンダをGeminiに見せて「かっこよさ・違和感」を採点させる
   (1コール/スーツ)。人力でやっている 生成→目視→修正 ループの自動化=回帰テストの目
3. **写経の半自動化** — 参照画像→VLM→blueprint下書き(人手転写の下ごしらえ)

## v1の対応範囲と次の一手

対応済み: 18部位すべてのロフトプリセット(right_* は left_* のミラー生成)、リング溝・子午線溝、
4マテリアルゾーン(nano_banana テクスチャパスとUV smart-projection 互換)。

features v2(参照三面図 `examples/Gemini_Generated_Image_*.png` のスーツ文法に準拠):
- `visor`(shape: band / **v** = V字バイザー)/ `chin_guard`(顎ガード)/ `crest_fin` / `horn_pair`(radius小=センサーアンテナ)
- `pec_plates`(胸筋バルジ)+ 腹部は ring_grooves 3段で分割
- `cuff_flange`(ガントレット/ブーツのフレアカフ)/ `pad_dome`(膝パッド)/ `buckle`(ベルトバックル)
- 細線エミッシブ配管 = width_deg 2前後の emissive 子午線溝

ヒーロー文法のフルセット例: `examples/armor-blueprint.hero.sample.json`(銀×青のメタル系、
ルールコンパイラが同文法を自動生成する)。ジオメトリはシルエット+ゾーン地図を担い、
参照画像レベルの塗り込みは nano_banana テクスチャパスが担う(参照三面図を
`GeminiReferenceImage` としてスタイル参照に渡せる)。

### 再現演習の記録 (2026-07-05)

参照三面図をプログラムで再現する演習を実施(`examples/armor-blueprint.galaxy-guard-repro.json`)。
この演習でエンジンに追加された表現力:

- **sector付きリング溝**(`center_deg`/`sector_deg`)— 口元ベント等の前面限定リッジ
- **汎用 bulge**(任意の角度/高さのガウス隆起)— ふくらはぎ・筋肉面
- **emissiveマテリアルの発色改善**(暗い拡散色+飽和発光でスタジオ光の白飛びを防止)

演習から意図コンパイラへ焼き込んだ文法(テキストのみで自動適用):
イヤーポッド / 口元ベント / 胸部共鳴核(発光ディスク)/ バックパック(guard>0.35)/
サイドポーチ(guard+tension>0.5)/ 二層パウルドロン / ふくらはぎバルジ / 手足の発光配管。

確認済み: `compile_blueprint('メタル系宇宙刑事。銀の装甲に…')` → 素材語「メタル/銀」で
シルバーパレットが選ばれ、全文法が乗った18部位が適合審査 17/18+関節4/4 で組み上がる。
既知の制約: ルールコンパイラの色理解は素材語(銀/黒/金)のみ。「青い光」等の自由な色指定は
LLMルート(`llm_prompt`)が担う設計。

次の一手(優先順):
1. **feature拡充** — vent_array(頬/後頭部のスリット)、blade_trim(縁の刃)、pec_bulge(胸筋の張り)、
   boot の踵/爪先分割
2. **LLMルートBの結線** — variant_selection.py の Sakura/Gemini アダプタに `llm_prompt()` を接続し、
   Web Forge の自由文入力 → blueprint 生成 → 即時3D化をAPI化(/v1/suits/forge の asset_pipeline に統合)
3. **ライン一貫性** — 1つのblueprintから18部位フルセットを生成し、Wear Build で全身審査
4. **溝リングのUVゾーン地図** — 溝ゾーンをUVアイランドへ書き出し、nano_banana プロンプト契約に連携

## 実証記録 (2026-07-05)

- `examples/armor-blueprint.sample.json` → helmet 75k tris / chest 39k / shoulder 23k、
  クリース入り滑面・バイザー発光・クレスト・パネル溝すべて成立
- 意図文「守る盾+闘志の牙+誓いの光」→ ルールコンパイラ → fighting+guard 軸 → 赤基調・角付き・
  重装断面の別デザインが自動生成(output/blueprint-armor/intent-demo/)
- テスト: tests/test_armor_blueprint.py 14件 green(スキーマ/決定論/軸抽出/純数学)

## 尖りと武装の拡張計画(2026-07-11 — 「入力した意図に沿った武装や鎧」)

現エンジンの文法(ロフト+特徴+浮き板+審査)はそのまま**武装と装飾**へ延長できる。
実装順の提案:

1. **武装モジュール(本命)** — 剣・盾・銃を第19+のモジュール群として追加。
   ジオメトリは既存文法の再利用: 刃=edge_blade の独立化+ロフト柄、
   盾=overlay_plate の大判独立化+持ち手、銃=箱ロフト+バレル+機関部ポッド。
   装着は背中(鞘=既存sashと接続)/腰ホルスター/手持ち(Hand ボーンアンカー)。
   _GEAR_WORDS が既に blade/shooter/guard を検出しているので、
   コンパイラは「言葉→武装の有無・種類」を今日の仕組みのまま導出できる
2. **クレスト/角の増幅** — exalt系は height 1.5〜2倍(既存バックログ)。
   シルエットの「尖り」が一番安く跳ねる場所
3. **設計局AIによる命名+意匠の焦点** — 解釈時に suit_name(銘)と
   focal_point(この鎧の見せ場はどこか)を返させ、焦点部位に装飾予算を集中
4. **非対称の解禁** — mirror:false の運用を広げ、片肩大型パウルドロン・
   片腕ガントレット強化など「主役の非対称」を語彙(asymmetry軸)から導出
5. **マント/布** — 静的メッシュの背面ドレープから(物理は後)。
   王・裁定者系の語彙で発火
6. **テクスチャ/エンブレム・パス** — nano_banana でエンブレム画像→デカール。
   幾何ではなく画像の領分(docs/armor-realism-candidates 参照)。
   「意味合いの尖り」の最終兵器

原則は不変: 言葉が主張した機能だけが装備になる(飾りを置かない)。
武装は _GEAR_WORDS の演繹の延長であり、スキーマ検証+適合審査を必ず通す。
