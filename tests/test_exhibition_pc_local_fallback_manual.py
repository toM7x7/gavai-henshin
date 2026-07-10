from pathlib import Path


def test_exhibition_pc_local_fallback_manual_covers_required_fallbacks() -> None:
    manual = Path(
        "docs/exhibition-pc-local-fallback-migration-manual-2026-05-05.md"
    ).read_text(encoding="utf-8")

    for token in {
        "mocopiなし、外部ネットなしで成立",
        "USB ADB reverse",
        "LAN fallback",
        "mocopi無しURL",
        "ネット不調時",
        "直前QAチェックリスト",
        "start_exhibition_local_stack.ps1",
        "start_quest_adb_reverse.ps1",
        "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>",
        "Web Forge -> Quest 変身 -> Replay",
        "GCP/Webサービス化は",
    }:
        assert token in manual


def test_exhibition_pc_local_fallback_manual_keeps_mocopi_optional() -> None:
    manual = Path(
        "docs/exhibition-pc-local-fallback-migration-manual-2026-05-05.md"
    ).read_text(encoding="utf-8")

    assert "mocopi無し = 失敗" in manual
    assert "mocopiは「体験向上」" in manual
    assert "mocopi不調を理由に本体験を止めません" in manual
