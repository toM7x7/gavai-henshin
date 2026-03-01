# ID Policy（Gate 0 固定）

最終更新: 2026-03-01  
適用範囲: `henshin` CLI / `SuitSpec v0.2` / `Morphotype v0.2`

## 1. ID種別とフォーマット

1. `SessionID`
   - 形式: `S-YYYYMMDD-XXXX`
   - 正規表現: `^S-[0-9]{8}-[A-Z0-9]{4}$`
   - 生成元: `generate_session_id()`

2. `SuitID`
   - 形式: `VDA-{SERIES}-{ROLE}-{REV}-{SEQ}`
   - 正規表現: `^VDA-[A-Z0-9]+-[A-Z0-9]+-[0-9]{2}-[0-9]{4}$`
   - 生成元: `generate_suit_id(series, role, rev, seq)`

3. `ApprovalID`
   - 形式: `APV-########`
   - 正規表現: `^APV-[0-9]{8}$`
   - 生成元: `generate_approval_id()`

4. `MorphotypeID`
   - 形式: `MTP-########`
   - 正規表現: `^MTP-[0-9]{8}$`
   - 生成元: `generate_morphotype_id()`

実装参照: `src/henshin/ids.py`

## 2. 採番ルール（確定）

1. `SERIES` / `ROLE`
   - 英数字以外は除去し、英大文字へ正規化して採用する。
   - 除去後に空文字になる値は不正として拒否する。

2. `REV`
   - 範囲は `00..99`（CLI引数 `--rev`）。
   - 同一シリーズ/同一ロールで互換性のある更新は `REV` を維持し、`SEQ` を進める。
   - 互換性を壊す更新は `REV` を増やす。

3. `SEQ`
   - 範囲は `0000..9999`（CLI引数 `--seq`）。
   - 運用上は `0001` 開始を標準とする。
   - 同一 `SERIES/ROLE/REV` 内で単調増加させる。

4. `ApprovalID` / `MorphotypeID`
   - 8桁数字の疑似乱数で発行する（現段階は仮運用）。
   - 重複検知時は再発行する。

## 3. 発行フロー（CLI）

1. `new-session`
   - `SessionID` を発行し、`sessions/<SessionID>/` を作成する。

2. `draft`
   - 指定がなければ `SuitID` / `ApprovalID` / `MorphotypeID` を自動発行する。
   - `suitspec.json` と `morphotype.json` へ同じID系を記録する。

## 4. 運用メモ（暫定）

1. 現在は中央採番サービス未導入のため、`SuitID` の `SEQ` 進行はCLI利用者が管理する。
2. `ApprovalID` は監査サービス連携時に外部払い出しへ切り替える想定（フォーマットは維持）。
3. 将来の自動重複検知は `sessions/` 横断インデックスで実装する。
