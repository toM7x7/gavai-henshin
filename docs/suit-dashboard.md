# Suit Dashboard 手順

更新日: 2026-03-01

## 1. 目的

`viewer/suit-dashboard` は次を1画面で行うためのUIです。

1. スーツ（SuitSpec）選択
2. 部位別パーツ画像の生成実行（CLI API経由）
3. 各部位を個別3Dで立体確認
4. 必要なら Body Fit Viewer に遷移して全身確認

## 2. 起動

```powershell
$env:PYTHONPATH="src"
python -m henshin serve-dashboard --port 8010
```

開くURL:

- `http://localhost:8010/viewer/suit-dashboard/`

## 3. 基本フロー

1. `SuitSpec` を選び `読込`
2. `生成モード` を選ぶ
   - `mesh_uv`: 展開図寄り（メッシュ貼り込み向け）
   - `concept`: 単体イメージ寄り
3. `Fallback Dir` を指定（既存画像活用時）
4. 対象パーツを選択して `生成実行`
5. 右側カードで各部位を個別3D確認

## 4. 推奨設定（既存画像活用）

1. `Fallback Dir`: `sessions/S-20260228-JBJK/artifacts/parts`
2. `既存画像優先`: ON
3. `SuitSpecへ反映`: ON
4. `生成モード`: `mesh_uv`

## 5. Mesh Relief

- `Mesh Relief` はテクスチャ明暗を使った疑似凹凸です。
- 目安は `0.04〜0.06`。
- 0にすると凹凸を無効化できます。

## 6. 補足

1. ダッシュボード生成は内部で `python -m henshin generate-parts` を呼び出します。
2. APIキー未設定でも `fallback-dir` があれば生成を継続できます。
3. 本実装は「部位別確認最適化」が目的で、最終メッシュ（GLB/FBX）統合は次フェーズです。

## 2026-03-02 �ǉ�
- �w�i�𔒊�ɓ���
- �p�[�c�J�[�h�� 3D / UV �^�u��ǉ��iUV���C���d��j
- UV��ʎw�W�iUV��L�� / �e�N�X�`���[�U�� / �O���[�U�� / ��v�x�j��\��
- �S�̃^�u�� �{�f�B�O�i ��ǉ��i���_�����j
- prefer fallback �̏����l��OFF�ɕύX�imesh_uv������D��j
