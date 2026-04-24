# 02_定義書_GCP

Version: 0.2  
用途: プロジェクトの定義・用語・スコープを固定する

---

## 1. プロジェクト名
**変身試験プラットフォーム / Henshin Trial Platform**

---

## 2. プロダクト定義
ユーザーの**感情・思い・文脈**を起点に、  
AIがスーツ案を提案し、Web上でスーツを成立させ、Quest上で変身試験を実行し、**Quest内で試験Replayまで確認できる**サービスを作る。

---

## 3. これは何のサービスか
これは「ヒーロー生成アプリ」ではない。  
これは **変身試験サービス** である。

体験者は「なりきり」をするのではなく、
- 設計されたスーツを
- 試験条件で
- 起動し
- 記録し
- 再確認する

という流れを体験する。

---

## 4. 体験の中核フロー

### 4.1 事前入力
- 思い
- 文脈
- なりたい像
- 守りたいもの
- 気分や価値観タグ

### 4.2 スーツ成立
- AIが方向性を解釈
- PartPlan を提案
- Web上で素体 + パーツを成立させる
- SuitManifest を保存

### 4.3 Quest試験
- 適合確認
- 仮組み
- 掛け声
- 蒸着完了

### 4.4 Quest Replay
- 主要イベントの再生
- ステップごとの見返し
- 解説付きReplay

---

## 5. 中核思想

### 5.1 AIは設計者であって、全自動鍛造機ではない
AIの役割は次に限定する。
- Emotion / Context の構造化
- DesignVector の生成
- PartPlan の提案
- Blueprint / Emblem / 解説文の生成

AIが直接フル3D完成品を毎回本番採用することは、MVPでは目指さない。

### 5.2 3Dは成立性優先
3Dは **素体 + パーツ + 表層差分** で成立させる。  
MVPでの完全自動3D生成は本線にしない。

### 5.3 ReplayはQuest主
Replay は「あとでWebで見る」のではなく、**試験直後にQuest内で見返せる**ことを主目標にする。

---

## 6. スコープ

### 6.1 MVPに含む
- Suit Forge Web
- Firebase Auth による operator 認証
- SuitManifest の保存
- Cloud SQL / Firestore / Cloud Storage による管理
- Quest 変身試験
- Quest Replay
- LLMによる PartPlan 提案

### 6.2 MVPに含まない
- WebXR 本編
- 毎回完全自動フル3D生成
- Webカム変身本編
- 自動SE / 自動BGM本格生成
- 一般ユーザー公開向けフルSNS共有機能

---

## 7. 論理サービス定義

### 7.1 Emotion / Context Analyzer
入力テキストを EmotionProfile に落とす。

### 7.2 Design Vector Generator
EmotionProfile からデザイン方向性を作る。

### 7.3 Part Planner
DesignVector をもとに PartPlan YAML/JSON を出す。

### 7.4 Resolver
PartPlan を PartCatalog に照らして実在構成へ落とす。

### 7.5 Suit Forge Web
素体 + パーツを組み、保存する。

### 7.6 Suit Registry API
Suit / Session / Replay / Asset を保存・配信する。

### 7.7 Quest Transform Runtime
変身試験を実行する。

### 7.8 Quest Replay Runtime
ReplayScript に基づいて Quest 内再生を行う。

---

## 8. 用語定義

### EmotionProfile
感情・態度・価値観を構造化したもの。

### DesignVector
EmotionProfile をスーツ設計方向に変換したもの。

### PartPlan
LLMが提案する抽象構成案。

### PartCatalog
実在するパーツ辞書。

### SuitManifest
スーツの正本。Questが読む。

### Morphotype
体躯プロファイル。Quest適合に使う。

### TransformSession
1回の試験の記録単位。

### ReplayScript
Quest Replay の再生指示。

---

## 9. 3Dモデルの定義

### 9.1 3レイヤー構造
#### Base Layer
- 密着スーツ
- ベース身体
- グローブ基礎
- ブーツ基礎

#### Armor Layer
- ヘルメット
- 胸部
- 肩
- 前腕
- ベルト
- 脚部
- 背部ユニット

#### Surface Layer
- エンブレム
- 発光ライン
- 材質プリセット
- テクスチャ差分

### 9.2 ソケット規格
- head_socket
- chest_socket
- shoulder_l_socket
- shoulder_r_socket
- arm_l_socket
- arm_r_socket
- belt_socket
- leg_l_socket
- leg_r_socket
- back_socket
- emblem_socket

---

## 10. 成果物定義

### 10.1 正本
- SuitManifest
- TransformSession
- ReplayScript

### 10.2 副生成物
- merged.glb
- preview.png
- blueprint.png
- emblem.png
- replay export (将来)

---

## 11. 進め方の原則

### 11.1 仕様先行で固定するもの
- Schema
- Socket naming
- PartCatalog
- State machine

### 11.2 実装で後から詰めるもの
- 画面の細かなUI表現
- 演出の質感
- MCP自動化の範囲
- 3D粗生成の研究線

---

## 12. 一文でいうと

**このプロジェクトは、感情と文脈を起点にスーツを設計し、Quest上でその変身試験とReplayを成立させるための基盤である。**
