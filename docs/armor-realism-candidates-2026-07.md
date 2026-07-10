# 装甲リアリズム強化 — 事例・候補調査(2026-07-08)

「もうちょっとモデルがリアルにスマートにならないか」への調査結果。
結論: **リアリティは4層で積める**。下の層ほど安い・速い・既存パイプラインと相性が良い。
上の層ほど品質上限が高いが、決定論・低コストという本プロジェクトの철학とトレードオフになる。

## 現状のボトルネック分析

いまの装甲が「ゲームのプロトタイプ」に見え、参照三面図の「実写スーツ」に見えない理由:

1. **単色ゾーン材質** — base/accent/emissive の3色ベタ。実物スーツは擦り傷・パネル境界の
   汚れ・微細な色ムラがある(=テクスチャ不在)
2. **法線が滑らかすぎる** — Subdivision+Bevel で面は綺麗だが、微細な凹凸
   (リベット・ヘアライン・鋳造肌)がゼロ
3. ~~ビューアの照明が平板~~ → **対応済み(2026-07-08)**: RoomEnvironment IBL + ACES
   トーンマッピング導入。金属の映り込みが出るようになった

## 第0層: ビューア強化(実施済み・無料)

three.js 側の照明・トーンマッピングは最も安いリアリティ投資。

- **IBL(環境マップ)**: `RoomEnvironment` を `PMREMGenerator.fromScene` でプリフィルタし
  `scene.environment` へ。粗い面はぼけたmip、鏡面は鮮明なmipをサンプルする仕組みで、
  metalness の高い装甲に必須([Three.js Journey — Environment map](https://threejs-journey.com/lessons/environment-map)、
  [Three.js Journey — Realistic render](https://threejs-journey.com/lessons/realistic-render))
- **ACESFilmicToneMapping + exposure 1.1** — 白飛びせずハイライトが転がる
- 次の一手候補(未実施):
  - **HDRI 実写環境**([Poly Haven](https://polyhaven.com) の .hdr を RGBELoader→PMREM)。
    RoomEnvironment より情報量の多い映り込み。ファイルサイズ注意(背景に使わなければ低解像度で十分
    — [sbcode Environment Maps](https://sbcode.net/threejs/environment-maps/))
  - **Bloom(EffectComposer + UnrealBloomPass)** — エミッシブ配管・バイザーが「発光して見える」。
    glTFの `KHR_materials_emissive_strength` がbloomのヒントになる
    ([Khronos glTF PBR](https://www.khronos.org/gltf/pbr/))
  - パフォーマンス系のtipsは [100 Three.js Tips (2026)](https://www.utsubo.com/blog/threejs-best-practices-100-tips)

## 第1層: Blender側のプロシージャル微細ディテール(無料・決定論を保てる)

エンジン(armor_blueprint_builder.py)に足せる「実物らしさ」。LLM不要・決定論のまま:

- **エッジウェア(角の擦れ)**: ベベル済みエッジ頂点に Vertex Color を焼き、
  シェーダで「角だけ金属地金が覗く」2色ブレンド。Pointiness/曲率ベースで自動化可能
- **プロシージャルノイズ法線**: ノードで微細バンプ(鋳造肌・ヘアライン)。
  ジオメトリを増やさずテクスチャレスで表面情報量を上げる
- **パネルライン/デカール文法**: 業界標準は trim sheet + decal
  ([Blender Bros MaterialWorks](https://www.blenderbros.com/materialworks) は860デカール+21M組合せ、
  [Sci-fi Hard Surface Trim Sheet](https://superhivemarket.com/products/sci-fi-hard-surface-trim-sheet-texture-pack) 等)。
  本エンジンは既に溝(groove)を制御ケージに織り込む方式なので、
  **「溝の語彙を増やす」**(ボルト列・通気スリット・型番刻印風の矩形凹み)が同型の拡張
- **参考**: [Mastering Hard Surface in Blender](https://www.exp-points.com/sady-fofana-mastering-hard-surface-in-blender)

推奨度: ★★★ — 決定論哲学と完全に整合。次の実装候補の本命。

## 第2層: AIテクスチャパス(nano_banana 結線 — 設計済み未実装)

ゾーン単色 → PBRテクスチャへ。「塗りの最終品質はnano_bananaテクスチャパスが担う」設計を実行に移す層。

- **本命: nano_banana(Gemini画像)でスタイルガイド生成 → Blenderで投影/UV焼き込み**。
  既存のGemini結線・APIキーを流用できる
- 代替・参考事例:
  - [StableGen](https://github.com/sakalond/StableGen) — Blender内でStable Diffusionにより
    メッシュへ直接テクスチャ投影(オープンソース、ローカルGPU)
  - [Material Anything](https://arxiv.org/html/2411.15138v1) — 任意メッシュへPBR材質を
    拡散モデルで生成(研究、コード公開)。multi-view生成→PBR分解→UVインペイントという
    パイプライン構成は自前実装の設計図として参考になる
  - [3D AI Studio](https://www.3daistudio.com/blog/best-ai-texture-and-pbr-generators-2026) —
    既存モデルのリテクスチャ+PBRマップ一式(albedo/normal/roughness/metallic)をSaaSで
  - SDXLでシームレスPBRを作る手順: [Casey Primozic のノート](https://cprimozic.net/notes/posts/generating-textures-for-3d-using-stable-diffusion/)
- 実装の要点: 装甲は既に部位別メッシュなので **Smart UV Project → 部位ごとに
  1024pxテクスチャ → glTFに同梱** が最短。KTX2圧縮でGPUメモリ~1/10
  ([Khronos glTF PBR](https://www.khronos.org/gltf/pbr/))

推奨度: ★★★ — 品質の伸び幅が最大。「思い→色・模様」の表現力も上がる。

## 第3層: AI画像→3D生成(ヒーローパーツ/参照用 — 任意)

「一撃の見栄え」は最も高いが、決定論・数秒生成・無料という本エンジンの強みと衝突する。
**全身をこれで作る話ではなく**、(a)一点物のヒーローパーツ(胸のエンブレム、特殊武器)、
(b)品質のベンチマーク参照、として使うのが筋が良い。

- ホスト型SaaS:
  - **Meshy 6** — text/image-to-3D+PBR+トポロジ制御で最もバランス型
    ([2026比較](https://www.buildmvpfast.com/articles/best-llms-2026-guide/3d-modeling-ai)、
    [10 Best Image to 3D Tools](https://www.3daistudio.com/3d-generator-ai-comparison-alternatives-guide/best-image-to-3d-tools-2026))
  - **Tripo** — 速度とゲームレディトポロジ
  - **Rodin** — キャラクター・構造物のプレミアム品質
    ([Neural4D比較](https://www.neural4d.com/features/neural4d-vs-tripo-vs-meshy-vs-rodin)、
    [Medium比較](https://medium.com/data-science-in-your-pocket/ai-3d-model-generators-compared-tripo-ai-meshy-ai-rodin-ai-and-more-8d42cc841049))
  - いずれもヒーローアセットは人手クリーンアップ前提
- オープンソース(ローカル):
  - **[Hunyuan3D-2.1](https://github.com/tencent-hunyuan/hunyuan3d-2.1)** — 重み・学習コード完全公開、
    PBRテクスチャ合成込み。VRAM: 形状10GB / テクスチャ21GB / 両方29GB(`low_vram_mode` あり)。
    RTX 3080 12GBで形状生成は回る([README](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/README.md))
  - **TRELLIS**(Microsoft) — 技術者向け、[HuggingFaceの2026比較](https://trellis2.app/blog/best-image-to-3d-models-huggingface)

推奨度: ★☆☆(全身置換)/ ★★☆(ヒーローパーツ・参照用)

## 推奨ロードマップ

| 順 | 施策 | 層 | コスト | 効果 |
|---|---|---|---|---|
| 1 | ✅ IBL+ACES(実施済み) | 0 | 0 | 金属の映り込み |
| 2 | Bloom + HDRI差し替え | 0 | 数時間 | 発光装甲・実写環境反射 |
| 3 | エッジウェア+微細法線+溝語彙拡張 | 1 | 1-2日 | 「実物スーツの情報量」 |
| 4 | nano_banana テクスチャパス結線 | 2 | 2-3日 | 塗り・模様の最終品質 |
| 5 | (任意)Hunyuan3D/Meshyでヒーローパーツ実験 | 3 | 実験1日 | 一点物の見栄え検証 |

3と4が揃うと、参照三面図(Gemini_Generated_Image_*.png)の「実写スーツ感」に
プログラム生成のまま最接近できる見込み。
