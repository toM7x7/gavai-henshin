from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
UI_TEXT_SOURCE_FILES = (
    "viewer/shared/exhibition-copy.js",
    "viewer/armor-forge/index.html",
    "viewer/armor-forge/forge.js",
    "viewer/quest-iw-demo/index.html",
    "viewer/quest-iw-demo/quest-demo.js",
)
MOJIBAKE_MARKERS = (
    "\u7e1d",
    "\ufffd",
    "\u8708",
    "\u9015",
    "\u87bb",
    "\u973d",
    "\u8b5a",
    "\u8b6f",
    "\u9adf",
    "\u9a55",
    "\u7e3a",
)


def read_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_ui_text_sources_do_not_contain_mojibake_markers() -> None:
    for path in UI_TEXT_SOURCE_FILES:
        text = read_text(path)
        offenders = sorted({marker for marker in MOJIBAKE_MARKERS if marker in text})
        assert offenders == [], f"{path} contains mojibake markers: {offenders}"


def test_shared_operator_copy_defines_japanese_state_color_guides() -> None:
    shared = read_text("viewer/shared/exhibition-copy.js")

    for token in {
        "準備中",
        "認識中",
        "生成完了",
        "要確認",
        "黄: 入力待ち",
        "紫: 音声",
        "青: Web生成",
        "赤: コード",
        "operatorStateLabel",
        "operatorStateColorGuide",
    }:
        assert token in shared


def test_web_forge_operator_copy_uses_japanese_status_help() -> None:
    html = read_text("viewer/armor-forge/index.html")
    js = read_text("viewer/armor-forge/forge.js")

    for token in {
        'id="forgeStatusHelp"',
        "黄: 来場者の入力待ちです。",
        "待機中 / 表面未生成 / 生成後に状態を表示",
    }:
        assert token in html

    for token in {
        '../shared/exhibition-copy.js',
        "EXHIBITION_OPERATOR_COPY.forge.submitting",
        "operatorStateLabel(state)",
        "operatorStateColorGuide(state)",
        "外装GLB",
        "基礎スーツ表示中",
        "表面読込要確認",
        "浮き・接触・背面・腰・ブーツ・連続性は生成後に採寸します。",
    }:
        assert token in js

    for token in {
        "planned only / surface not generated",
        "texture failed",
        "Mock maps are not used here.",
        "armor pending",
        "surface pending",
        "base visible",
        "base pending",
        "float/contact/back/waist/boot/continuity metrics pending",
        "表面Probe",
    }:
        assert token not in html
        assert token not in js


def test_web_forge_exhibition_mode_surfaces_priority_operator_actions() -> None:
    html = read_text("viewer/armor-forge/index.html")
    js = read_text("viewer/armor-forge/forge.js")
    css = read_text("viewer/armor-forge/styles.css")

    for token in {
        'id="exhibitionSummary"',
        'aria-label="展示モード要約"',
        'id="exhibitionCode"',
        'id="exhibitionHeight"',
        'id="exhibitionVariant"',
        'id="exhibitionQuestLink"',
        'id="replaySaveLink"',
        'id="textureQuickAction"',
        'id="textureQuickButton"',
        'id="textureQuickDetail"',
        'aria-label="表面生成クイック操作"',
        "展示モード",
        "選択variant",
        "Questで開く/試す導線",
        "Replay保存導線",
    }:
        assert token in html

    for token in {
        "function useExhibitionMode()",
        'params.get("mode") === "exhibition"',
        'params.get("exhibition") === "1"',
        "const EXHIBITION_MODE = useExhibitionMode();",
        "document.body.dataset.exhibitionMode",
        "renderExhibitionSummary",
        "selectedVariantSummaryJa",
        "const VARIANT_DISPLAY_LABELS_JA = new Map",
        '["Sleek line variant", "ライン重視"]',
        '["Bold armored variant", "装甲強調"]',
        "variantDisplayNameJa",
        "display_name_ja: variantDisplayNameJa(part, selectedKey, selectedVariant?.display_name)",
        "const variantName = firstString(record.display_name_ja, record.display_name",
        "option.textContent = variantDisplayNameJa(id, variantKey, record?.display_name);",
        'summary.textContent = key ? `自動: ${variantDisplayNameJa(part, key)}`',
        "replaySaveUrlFromQuestUrl",
        'url.searchParams.set("replayView", "mirror")',
        "setExhibitionLinkState",
        'UI.resultDetails?.removeAttribute("open")',
        'details.dataset.exhibitionPriority = "low"',
        "textureJobButtons()",
        "UI.textureQuickButton?.addEventListener",
        "Questで開く/試す",
        "Questで試してReplay保存",
    }:
        assert token in js

    for token in {
        'body[data-exhibition-mode="true"] .result-panel .exhibition-summary',
        ".exhibition-summary__stats",
        ".exhibition-actions",
        ".texture-quick-action",
        ".replay-link",
        'body[data-exhibition-mode="true"] .support-details[data-exhibition-priority="low"]',
    }:
        assert token in css


def test_web_forge_exhibition_mode_qa_keeps_links_and_mobile_layout_safe() -> None:
    html = read_text("viewer/armor-forge/index.html")
    js = read_text("viewer/armor-forge/forge.js")
    css = read_text("viewer/armor-forge/styles.css")

    assert '<section id="exhibitionSummary" class="exhibition-summary" aria-label="展示モード要約" hidden>' in html
    assert 'if (!EXHIBITION_MODE || !UI.exhibitionSummary) return;' in js
    assert 'const enabled = Boolean(code) && !stale;' in js
    assert 'UI.exhibitionSummary.hidden = false;' in js

    for token in {
        'if (UI.exhibitionCode) UI.exhibitionCode.textContent = code || "----";',
        'if (UI.exhibitionHeight) UI.exhibitionHeight.textContent = `${declaredHeightCm()}cm`;',
        "selectedVariantSummaryJa()",
        'text: enabled ? "Questで開く/試す" : "生成後にQuestで試す"',
        'text: enabled ? "Questで試してReplay保存" : "生成後にReplay保存へ"',
        'link.classList.toggle("disabled", !enabled);',
        'link.setAttribute("aria-disabled", enabled ? "false" : "true");',
        'url.searchParams.set("replayView", "mirror");',
        'const stale = UI.questLink?.dataset.stalePreview === "true";',
    }:
        assert token in js

    exhibition_css = css[css.index(".exhibition-summary[hidden]") : css.index(".result-details")]
    for token in {
        "grid-column: 1 / -1;",
        "min-width: 0;",
        ".result-panel .exhibition-summary__stats",
        "grid-template-columns: minmax(92px, 0.42fr) minmax(74px, 0.28fr) minmax(0, 1fr);",
        ".result-panel .exhibition-actions",
        "grid-template-columns: repeat(2, minmax(0, 1fr));",
        ".exhibition-actions .quest-link",
        "min-height: 44px;",
    }:
        assert token in exhibition_css
    assert "white-space: nowrap" not in exhibition_css
    assert "position: fixed" not in exhibition_css

    mobile_css = css[css.index("@media (max-width: 760px)") :]
    for token in {
        ".result-panel .exhibition-summary__stats",
        ".result-panel .exhibition-actions",
        "grid-template-columns: 1fr;",
    }:
        assert token in mobile_css

    result_strong_css = css[css.index(".result-panel strong") : css.index(".result-panel small")]
    assert "overflow-wrap: anywhere;" in result_strong_css


def test_quest_operator_copy_replaces_public_english_readouts() -> None:
    html = read_text("viewer/quest-iw-demo/index.html")
    js = read_text("viewer/quest-iw-demo/quest-demo.js")

    for token in {
        "<title>GAVAI Quest変身デモ</title>",
        "IWSDK / mocopi / Sakura AI Engine 連携",
        'aria-label="Quest没入シーン"',
        'aria-label="Quest変身デモ操作"',
        'id="operatorStateHelp"',
        "黄: 待機中です。4桁コード、マイク、VR開始の順に確認してください。",
        'aria-label="変身体験ルート状態"',
        'aria-label="Questスーツ呼び出し"',
        'aria-label="セッション状態"',
        '<span id="sessionId">セッション: 待機</span>',
        '<span id="triggerState">音声: 待機</span>',
        '<span id="equipState">変身: 待機</span>',
    }:
        assert token in html

    for token in {
        "SESSION",
        "TRIGGER",
        "EQUIP",
        "IWSDK immersive scene",
        "IW henshin demo controls",
        "New Route status",
        "Quest suit recall",
        "Session readout",
        "Sakura AI Engine bridge",
    }:
        assert token not in html

    for token in {
        '../shared/exhibition-copy.js',
        "setOperatorStateHelp",
        "EXHIBITION_OPERATOR_COPY.quest.operatorHelpListening",
        "EXHIBITION_OPERATOR_COPY.quest.operatorHelpComplete",
        "EXHIBITION_OPERATOR_COPY.quest.operatorHelpError",
        "VRを開始できません",
        "Quest VRモード利用可能",
    }:
        assert token in js

    assert "VR session could not start" not in js
