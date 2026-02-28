# gavai-henshin

Loreを基点に、Blueprintを実行可能にするための **SIM-first プロトタイピング基盤** です。  
現段階は「技術検証デモを高速に回す」ことを目的に、仮案ルールで構築しています。

## 目的
- Track A: Suit Forge（生成/3D試着の土台）
- Track B: Transform Stage（B->C->D->蒸着->封印の状態遷移）
- Archive: セッション成果物の保存（物証化）

## 現在の実装範囲
- 仮案IDルールと設定ファイル
- `SuitSpec` / `Morphotype` のスキーマ（`schemas/`）
- 生成ドラフト出力（JSON）
- Gemini API経由の画像生成（Blueprint/Emblem）
- Gemini API経由の部位別画像生成（module単位）
- プロトコル状態遷移（happy/refused）
- セッション保存（ログ/要約/ダミー成果物）
- 右腕ドック装着シミュレーション（PoC参照統合）
- 全身セグメント装着シミュレーション（PoC汎化）
- CLI実行 (`henshin`)
- 単体テスト（標準ライブラリ `unittest`）

## ディレクトリ
- `src/henshin/`: 実行コード
- `schemas/`: JSON Schema
- `config/`: 仮案ルール
- `examples/`: サンプルJSON
- `docs/`: 実行準備ドキュメント
- `docs/roadmap.md`: ロードマップ
- `docs/progress-log.md`: 進捗ログ
- `docs/rightarm-integration.md`: 右腕PoC統合メモ
- `sessions/`: デモ出力先（Git管理は `.gitkeep` のみ）

## クイックスタート
```powershell
$env:PYTHONPATH="src"
python -m henshin demo --mode happy
python -m henshin demo --mode refused --refusal-code AUDIT_MISMATCH
python -m henshin validate --kind suitspec --path examples/suitspec.sample.json
python -m unittest discover -s tests -v
```

### Gemini APIキー設定
```powershell
$env:GEMINI_API_KEY="YOUR_API_KEY"
```

または、プロジェクト直下の `.env` に設定（CLIが自動読込）:
```dotenv
GEMINI_API_KEY=YOUR_API_KEY
```

## CLI
```powershell
python -m henshin new-session
python -m henshin draft --session-id S-20260228-A1B2 --series AXIS --role OP
python -m henshin demo --mode happy
python -m henshin validate --kind morphotype --path examples/morphotype.sample.json
python -m henshin generate-image --kind blueprint --suitspec examples/suitspec.sample.json
python -m henshin generate-parts --suitspec examples/suitspec.sample.json --dry-run
python -m henshin generate-parts --suitspec examples/suitspec.sample.json --update-suitspec
python -m henshin simulate-rightarm --input examples/rightarm_sequence.sample.json --output sessions/rightarm-sim.json
python -m henshin simulate-body --input examples/body_sequence.sample.json --output sessions/body-sim.json
```

## GitHub運用
- CI: `.github/workflows/ci.yml`（unittest実行）
- ライセンス: MIT
- コントリビュート規約: `CONTRIBUTING.md`

## 次の実装候補
1. SuitSpecサンプルを増やしてモジュール差し替え検証を追加
2. Armory Viewer（Unity）連携I/O仕様の固定
3. mocopi入力をMorphotype推定に変換する前処理実装
