# IW Henshin Module

更新日: 2026-04-16

## 目的

`src/henshin/iw_henshin.py` は、IWSDK/mocopi の実統合前に「声で生成を宣言し、全身アーマー蒸着を完了し、後で再生できるリプレイを残す」ための独立モジュールです。

既存の `viewer/body-fit` にはまだ直接接続していません。後続統合では、ここで出力する `body-sim.json` と `artifacts/iwsdk-deposition-replay.json` を読み込ませます。

## 構成

- `src/henshin/sakura_ai_engine.py`
  - さくらのAI Engine REST API ラッパ
  - Whisper 文字起こし: `/audio/transcriptions`
  - TTS 音声合成: `/audio/speech`
- `src/henshin/iw_henshin.py`
  - 「生成」トリガー判定
  - mocopi風フレームの `BodyFrame` 正規化
  - `run_body_sequence()` による装着完了判定
  - TTS 解説生成
  - リプレイ/イベント保存

## 最短実行

キーなしのドライラン:

```powershell
python -m henshin iw-henshin --transcript 生成 --mocopi examples/mocopi_sequence.sample.json --dry-run --session-id S-IW-DEMO
```

出力:

- `sessions/S-IW-DEMO/body-sim.json`
- `sessions/S-IW-DEMO/artifacts/iwsdk-deposition-replay.json`
- `sessions/S-IW-DEMO/artifacts/iwsdk-events.jsonl`

## さくらAI Engine設定

`.env` に後から追加します。

```dotenv
SAKURA_AI_ENGINE_TOKEN=YOUR_TOKEN_HERE
SAKURA_AI_ENGINE_BASE_URL=https://api.ai.sakura.ad.jp/v1
SAKURA_WHISPER_MODEL=whisper-large-v3-turbo
SAKURA_TTS_MODEL=zundamon
SAKURA_TTS_VOICE=normal
SAKURA_TTS_FORMAT=wav
VOICE_TRIGGER_PHRASE=生成
```

音声ファイルを使う場合:

```powershell
python -m henshin iw-henshin --audio input.wav --mocopi examples/mocopi_sequence.sample.json --session-id S-IW-LIVE
```

## 後続統合メモ

1. IWSDK 側は `iwsdk_events` と同じイベント名で bridge する。
2. mocopi 実機受信は `frames[].bones` にボーン座標を詰めて `normalize_mocopi_frames()` に渡す。
3. `viewer/body-fit` は `body-sim.json` を読めるため、最初のリプレイ表示は既存ビューア側のロード導線だけで成立する。
4. TTS が生成された場合は `replay.tts.audio_path` を UI で再生する。
