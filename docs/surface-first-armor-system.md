# Surface-first Armor System v1

## 目的
- VRM への装着を `mesh-first` ではなく `surface-first` で考える。
- AI 生成画像を UV テクスチャへ使う前提は維持する。
- 点群/ラティスは最終鎧そのものではなく、`装着の担体` として使う。

## 問題設定
- 現行の rigid armor だけで VRM fit を解くと、位置は合ってもサイズ感と量感が暴れやすい。
- 特に torso 系は `見た目の殻` が oversized になりやすく、fit 数学だけでは収まりきらない。
- webcam / 将来の mocopi を考えると、骨だけでなく `体表` を真実源に持つ必要がある。

## 用語
- `Surface Graph`
  - VRM 表面からサンプルした点群ラティス
  - 各点は `position / normal / region` を持つ
- `Skin Shell`
  - Surface Graph から少しだけ法線方向へ押し出した密着殻
  - 下地スーツ、蒸着途中、発光線、紋様の担体
- `Armor Mounts`
  - Surface Graph / body proxy から導く装着ポイント
  - rigid armor や外装パネルを載せる基準
- `Render Layers`
  - 下地スーツ、発光、紋様、外装パネル、剛体装甲などの表示層

## 基本方針
- 最終表現はハイブリッドにする。
- `surface-first` が向くもの:
  - 密着型の下地
  - 発光ライン
  - 蒸着の粒子定着
  - 身体に沿う紋様
- `mesh-first` が向くもの:
  - helmet
  - shoulder armor
  - chest/back の大型外装
  - shin / boot の硬い装甲

## データ構造
```ts
type SurfaceNode = {
  region:
    | "head"
    | "torso"
    | "left_upperarm"
    | "right_upperarm"
    | "left_forearm"
    | "right_forearm"
    | "left_thigh"
    | "right_thigh"
    | "left_shin"
    | "right_shin"
    | "left_foot"
    | "right_foot";
  position: Vector3;
  normal: Vector3;
  surfaceDelta: number;
};

type ArmorMount = {
  name: string;
  region: SurfaceNode["region"];
  position: Vector3;
  normal: Vector3;
};

type SurfaceFirstSnapshot = {
  sampleCount: number;
  density: number;
  shellOffset: number;
  nodes: SurfaceNode[];
  links: Array<{ start: Vector3; end: Vector3; region: string }>;
  mounts: ArmorMount[];
  proxies: Record<string, unknown>;
  regionCounts: Record<string, number>;
};
```

## 処理順
1. VRM の骨から canonical joints と体格指標を求める
2. VRM 表面を sample して点群を作る
3. 点群を head / torso / limbs / foot proxy に再投影して region を付ける
4. 点群法線から `Skin Shell` を生成する
5. proxy と region から `Armor Mounts` を置く
6. rigid armor は mount と fit shell を参照して装着する
7. AI 生成テクスチャは従来どおり render shell 側に貼る

## 固定するもの
- VRM 基準体
- body proxy の定義
- region 分類
- mount 名称と責務
- 既存 UV / texture パイプライン

## 即時計算するもの
- surface sample
- node normal
- shell offset
- mount 位置
- body fit の評価

## 生成 AI に任せるもの
- UV に貼る画像
- 紋章
- マテリアル感
- 表面ディテール

## デモ実装の範囲
- `viewer/body-fit` に `Surface-first Demo` パネルを追加
- 表示できるもの:
  - `Surface Graph`
  - `Skin Shell`
  - `Armor Mounts`
- 調整できるもの:
  - `Point Density`
  - `Shell Offset`
- ハーネス:
  - `window.__HENSHIN_BODY_FIT__.runSurfaceFirstDemo()`

## デモ実装の非ゴール
- 点群を直接 final armor にすること
- 三角形メッシュの完全再生成
- UV 展開の置き換え
- rigid armor 全置換

## 期待する使い方
- まず Surface Graph と Skin Shell で `どこまで身体に沿うか` を見る
- 次に Armor Mounts を見て `どこに硬い装甲を吊るすか` を決める
- 最後に rigid armor と AI texture を重ねる

## 判断
- `点群を最終鎧にする` は弱い
- `点群を装着の基盤にする` は強い
- よってこの方式は `surface-first fitting substrate` として採用する
