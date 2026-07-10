"""Intent -> ArmorBlueprint v1 compiler.

Two front doors, one contract:

1. ``compile_blueprint(intent, axes=...)`` — deterministic rule compiler.
   No LLM, no network, milliseconds. The EmolgiaSeed 6-axis mapping from
   blueprint.md (高揚/闘志/哀傷/緊張/守護/受容) drives silhouette, edges,
   grooves, features, and palette.
2. ``llm_prompt(intent)`` — the exact instruction string for an LLM
   (Gemini / Sakura) to emit a richer blueprint JSON. The LLM only writes
   the small design JSON; geometry is always built by the deterministic
   Blender builder, so token cost stays one short call per suit.

Either path validates against schemas/armor-blueprint.v1.schema.json via
``validate_against_schema(payload, "armor-blueprint")``.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .validators import validate_against_schema

AXES = ("exalt", "fighting", "sorrow", "tension", "guard", "embrace")

# 感情軸ごとの色相帯 (blueprint.md A-1.1 の6軸を踏襲)
_AXIS_PALETTE = {
    "exalt": {"base_surface": "#3A2A12", "accent": "#F2B441", "emissive": "#FFD75E", "trim": "#7A5A28"},
    "fighting": {"base_surface": "#2A1216", "accent": "#C7323C", "emissive": "#FF4D3A", "trim": "#6E2430"},
    "sorrow": {"base_surface": "#131A2E", "accent": "#4A5C8C", "emissive": "#5A8CFF", "trim": "#2C3A5E"},
    "tension": {"base_surface": "#171224", "accent": "#6C4A9C", "emissive": "#B45AFF", "trim": "#3A2C56"},
    "guard": {"base_surface": "#12262A", "accent": "#3E8C7A", "emissive": "#3AE8C7", "trim": "#26504A"},
    "embrace": {"base_surface": "#2A1620", "accent": "#D486A0", "emissive": "#FF9EC7", "trim": "#6E3A50"},
}

_INTENT_KEYWORDS = {
    "exalt": ("高揚", "昂", "興奮", "光", "輝", "希望", "上昇"),
    "fighting": ("闘", "戦", "攻", "牙", "刃", "怒", "突破", "征"),
    "sorrow": ("哀", "悲", "喪", "静", "雨", "涙", "鎮魂"),
    "tension": ("緊張", "警戒", "研ぎ", "張り", "鋭敏", "監視"),
    "guard": ("守", "護", "盾", "防", "壁", "支え", "庇"),
    "embrace": ("受容", "包", "抱", "赦", "慈", "和らぎ", "共"),
}

"""NOTE: the default set is the FULL authored body (right limbs mirror from
left at assembly). The old 4-module default is why route-A suits shipped
with bare backs, waists and legs for weeks — the builder silently filled
missing parts with featureless defaults."""
_DEFAULT_MODULES = ("helmet", "chest", "back", "waist",
                    "left_shoulder", "right_shoulder",
                    "left_upperarm", "left_forearm", "left_hand",
                    "left_thigh", "left_shin", "left_boot")


def axes_from_intent(intent: str) -> dict[str, float]:
    """Very light keyword scoring; explicit axes always beat this."""
    scores = {axis: 0.0 for axis in AXES}
    text = intent or ""
    for axis, words in _INTENT_KEYWORDS.items():
        for word in words:
            scores[axis] += 0.34 * len(re.findall(re.escape(word), text))
    top = max(scores.values())
    if top <= 0.0:
        scores["guard"] = 0.5  # 無指定は守護寄りの中立 — 制度の色
    return {axis: min(1.0, value) for axis, value in scores.items()}


def _dominant(axes: dict[str, float]) -> tuple[str, str]:
    ordered = sorted(AXES, key=lambda a: axes.get(a, 0.0), reverse=True)
    return ordered[0], ordered[1]


# 色語 -> (大面プレート用の落ち着いた base色, 発光用の明色 glow)
_COLOR_WORDS: dict[tuple[str, ...], tuple[str, str]] = {
    ("赤", "紅", "レッド", "朱", "緋", "紅蓮"): ("#7A1E22", "#FF4D3A"),
    ("青", "蒼", "ブルー", "藍", "群青"): ("#24406E", "#38B8FF"),
    ("碧", "緑", "グリーン", "翠", "萌黄"): ("#1E5A46", "#3AE8C7"),
    ("紫", "菫", "バイオレット", "royal"): ("#3A2456", "#B45AFF"),
    ("橙", "オレンジ", "琥珀"): ("#7A3A12", "#FF9A3A"),
    ("桃", "ピンク", "紅梅", "薔薇"): ("#6E2A44", "#FF9EC7"),
    ("黄", "イエロー"): ("#8A6A1E", "#FFD75E"),
    ("金", "黄金", "ゴールド"): ("#8A6A1E", "#FFD75E"),
    ("白", "白銀", "ホワイト", "純白"): ("#C8CDD9", "#EAF2FF"),
    ("黒", "漆黒", "ブラック", "闇"): ("#15181E", "#7E8CA0"),
    ("銀", "シルバー", "メタル", "鋼", "鉄", "白金"): ("#B4BAC6", "#DDE4EE"),
}
_GLOW_WORDS = ("光", "発光", "輝", "灯", "グロー", "ライト", "燐光", "残光", "煌")
_METAL_WORDS = ("メタル", "銀", "シルバー", "鋼", "鉄", "白金", "金", "黄金", "ゴールド", "白銀", "黒", "漆黒", "白", "純白")

# 形状語 -> シルエットの動き
_SHAPE_WORDS: dict[str, tuple[str, ...]] = {
    "sharp": ("鋭", "尖", "刃", "エッジ", "シャープ", "鋭角", "斬"),
    "round": ("丸", "曲線", "柔", "なめらか", "円", "球", "優"),
    "heavy": ("重", "厚", "剛", "硬", "鎧", "重装", "堅", "巌", "壁"),
    "slim": ("細", "軽", "スリム", "繊細", "華奢", "薄", "俊敏"),
    "spike": ("棘", "トゲ", "スパイク", "牙", "刺", "鋸", "茨"),
    "horn": ("角", "ツノ", "ホーン"),
    "wing": ("翼", "羽", "ウイング", "翅", "飛"),
    "crown": ("王", "冠", "クラウン", "帝", "覇", "王者"),
    "insect": ("昆虫", "甲殻", "蟲", "インセクト", "節足", "蟷螂", "甲虫"),
    "beast": ("獣", "狼", "竜", "龍", "ビースト", "猛", "野"),
    "speed": ("速", "疾", "流線", "スピード", "俊", "風", "翔"),
}


def _intent_rng(intent: str) -> random.Random:
    """Deterministic per-suit PRNG: same text -> same suit, different text ->
    a different suit even at the same dominant axis. This is what stops two
    inputs from collapsing to the same individual."""
    seed = int.from_bytes(hashlib.sha256((intent or "seed").encode("utf-8")).digest()[:8], "big")
    return random.Random(seed)


def _detect_shapes(intent: str) -> set[str]:
    txt = intent or ""
    return {tag for tag, words in _SHAPE_WORDS.items() if any(w in txt for w in words)}


# 機能→装備の演繹(行間を埋める文法): ヒーロー像の役割・能力の言葉から、
# その機能が物理的に要求する小物を導く。飾りは置かない — すべての小物は
# 言葉が主張した能力の痕跡である
_GEAR_WORDS: dict[str, tuple[str, ...]] = {
    "patrol": ("警", "巡査", "ポリス", "パトロール", "治安", "刑事", "捜査", "police"),
    "blade": ("剣", "刀", "斬", "ブレード", "太刀", "侍", "剣士", "抜刀"),
    "shooter": ("銃", "砲", "シューター", "狙撃", "ガン", "弾"),
    "flight": ("飛", "翔", "ジェット", "スラスタ", "飛行", "浮遊"),
    "scan": ("探", "調査", "スキャン", "センサー", "観測", "分析", "追跡"),
    "rescue": ("救", "レスキュー", "消防", "救助", "救急", "命を"),
    "comms": ("通信", "指令", "無線", "コール", "司令"),
    "stealth": ("隠密", "忍", "ステルス", "潜入", "静寂"),
}


def _detect_gear(intent: str) -> set[str]:
    txt = intent or ""
    return {tag for tag, words in _GEAR_WORDS.items() if any(w in txt for w in words)}


def _gear_for(functions: set[str], module: str, rng: random.Random) -> list[dict[str, Any]]:
    """Append the gear a module carries for the claimed capabilities."""
    out: list[dict[str, Any]] = []
    if not functions:
        return out
    limb_side = 90 if module.startswith("left_") else -90 if module.startswith("right_") else 0

    if "patrol" in functions or "rescue" in functions:
        if module.endswith("_shoulder"):
            out.append({"kind": "buckle", "position": 0.88, "angle_deg": 0, "width_m": 0.06,
                        "height_m": 0.022, "depth_m": 0.014, "zone": "emissive"})
        if module == "back":
            out.append({"kind": "buckle", "position": 0.84, "angle_deg": 180, "width_m": 0.12,
                        "height_m": 0.034, "depth_m": 0.02, "zone": "emissive"})
    if ("patrol" in functions or "shooter" in functions) and module.endswith("_thigh"):
        out.append({"kind": "buckle", "position": 0.55, "angle_deg": limb_side, "width_m": 0.05,
                    "height_m": 0.1, "depth_m": 0.034, "zone": "base_surface"})
    if ("patrol" in functions or "shooter" in functions or "rescue" in functions) and module == "waist":
        for a in (46, -46):
            out.append({"kind": "buckle", "position": 0.5, "angle_deg": a, "width_m": 0.045,
                        "height_m": 0.055, "depth_m": 0.024,
                        "zone": "emissive" if "rescue" in functions else "base_surface"})
    if "blade" in functions:
        if module == "back":  # 鞘の帯 + 腰後ろの留め具
            out.append({"kind": "sash", "band_top": 0.9, "band_bottom": 0.24, "from_deg": -22,
                        "to_deg": 30, "width_m": 0.055, "lift_m": 0.012, "zone": "accent"})
            out.append({"kind": "buckle", "position": 0.3, "angle_deg": 155, "width_m": 0.045,
                        "height_m": 0.11, "depth_m": 0.03, "zone": "trim"})
        if module.endswith("_forearm"):  # 受けの籠手を厚く
            out.append({"kind": "overlay_plate", "position": 0.6, "t_span": 0.28,
                        "angle_deg": limb_side, "arc_deg": 60, "lift_m": 0.012,
                        "corner": 0.2, "rim": 0.9, "bolts": True, "zone": "accent"})
    if "flight" in functions:
        if module.endswith("_shin"):  # ふくらはぎのスラスタ
            out.append({"kind": "buckle", "position": 0.72, "angle_deg": 180, "width_m": 0.05,
                        "height_m": 0.07, "depth_m": 0.032, "zone": "trim"})
            out.append({"kind": "vent_slats", "position": 0.6, "t_span": 0.12, "angle_deg": 180,
                        "arc_deg": 28, "slats": 3, "depth": 0.6, "zone": "emissive"})
        if module == "back":  # 姿勢制御フィン
            out.append({"kind": "edge_blade", "position": 0.6, "t_span": 0.4, "angle_deg": 35,
                        "height_m": 0.04, "sweep": 0.7, "mirror": True, "zone": "accent"})
    if "scan" in functions:
        if module.endswith("_forearm"):
            out.append({"kind": "buckle", "position": 0.6, "angle_deg": -limb_side or 90,
                        "width_m": 0.03, "height_m": 0.05, "depth_m": 0.016, "zone": "emissive"})
        if module == "helmet":
            for a in (58, -58):
                out.append({"kind": "pad_dome", "position": 0.62, "angle_deg": a, "width_m": 0.024,
                            "height_m": 0.024, "depth_m": 0.012, "zone": "emissive"})
    if "rescue" in functions and module == "back":  # 背のタンク対
        for a in (152, -152):
            out.append({"kind": "pad_dome", "position": 0.5, "angle_deg": a, "width_m": 0.07,
                        "height_m": 0.11, "depth_m": 0.045, "zone": "trim"})
    if "comms" in functions:
        if module == "helmet":
            out.append({"kind": "horn_pair", "length": 0.45, "curve": 0.12, "radius_m": 0.004,
                        "zone": "accent"})
        if module.endswith("_forearm"):
            out.append({"kind": "buckle", "position": 0.72, "angle_deg": limb_side, "width_m": 0.028,
                        "height_m": 0.04, "depth_m": 0.014, "zone": "emissive"})
    if "stealth" in functions and module.endswith("_forearm"):
        out.append({"kind": "edge_blade", "position": 0.55, "t_span": 0.4, "angle_deg": limb_side,
                    "height_m": 0.028, "sweep": 0.8, "zone": "trim"})
    return out


def _colors_in_order(intent: str) -> list[tuple[str, str]]:
    """Colours mentioned, in order of first appearance -> [(base, glow), ...]."""
    txt = intent or ""
    found: list[tuple[int, str, str]] = []
    for words, (base, glow) in _COLOR_WORDS.items():
        pos = min((txt.find(w) for w in words if w in txt), default=-1)
        if pos >= 0:
            found.append((pos, base, glow))
    found.sort(key=lambda x: x[0])
    return [(b, g) for _, b, g in found]


def _shift(hex_color: str, rng: random.Random, amt: float = 0.06) -> str:
    """Nudge each channel by ±amt so no two suits share an exact swatch."""
    text = hex_color.lstrip("#")
    out = []
    for i in range(0, 6, 2):
        v = int(text[i:i + 2], 16) / 255.0
        v = max(0.0, min(1.0, v * (1.0 + rng.uniform(-amt, amt))))
        out.append(f"{int(round(v * 255)):02X}")
    return "#" + "".join(out)


def _resolve_palette(intent: str, primary: str, secondary: str, blend: float,
                     rng: random.Random) -> dict[str, str]:
    """Colour words are authoritative; the axis palette only fills gaps. Every
    channel gets a small deterministic jitter so palettes never repeat exactly."""
    pal = dict(_AXIS_PALETTE[primary])
    if blend > 0.35:
        pal["accent"] = _AXIS_PALETTE[secondary]["accent"]
    colors = _colors_in_order(intent)
    txt = intent or ""
    has_metal = any(w in txt for w in _METAL_WORDS)
    glow_named = any(w in txt for w in _GLOW_WORDS)
    if colors:
        base0, glow0 = colors[0]
        if has_metal:
            pal["base_surface"] = base0  # metal words set the plate tone
        else:
            pal["base_surface"] = base0
        # emissive: a glow-flagged colour, else the last colour's glow
        pal["emissive"] = (colors[-1][1] if (glow_named or len(colors) > 1) else glow0)
        if len(colors) > 1:
            pal["accent"] = colors[1][0]
        else:
            pal["accent"] = glow0 if not has_metal else pal.get("accent", "#8792A6")
        pal.setdefault("trim", "#C8CDD9")
    return _ensure_palette_contrast({k: _shift(v, rng) for k, v in pal.items()})


def _luma(hex_color: str) -> float:
    t = str(hex_color).lstrip("#")
    try:
        r, g, b = int(t[0:2], 16), int(t[2:4], 16), int(t[4:6], 16)
    except (ValueError, IndexError):
        return 0.5
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def _ensure_palette_contrast(pal: dict[str, str]) -> dict[str, str]:
    """Legibility guard for BOTH routes: white-on-white / red-on-red kills
    every panel line and plate edge. If base and accent read as the same
    tone, force the accent to the opposite pole."""
    base = pal.get("base_surface")
    accent = pal.get("accent")
    if base and accent and abs(_luma(base) - _luma(accent)) < 0.22:
        pal = dict(pal)
        pal["accent"] = "#1B2431" if _luma(base) > 0.5 else "#EDF0F4"
    return pal


def _jit_profile(base: list, rng: random.Random, amt: float) -> list:
    """Perturb a loft profile's scale values so the body curve itself varies."""
    out = []
    for t, sc in base:
        j = max(0.35, min(1.15, sc + rng.uniform(-amt, amt)))
        out.append([round(t, 3), round(j, 3)])
    return out


# silhouette families — the SHELL SHAPE itself must diverge per concept,
# not just the colours and the bolt-on features (chuuni-6 lesson)
_HELMET_PROFILES = {
    "dome": [[0.0, 0.66], [0.18, 0.9], [0.42, 1.0], [0.66, 0.98], [0.86, 0.84], [1.0, 0.46]],
    "wedge": [[0.0, 0.6], [0.22, 0.84], [0.52, 0.96], [0.78, 1.0], [0.93, 0.78], [1.0, 0.4]],
    "jaw": [[0.0, 0.76], [0.13, 0.99], [0.4, 1.0], [0.7, 0.94], [0.9, 0.76], [1.0, 0.5]],
}
_TORSO_PROFILES = {
    "hero": [[0.0, 0.82], [0.32, 0.94], [0.62, 1.0], [1.0, 0.9]],
    "vee": [[0.0, 0.7], [0.35, 0.88], [0.72, 1.0], [1.0, 0.97]],
    "barrel": [[0.0, 0.9], [0.38, 1.0], [0.75, 0.98], [1.0, 0.84]],
}

# per-part default loft profiles (mirror the builder presets so we can jitter)
_PART_PROFILE = {
    "helmet": _HELMET_PROFILES["dome"],
    "torso": _TORSO_PROFILES["hero"],
    "limb": [[0.0, 0.8], [0.25, 0.94], [0.55, 1.0], [1.0, 0.84]],
}


def _slug(intent: str) -> str:
    digest = 0
    for ch in intent or "":
        digest = (digest * 131 + ord(ch)) % (36 ** 4)
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    out = ""
    for _ in range(4):
        digest, rem = divmod(digest, 36)
        out = chars[rem] + out
    return out


def _suit_dna(axes: dict[str, float], moves: set[str], rng: random.Random) -> dict[str, Any]:
    """Continuous per-suit silhouette genes. Word tags bias the ranges; the RNG
    fills the rest, so every distinct intent gets a distinct body."""
    fight, tens, exalt = axes["fighting"], axes["tension"], axes["exalt"]
    guard, sorrow, embr = axes["guard"], axes["sorrow"], axes["embrace"]
    # numeric cross-section (1.4 sharp .. 3.6 boxy), continuous not bucketed
    cross = 2.0
    cross += 0.5 * fight + 0.5 * tens + 0.7 * guard - 0.5 * (exalt + embr)
    if "sharp" in moves or "insect" in moves or "beast" in moves:
        cross -= 0.8
    if "round" in moves:
        cross += 0.9
    if "heavy" in moves:
        cross += 0.7
    cross = max(1.4, min(3.6, cross + rng.uniform(-0.35, 0.35)))
    spikiness = 0.4 * (fight + tens) + (0.6 if "spike" in moves or "beast" in moves else 0) \
        + (0.3 if "insect" in moves else 0) + rng.uniform(-0.1, 0.25)
    return {
        "cross": round(cross, 2),
        "edge": ("razor" if ("sharp" in moves or fight > 0.6 or "beast" in moves)
                 else "organic" if ("round" in moves or embr > 0.5 or sorrow > 0.6)
                 else "machined"),
        "spikiness": max(0.0, spikiness),
        "crest_scale": round(min(1.7, rng.uniform(0.75, 1.4) * (1.25 if ("crown" in moves or "wing" in moves) else 1.0)
                             * (1.15 if exalt > 0.5 else 1.0)), 3),
        "crest_count": (3 if ("crown" in moves and rng.random() < 0.7) else
                        2 if (exalt > 0.5 or "crown" in moves or rng.random() < 0.35) else 1),
        "wing": ("wing" in moves) or (exalt > 0.55 and rng.random() < 0.4),
        "shoulder_flare": round(0.12 + 0.18 * guard + (0.12 if "heavy" in moves else 0)
                               + rng.uniform(-0.04, 0.08), 3),
        "groove_rows": (4 if "heavy" in moves else 3 if (tens > 0.4 or rng.random() < 0.5) else 2),
        "asymmetry": round((0.12 if "beast" in moves else 0.0) + tens * rng.uniform(0.0, 0.14), 3),
        "antennae": ("insect" in moves) or (tens > 0.4) or rng.random() < 0.4,
        "profile_jit": 0.10 + 0.06 * tens + (0.05 if "beast" in moves else 0),
    }


def _plate_style(axes: dict[str, float], moves: set[str], rng: random.Random) -> str:
    """Pick the plate-architecture family — the structural concept of the suit.
    This is what makes two intents read as DIFFERENT SUITS, not recolors."""
    if "insect" in moves or ("slim" in moves and axes["tension"] > 0.3):
        return "lamellar"    # many narrow lens plates, segmented carapace
    if "heavy" in moves or axes["guard"] > 0.55:
        return "bulwark"     # few LARGE square slabs, fortress look
    if "speed" in moves or "wing" in moves or "slim" in moves:
        return "aero"        # long low panels + swept edge blades
    if "beast" in moves or axes["fighting"] > 0.55:
        return "brutal"      # chunky offset plates + spikes
    return rng.choice(["hero", "hero", "lamellar", "aero"])


def _plates_for(style: str, region: str, rng: random.Random,
                depth_zone: str = "accent") -> list[dict[str, Any]]:
    """Emit overlay_plate/edge_blade stacks for a body region in a style."""
    out: list[dict[str, Any]] = []

    def plate(**kw):
        base = {"kind": "overlay_plate", "zone": kw.pop("zone", "base_surface")}
        base.update(kw)
        # every stamped plate gets a reinforced rim; square-ish plates are
        # likelier to show corner fasteners — manufacturing evidence
        base.setdefault("rim", round(rng.uniform(0.45, 0.9), 2))
        if rng.random() < (0.55 if base.get("corner", 0.5) < 0.5 else 0.25):
            base.setdefault("bolts", True)
        out.append(base)

    if region == "chest":
        if style == "bulwark":
            # transcription finding: pecs mid-set + stacked ab BANDS (wide/thin)
            plate(position=0.68, t_span=0.26, angle_deg=rng.uniform(22, 32),
                  arc_deg=rng.uniform(42, 50), lift_m=rng.uniform(0.014, 0.02),
                  corner=rng.uniform(0.25, 0.4), mirror=True, zone="base_surface")
            for i, tp in enumerate((0.4, 0.28, 0.17)):
                plate(position=tp, t_span=rng.uniform(0.1, 0.13), angle_deg=0,
                      arc_deg=rng.uniform(80, 92), lift_m=0.013, corner=0.2,
                      zone=("accent" if i == 1 else "base_surface"))
        elif style == "lamellar":
            n = rng.randint(3, 5)
            for i in range(n):
                plate(position=0.2 + 0.62 * i / max(1, n - 1), t_span=rng.uniform(0.1, 0.16),
                      angle_deg=0, arc_deg=rng.uniform(70, 100),
                      lift_m=rng.uniform(0.006, 0.012), corner=rng.uniform(0.75, 1.0))
        elif style == "aero":
            plate(position=0.62, t_span=0.5, angle_deg=rng.uniform(16, 26), arc_deg=rng.uniform(30, 45),
                  lift_m=rng.uniform(0.006, 0.01), corner=rng.uniform(0.6, 0.9), mirror=True)
        elif style == "brutal":
            plate(position=0.68, t_span=0.34, angle_deg=rng.uniform(20, 32), arc_deg=rng.uniform(45, 65),
                  lift_m=rng.uniform(0.014, 0.024), corner=rng.uniform(0.15, 0.45), mirror=True)
            plate(position=0.28, t_span=0.2, angle_deg=0, arc_deg=rng.uniform(60, 85),
                  lift_m=rng.uniform(0.01, 0.018), corner=0.3)
        else:  # hero
            plate(position=0.7, t_span=0.3, angle_deg=rng.uniform(18, 30), arc_deg=rng.uniform(38, 55),
                  lift_m=rng.uniform(0.01, 0.016), corner=rng.uniform(0.4, 0.7), mirror=True)
            plate(position=0.28, t_span=0.22, angle_deg=0, arc_deg=rng.uniform(70, 95),
                  lift_m=rng.uniform(0.008, 0.014), corner=rng.uniform(0.3, 0.6))
    elif region == "shoulder":
        if style == "lamellar":
            for i in range(rng.randint(2, 3)):
                plate(position=0.3 + 0.25 * i, t_span=0.16, angle_deg=0, arc_deg=rng.uniform(110, 150),
                      lift_m=0.008 + 0.004 * i, corner=rng.uniform(0.7, 1.0))
        elif style == "bulwark":
            plate(position=0.55, t_span=0.42, angle_deg=0, arc_deg=rng.uniform(120, 155),
                  lift_m=rng.uniform(0.014, 0.022), corner=rng.uniform(0.1, 0.3))
        elif style == "aero":
            out.append({"kind": "edge_blade", "position": 0.6, "t_span": 0.5,
                        "angle_deg": 90, "height_m": rng.uniform(0.03, 0.05),
                        "sweep": rng.uniform(0.4, 0.8), "zone": "accent"})
        else:
            plate(position=0.6, t_span=0.32, angle_deg=0, arc_deg=rng.uniform(100, 140),
                  lift_m=rng.uniform(0.01, 0.018), corner=rng.uniform(0.3, 0.7))
    elif region == "limb":
        if style == "aero":
            out.append({"kind": "edge_blade", "position": 0.5, "t_span": rng.uniform(0.45, 0.65),
                        "angle_deg": 90, "height_m": rng.uniform(0.025, 0.045),
                        "sweep": rng.uniform(0.5, 0.9), "zone": "accent"})
        elif style == "lamellar":
            for i in range(2):
                plate(position=0.35 + 0.34 * i, t_span=0.18, angle_deg=0, arc_deg=rng.uniform(60, 85),
                      lift_m=0.006, corner=rng.uniform(0.75, 1.0))
        elif style in ("bulwark", "brutal"):
            plate(position=0.55, t_span=0.36, angle_deg=0, arc_deg=rng.uniform(75, 105),
                  lift_m=rng.uniform(0.01, 0.016), corner=rng.uniform(0.1, 0.4))
        else:
            plate(position=0.55, t_span=0.3, angle_deg=0, arc_deg=rng.uniform(60, 85),
                  lift_m=rng.uniform(0.007, 0.012), corner=rng.uniform(0.4, 0.7))
    elif region == "helmet":
        # cheek guards: mirrored side plates below the visor line
        plate(position=0.34, t_span=0.2, angle_deg=rng.uniform(52, 68), arc_deg=rng.uniform(34, 50),
              lift_m=rng.uniform(0.006, 0.011),
              corner=(0.2 if style in ("bulwark", "brutal") else rng.uniform(0.6, 0.95)), mirror=True)
        if style == "lamellar":
            plate(position=0.62, t_span=0.12, angle_deg=180, arc_deg=rng.uniform(90, 130),
                  lift_m=0.006, corner=0.9)
    elif region == "waist":
        # ergonomics: the pelvis flexes, so the guard is SEGMENTS, not a tub —
        # rear faulds (hip drape) + side skirts, each its own overlapping plate
        plate(position=0.5, t_span=rng.uniform(0.38, 0.48), angle_deg=180,
              arc_deg=rng.uniform(95, 115), lift_m=rng.uniform(0.008, 0.012),
              corner=0.25, taper=round(rng.uniform(-0.3, -0.15), 2), zone="base_surface")
        plate(position=0.5, t_span=rng.uniform(0.3, 0.4), angle_deg=rng.uniform(90, 100),
              arc_deg=rng.uniform(36, 46), lift_m=rng.uniform(0.009, 0.013),
              corner=0.3, taper=round(rng.uniform(-0.3, -0.2), 2), mirror=True, zone="base_surface")
    if region == "shoulder" and style != "lamellar":
        # 肩びら: articulation leaves under the pauldron dome — the shoulder
        # is the fastest joint on the body, one rigid cup cannot follow it
        for i in range(2):
            plate(position=0.30 - 0.13 * i, t_span=0.14, angle_deg=0,
                  arc_deg=rng.uniform(128, 152), lift_m=0.008 + 0.005 * i,
                  corner=0.35, zone=("accent" if i == 1 else "base_surface"))
    return out


def _details_for(style: str, region: str, rng: random.Random,
                 axes: dict[str, float]) -> list[dict[str, Any]]:
    """Micro-detail grammar: stamped panel steps, machined vent louvres and
    fastener rows. This layer kills the 'smooth toy' look — every suit shows
    manufacturing evidence, denser for guard/tension-heavy words."""
    out: list[dict[str, Any]] = []
    density = 0.55 + 0.45 * max(axes["guard"], axes["tension"], axes["fighting"])

    def maybe(pr: float) -> bool:
        return rng.random() < pr * density

    heavy_raise = 0.7 if style in ("bulwark", "brutal") else 0.5
    if region == "helmet":
        out.append({"kind": "vent_slats", "position": round(rng.uniform(0.23, 0.29), 3),
                    "t_span": 0.11, "angle_deg": 0, "arc_deg": round(rng.uniform(30, 42), 1),
                    "slats": rng.randint(3, 4), "depth": 0.55, "zone": "trim"})
        if maybe(0.95):
            out.append({"kind": "panel_step", "position": round(rng.uniform(0.42, 0.5), 3),
                        "t_span": round(rng.uniform(0.22, 0.3), 2),
                        "angle_deg": round(rng.uniform(78, 92), 1),
                        "arc_deg": round(rng.uniform(44, 56), 1),
                        "raise": round(rng.uniform(0.4, 0.6), 2), "mirror": True})
        if maybe(0.8):
            out.append({"kind": "rivet_row", "position": round(rng.uniform(0.56, 0.66), 3),
                        "angle_deg": round(rng.uniform(88, 100), 1), "arc_deg": 22,
                        "count": 3, "mirror": True, "zone": "trim"})
    elif region == "chest":
        if maybe(1.0):
            out.append({"kind": "panel_step", "position": round(rng.uniform(0.68, 0.76), 3),
                        "t_span": round(rng.uniform(0.2, 0.28), 2),
                        "angle_deg": round(rng.uniform(30, 40), 1),
                        "arc_deg": round(rng.uniform(28, 38), 1),
                        "raise": round(rng.uniform(0.45, 0.65), 2), "mirror": True})
        if maybe(0.9):
            out.append({"kind": "vent_slats", "position": round(rng.uniform(0.56, 0.64), 3),
                        "t_span": 0.15, "angle_deg": round(rng.uniform(84, 92), 1),
                        "arc_deg": round(rng.uniform(20, 26), 1), "slats": 3,
                        "depth": 0.6, "mirror": True, "zone": "trim"})
        if maybe(0.85):
            out.append({"kind": "rivet_row", "position": 0.93, "angle_deg": 0,
                        "arc_deg": round(rng.uniform(96, 120), 1),
                        "count": rng.randint(5, 8), "zone": "trim"})
    elif region == "back":
        out.append({"kind": "panel_step", "position": 0.55,
                    "t_span": round(rng.uniform(0.4, 0.5), 2), "angle_deg": 0,
                    "arc_deg": round(rng.uniform(40, 50), 1),
                    "raise": round(heavy_raise + rng.uniform(-0.05, 0.1), 2)})
        if maybe(0.9):
            out.append({"kind": "vent_slats", "position": round(rng.uniform(0.58, 0.68), 3),
                        "t_span": 0.16, "angle_deg": round(rng.uniform(18, 26), 1),
                        "arc_deg": 20, "slats": 4, "depth": 0.6, "mirror": True, "zone": "trim"})
        if maybe(0.7):
            out.append({"kind": "rivet_row", "position": 0.3, "angle_deg": 0,
                        "arc_deg": 90, "count": 5, "zone": "trim"})
    elif region == "waist":
        if maybe(0.8):
            out.append({"kind": "rivet_row", "position": 0.52,
                        "angle_deg": round(rng.uniform(24, 34), 1), "arc_deg": 26,
                        "count": 3, "mirror": True, "zone": "trim"})
    elif region == "shoulder":
        if maybe(0.95):
            out.append({"kind": "panel_step", "position": round(rng.uniform(0.68, 0.78), 3),
                        "t_span": round(rng.uniform(0.28, 0.36), 2), "angle_deg": 0,
                        "arc_deg": round(rng.uniform(130, 160), 1),
                        "raise": round(rng.uniform(0.5, 0.7), 2)})
        if maybe(0.8):
            out.append({"kind": "rivet_row", "position": round(rng.uniform(0.28, 0.38), 3),
                        "angle_deg": 0, "arc_deg": round(rng.uniform(110, 140), 1),
                        "count": 5, "zone": "trim"})
    elif region == "limb":
        if maybe(0.9):
            out.append({"kind": "panel_step", "position": round(rng.uniform(0.52, 0.62), 3),
                        "t_span": round(rng.uniform(0.3, 0.4), 2),
                        "angle_deg": 90, "arc_deg": round(rng.uniform(60, 80), 1),
                        "raise": round(rng.uniform(0.4, 0.6), 2)})
        if maybe(0.6):
            out.append({"kind": "vent_slats", "position": round(rng.uniform(0.26, 0.34), 3),
                        "t_span": 0.11, "angle_deg": 90, "arc_deg": 24,
                        "slats": 3, "depth": 0.5, "zone": "trim"})
        if maybe(0.6):
            out.append({"kind": "rivet_row", "position": round(rng.uniform(0.14, 0.2), 3),
                        "angle_deg": 0, "arc_deg": 90, "count": 4, "zone": "trim"})
    elif region == "hand":
        if maybe(0.8):
            out.append({"kind": "rivet_row", "position": round(rng.uniform(0.65, 0.75), 3),
                        "angle_deg": 0, "arc_deg": 60, "count": 4, "zone": "trim"})
    elif region == "boot":
        out.append({"kind": "panel_step", "position": 0.35, "t_span": 0.3,
                    "angle_deg": 0, "arc_deg": round(rng.uniform(70, 82), 1),
                    "raise": round(rng.uniform(0.4, 0.6), 2)})
        if maybe(0.7):
            out.append({"kind": "rivet_row", "position": 0.55, "angle_deg": 0,
                        "arc_deg": 84, "count": 4, "zone": "trim"})
    return out


def _physique(axes: dict[str, float], moves: set[str], rng: random.Random) -> dict[str, float]:
    """Worn-size bulk: heavy words make a bruiser, slim/speed words a sprinter.
    Width/depth only — the fit audit still keeps every plate off the body."""
    heavy = 1.0 if "heavy" in moves else 0.0
    slim = 1.0 if ("slim" in moves or "speed" in moves) else 0.0
    g = axes["guard"]

    def clamp(v, lo, hi):
        return round(max(lo, min(hi, v)), 3)

    return {
        "torso_bulk": clamp(1.0 + 0.22 * g + 0.2 * heavy - 0.12 * slim + rng.uniform(-0.04, 0.06), 0.85, 1.45),
        "shoulder_bulk": clamp(1.0 + 0.3 * g + 0.28 * heavy + (0.15 if "crown" in moves else 0)
                               - 0.1 * slim + rng.uniform(-0.05, 0.1), 0.85, 1.6),
        "limb_bulk": clamp(1.0 + 0.12 * g + 0.18 * heavy - 0.15 * slim + rng.uniform(-0.04, 0.06), 0.85, 1.4),
        "helmet_bulk": clamp(1.0 + 0.06 * heavy - 0.04 * slim + rng.uniform(-0.03, 0.04), 0.9, 1.25),
    }


def compile_blueprint(
    intent: str,
    axes: dict[str, float] | None = None,
    modules: tuple[str, ...] | list[str] = _DEFAULT_MODULES,
    palette: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Intent -> blueprint. Same text -> same suit (deterministic PRNG), but
    different text yields a genuinely different individual: word nuance and an
    intent-seeded RNG jitter the silhouette, features, grooves and palette so
    two inputs never collapse to the same armor. No LLM in this path."""
    resolved_axes = {a: max(0.0, min(1.0, float((axes or {}).get(a, 0.0)))) for a in AXES}
    if axes is None:
        resolved_axes = axes_from_intent(intent)
    primary, secondary = _dominant(resolved_axes)
    p = resolved_axes[primary]
    s = resolved_axes[secondary]

    rng = _intent_rng(intent)
    moves = _detect_shapes(intent)
    dna = _suit_dna(resolved_axes, moves, rng)
    style = _plate_style(resolved_axes, moves, rng)
    edge = dna["edge"]
    base_cross = dna["cross"]

    def jit(x, spread):
        return round(x + rng.uniform(-spread, spread), 3)

    def jit0(x, spread):  # jitter but never below zero (bounded fields)
        return round(max(0.0, x + rng.uniform(-spread, spread)), 3)

    def part_cross(bias=0.0):
        return round(max(1.4, min(3.6, base_cross + bias + rng.uniform(-0.25, 0.25))), 2)

    def rows_grooves(depth, zone_pref="accent"):
        n = dna["groove_rows"]
        span = [0.72, 0.5, 0.32, 0.18][:n]
        return [{"position": jit(pos, 0.03), "width": round(rng.uniform(0.012, 0.02), 3),
                 "depth": round(depth * rng.uniform(0.85, 1.05), 3),
                 "zone": ("emissive" if (i == 0 and resolved_axes["exalt"] > 0.4) else zone_pref)}
                for i, pos in enumerate(span)]

    groove_depth = round(0.32 + 0.3 * resolved_axes["tension"] + rng.uniform(-0.05, 0.1), 3)
    pipe = {"width_deg": round(rng.uniform(1.8, 2.6), 2), "depth": 0.5, "zone": "emissive"}
    asym = dna["asymmetry"]

    # ---- silhouette families: the shell SHAPE diverges per concept ------
    if "sharp" in moves or "speed" in moves or "insect" in moves:
        helm_profile = _HELMET_PROFILES["wedge"]      # 後頭部へ流れる
    elif "heavy" in moves or resolved_axes["guard"] > 0.5 or base_cross > 2.6:
        helm_profile = _HELMET_PROFILES["jaw"]        # 顎の張った箱型
    else:
        helm_profile = _HELMET_PROFILES[rng.choice(("dome", "dome", "wedge", "jaw"))]
    if "heavy" in moves or resolved_axes["guard"] > 0.55:
        torso_profile = _TORSO_PROFILES["barrel"]
    elif "slim" in moves or "speed" in moves or resolved_axes["tension"] > 0.45:
        torso_profile = _TORSO_PROFILES["vee"]
    else:
        torso_profile = _TORSO_PROFILES[rng.choice(("hero", "hero", "vee", "barrel"))]

    # ---- helmet ---------------------------------------------------------
    helm_bias = -0.4  # helmets hug the skull: pull toward rounded
    helmet_features: list[dict[str, Any]] = [
        {"kind": "visor", "shape": "v",
         "v_dip": jit(0.06 + 0.08 * resolved_axes["fighting"], 0.02),
         "band_bottom": 0.48, "band_top": jit(0.68 + 0.06 * resolved_axes["tension"], 0.03),
         "wrap_deg": round(110 + 30 * resolved_axes["exalt"] + rng.uniform(-8, 12), 1)},
        {"kind": "chin_guard", "flare": jit(0.10 + 0.08 * resolved_axes["guard"], 0.03),
         "top": 0.40, "wrap_deg": round(108 + rng.uniform(-6, 10), 1)},
        {"kind": "pad_dome", "position": 0.5, "angle_deg": round(96 + asym * 40, 1),
         "width_m": 0.045, "height_m": 0.045, "depth_m": 0.014, "zone": "accent"},
        {"kind": "pad_dome", "position": 0.5, "angle_deg": -96,
         "width_m": 0.045, "height_m": 0.045, "depth_m": 0.014, "zone": "accent"},
    ]
    # crest(s): count and shape vary per suit
    for c in range(dna["crest_count"]):
        spread = 0.0 if dna["crest_count"] == 1 else (c - (dna["crest_count"] - 1) / 2) * 0.16
        helmet_features.append({
            "kind": "crest_fin",
            "length": round(min(0.9, max(0.2, (0.34 + 0.2 * resolved_axes["exalt"]) * dna["crest_scale"]) * (1 - abs(spread))), 3),
            "height": round(min(0.55, max(0.16, (0.14 + 0.16 * resolved_axes["exalt"] + 0.1 * resolved_axes["fighting"]) * dna["crest_scale"])), 3),
            "sweep": round(max(-1.0, min(1.0, jit(0.45 + 0.4 * resolved_axes["sorrow"], 0.12))), 3),
            "thickness_m": round(rng.uniform(0.008, 0.013), 4), "zone": "accent"})
    if dna["antennae"]:
        helmet_features.append({"kind": "horn_pair", "length": jit(0.3 + 0.12 * resolved_axes["tension"], 0.06),
                                "curve": round(rng.uniform(0.15, 0.4), 2), "radius_m": 0.005, "zone": "accent"})
    if "horn" in moves or "beast" in moves or resolved_axes["fighting"] > 0.5:
        helmet_features.append({"kind": "horn_pair",
                                "length": jit(0.2 + 0.22 * resolved_axes["fighting"], 0.06),
                                "curve": round(rng.uniform(0.5, 0.85), 2),
                                "radius_m": round(rng.uniform(0.016, 0.026), 4), "zone": "accent"})
    if dna["spikiness"] > 0.9:  # thorn crown
        helmet_features.append({"kind": "spike_row", "position": jit(0.78, 0.03),
                                "count": rng.randint(3, 6), "arc_deg": round(rng.uniform(90, 160), 1),
                                "length_m": round(rng.uniform(0.03, 0.055), 3), "radius_m": 0.009,
                                "pitch_deg": round(rng.uniform(30, 70), 1), "zone": "accent"})

    helm_grooves = [{"position": jit(0.42, 0.03), "width": 0.014, "depth": groove_depth, "zone": "accent"},
                    {"position": jit(0.30, 0.02), "width": 0.012, "depth": 0.5, "center_deg": 0, "sector_deg": 70, "zone": "accent"},
                    {"position": jit(0.24, 0.02), "width": 0.012, "depth": 0.5, "center_deg": 0, "sector_deg": 56, "zone": "accent"}]
    helm_merid = [{"angle_deg": round(52 + rng.uniform(-8, 8), 1), "width_deg": 3.5, "depth": groove_depth, "zone": "accent"},
                  {"angle_deg": round(-52 + rng.uniform(-8, 8), 1), "width_deg": 3.5, "depth": groove_depth, "zone": "accent"}]
    if resolved_axes["tension"] > 0.4 or "insect" in moves:
        helm_merid.append({"angle_deg": 180, "width_deg": 4.0, "depth": 0.55, "zone": "emissive"})

    parts: list[dict[str, Any]] = []
    for module in modules:
        if module == "helmet":
            parts.append({
                "module": "helmet",
                "silhouette": {
                    "cross_section": part_cross(helm_bias),
                    "crown_height": jit0(0.04 + 0.1 * resolved_axes["exalt"] + 0.04 * resolved_axes["fighting"], 0.02),
                    "front_bias": jit(0.04 + 0.14 * resolved_axes["fighting"] - 0.06 * resolved_axes["embrace"], 0.03),
                    "profile": _jit_profile(helm_profile, rng, dna["profile_jit"]),
                },
                "surface": {"edge_style": edge, "ring_grooves": helm_grooves,
                            "meridian_grooves": helm_merid, "rim_trim": True},
                "features": helmet_features + _plates_for(style, "helmet", rng)
                            + _details_for(style, "helmet", rng, resolved_axes),
            })
        elif module in ("chest", "back"):
            features = []
            if module == "chest":
                features.append({"kind": "v_core", "width_deg": jit(14 + 12 * resolved_axes["exalt"], 3),
                                 "apex": 0.22, "top": jit(0.55 + 0.15 * p, 0.05)})
                features.append({"kind": "pec_plates",
                                 "strength": jit(0.08 + 0.08 * max(p, resolved_axes["guard"]), 0.02),
                                 "lobe_offset_deg": round(30 + rng.uniform(-4, 6), 1), "center": 0.7})
                features.append({"kind": "pad_dome", "position": 0.74, "angle_deg": 0,
                                 "width_m": round(rng.uniform(0.048, 0.062), 3), "height_m": 0.055,
                                 "depth_m": 0.016, "zone": "emissive"})
                # 胴の分節(2026-07-09メモ): 首周りの襟甲 + デコルテ段差 + 腹部の瓦。
                # 板を張った胴ではなく、鎖骨/胸郭/腹部が別セグメントに読める構造。
                # 襟はパーツの外側(chest=前面 angle 0)に置く — 内側(180)は体に埋まる
                features.append({"kind": "collar", "position": 0.94,
                                 "height_m": round(0.05 + 0.04 * resolved_axes["guard"], 3),
                                 "flare": 0.25, "center_deg": 0,
                                 "sector_deg": round(190 + rng.uniform(0, 25), 1),
                                 "zone": "accent"})
                features.append({"kind": "panel_step", "position": 0.87, "t_span": 0.1,
                                 "angle_deg": 0, "arc_deg": jit(150, 15), "raise": 0.45})
                for ab_t in (0.30, 0.44):
                    features.append({"kind": "overlay_plate", "position": ab_t,
                                     "t_span": 0.1, "angle_deg": 0, "arc_deg": jit(120, 12),
                                     "lift_m": 0.007, "taper": 0.15, "corner": 0.5})
            if module == "back" and (dna["wing"]):
                features.append({"kind": "wing_pair", "span_m": round(0.22 + 0.12 * resolved_axes["exalt"], 3),
                                 "rise_m": round(0.14 + 0.1 * resolved_axes["exalt"], 3),
                                 "sweep": round(rng.uniform(0.4, 0.7), 2),
                                 "droop": round(rng.uniform(0.05, 0.25), 2), "zone": "accent"})
            elif module == "back" and resolved_axes["guard"] > 0.35:
                # 双丘に見えた大型バックルをやめ、放熱ルーバー(バックパック的)へ
                features.append({"kind": "vent_slats", "position": 0.6, "t_span": 0.18,
                                 "angle_deg": 180, "arc_deg": 70, "slats": 4, "depth": 0.6})
            if module == "back":
                # 襟甲の背面側 — backパーツの外側は angle 180。胸側の襟と左右で
                # 重なり、首を一周する分節(瓦)になる
                features.append({"kind": "collar", "position": 0.94,
                                 "height_m": round(0.06 + 0.04 * resolved_axes["guard"], 3),
                                 "flare": 0.3, "center_deg": 180,
                                 "sector_deg": round(170 + rng.uniform(0, 20), 1),
                                 "zone": "accent"})
            if module == "chest":
                features += _plates_for(style, "chest", rng)
            elif rng.random() < 0.7:
                features += _plates_for(style, "chest", rng)[:1]
            features += _details_for(style, module, rng, resolved_axes)
            parts.append({
                "module": module,
                "silhouette": {"cross_section": part_cross(0.4 if resolved_axes["guard"] > 0.3 else 0.0),
                               "profile": _jit_profile(torso_profile, rng, dna["profile_jit"] * 0.7)},
                "surface": {
                    "edge_style": edge,
                    "shell_thickness_m": round(0.009 + 0.008 * resolved_axes["guard"], 4),
                    "ring_grooves": rows_grooves(groove_depth),
                    "meridian_grooves": [
                        {"angle_deg": round(40 + rng.uniform(-6, 6), 1), "width_deg": 3.0, "depth": groove_depth, "zone": "accent"},
                        {"angle_deg": round(-40 + rng.uniform(-6, 6), 1), "width_deg": 3.0, "depth": groove_depth, "zone": "accent"},
                        dict(pipe, angle_deg=14), dict(pipe, angle_deg=-14),
                    ],
                },
                "features": features,
            })
        elif module == "waist":
            wf = [{"kind": "buckle", "position": 0.5, "angle_deg": 0,
                   "width_m": round(rng.uniform(0.06, 0.08), 3), "height_m": 0.05, "depth_m": 0.02, "zone": "accent"}]
            if resolved_axes["guard"] + resolved_axes["tension"] > 0.5:
                wf += [{"kind": "buckle", "position": 0.45, "angle_deg": a,
                        "width_m": 0.05, "height_m": 0.05, "depth_m": 0.022, "zone": "base_surface"} for a in (55, -55)]
            wf += _plates_for(style, "waist", rng)
            wf += _details_for(style, "waist", rng, resolved_axes)
            parts.append({"module": "waist", "silhouette": {"cross_section": part_cross(0.4)},
                          "surface": {"edge_style": edge,
                                      "ring_grooves": [{"position": 0.5, "width": 0.03, "depth": 0.3, "zone": "trim"}]},
                          "features": wf})
        elif module.endswith("_shin"):
            sf = [{"kind": "pad_dome", "position": 0.88, "angle_deg": 0,
                   "width_m": 0.055, "height_m": 0.06, "depth_m": 0.022, "zone": "accent"},
                  {"kind": "bulge", "angle_deg": 180, "position": 0.62,
                   "strength": jit(0.13, 0.03), "width_deg": 46, "width": 0.18}]
            if dna["spikiness"] > 0.7:
                sf.append({"kind": "spike_row", "position": 0.5, "angle_deg": 180,
                           "count": rng.randint(2, 4), "arc_deg": 60, "length_m": round(rng.uniform(0.03, 0.05), 3),
                           "radius_m": 0.01, "pitch_deg": 20, "zone": "accent"})
            sf += _plates_for(style, "limb", rng)
            sf += _details_for(style, "limb", rng, resolved_axes)
            parts.append({"module": module,
                          "silhouette": {"cross_section": part_cross(),
                                         "profile": _jit_profile(_PART_PROFILE["limb"], rng, dna["profile_jit"] * 0.6)},
                          "surface": {"edge_style": edge,
                                      "ring_grooves": [{"position": jit(0.45, 0.03), "width": 0.02, "depth": groove_depth, "zone": "accent"}],
                                      "meridian_grooves": [dict(pipe, angle_deg=0)]},
                          "features": sf})
        elif module.endswith("_forearm") or module.endswith("_boot"):
            flange_pos = 0.9 if module.endswith("_forearm") else 0.85
            ff = [{"kind": "cuff_flange", "position": flange_pos, "width": round(rng.uniform(0.05, 0.07), 3),
                   "flare": jit(0.14 + 0.1 * resolved_axes["guard"], 0.03), "zone": "accent"}]
            if module.endswith("_forearm") and dna["spikiness"] > 0.85:
                ff.append({"kind": "spike_row", "position": 0.75, "angle_deg": 180, "count": 3, "arc_deg": 50,
                           "length_m": 0.035, "radius_m": 0.009, "pitch_deg": 10, "zone": "accent"})
            ff += _plates_for(style, "limb", rng)
            ff += _details_for(style, "boot" if module.endswith("_boot") else "limb", rng, resolved_axes)
            parts.append({"module": module,
                          "silhouette": {"cross_section": part_cross(),
                                         "profile": _jit_profile(_PART_PROFILE["limb"], rng, dna["profile_jit"] * 0.6)},
                          "surface": {"edge_style": edge,
                                      "ring_grooves": [{"position": jit(0.4, 0.03), "width": 0.02, "depth": groove_depth,
                                                        "zone": "emissive" if resolved_axes["exalt"] > 0.35 else "accent"}]},
                          "features": ff})
        elif module.endswith("_shoulder"):
            sf = [{"kind": "cuff_flange", "position": 0.16, "width": 0.07,
                   "flare": round(min(0.38, 0.14 + 0.4 * dna["shoulder_flare"] + rng.uniform(-0.02, 0.04)), 3),
                   "zone": "accent"}]
            if dna["spikiness"] > 0.75:
                sf.append({"kind": "spike_row", "position": 0.55, "angle_deg": 0,
                           "count": rng.randint(2, 4), "arc_deg": round(rng.uniform(60, 120), 1),
                           "length_m": round(rng.uniform(0.03, 0.06), 3), "radius_m": 0.011,
                           "pitch_deg": round(rng.uniform(20, 60), 1), "zone": "accent"})
            sf += _plates_for(style, "shoulder", rng)
            sf += _details_for(style, "shoulder", rng, resolved_axes)
            parts.append({"module": module,
                          "silhouette": {"cross_section": part_cross(),
                                         "crown_height": jit0(0.08 + 0.06 * dna["shoulder_flare"], 0.02)},
                          "surface": {"edge_style": edge,
                                      "ring_grooves": [{"position": 0.5, "width": 0.02, "depth": groove_depth, "zone": "accent"}]},
                          "features": sf})
        else:
            grooves = [{"position": jit(0.55, 0.04), "width": 0.02, "depth": groove_depth,
                        "zone": "emissive" if resolved_axes["exalt"] > 0.35 else "accent"}]
            region = "hand" if module.endswith("_hand") else "limb"
            limb_features = _details_for(style, region, rng, resolved_axes)
            if region == "limb" and rng.random() < 0.6:
                limb_features += _plates_for(style, "limb", rng)[:1]
            if module.endswith(("_upperarm", "_thigh")):
                # articulation ring at the joint end — segments read as
                # "this armor can actually bend", the ergonomic tell
                limb_features.append({"kind": "cuff_flange", "position": 0.12,
                                      "width": round(rng.uniform(0.045, 0.06), 3),
                                      "flare": jit(0.12, 0.03), "zone": "accent"})
            parts.append({"module": module,
                          "silhouette": {"cross_section": part_cross(),
                                         "crown_height": jit0(0.1 * resolved_axes["fighting"], 0.02),
                                         "profile": _jit_profile(_PART_PROFILE["limb"], rng, dna["profile_jit"] * 0.6)},
                          "surface": {"edge_style": edge, "ring_grooves": grooves,
                                      "meridian_grooves": [dict(pipe, angle_deg=0)]},
                          "features": limb_features})

    # 機能→装備: capabilities the words claimed leave their traces as gear
    gear = _detect_gear(intent)
    if gear:
        for part in parts:
            part["features"] = (list(part.get("features") or [])
                                + _gear_for(gear, str(part["module"]), rng))[:16]

    # 実在感の下限保証: no part ships smooth. If the probability rolls left a
    # module with zero manufacturing detail, stamp a deterministic minimum
    _DETAIL_KINDS = {"panel_step", "vent_slats", "rivet_row", "overlay_plate", "edge_blade"}
    for part in parts:
        feats = list(part.get("features") or [])
        if not any(f.get("kind") in _DETAIL_KINDS for f in feats):
            feats.append({"kind": "rivet_row", "position": round(0.7 + rng.uniform(-0.06, 0.06), 3),
                          "angle_deg": 0, "arc_deg": 70, "count": 4, "zone": "trim"})
            feats.append({"kind": "panel_step", "position": 0.5,
                          "t_span": round(rng.uniform(0.28, 0.36), 2), "angle_deg": 0,
                          "arc_deg": round(rng.uniform(50, 70), 1),
                          "raise": round(rng.uniform(0.35, 0.5), 2)})
            part["features"] = feats[:16]

    blueprint = {
        "schema_version": "armor-blueprint.v1",
        "blueprint_id": f"ABP-{_slug(intent)}-{primary.upper()[:4]}",
        "design_intent": (intent or "").strip()[:2000],
        "emotion_axes": {a: round(v, 3) for a, v in resolved_axes.items() if v > 0},
        "palette": dict(palette) if palette else _resolve_palette(intent, primary, secondary, s, rng),
        "physique": _physique(resolved_axes, moves, rng),
        "parts": parts,
    }
    validate_against_schema(blueprint, "armor-blueprint")
    return blueprint


def llm_prompt(intent: str, modules: tuple[str, ...] | list[str] = _DEFAULT_MODULES) -> str:
    """Instruction for an LLM to emit a valid blueprint JSON (one short call).

    The LLM interprets 思い/意匠 into design parameters; it never touches
    geometry. Output must validate against armor-blueprint.v1.schema.json —
    feed the response straight into tools/generate_armor_from_blueprint.py.
    """
    module_list = ", ".join(modules)
    return (
        "あなたは治安標準庁・設計局のAIである。個人に中立、規格に従属せよ。\n"
        "以下の『設計依頼(誓いと意匠の意図)』を解釈し、ArmorBlueprint v1 JSONのみを出力せよ。\n"
        "説明文・コードフェンス・余計なキーは禁止。schema_version は 'armor-blueprint.v1' 固定。\n"
        f"blueprint_id は 'ABP-' で始まる英数字。parts には {module_list} を全て含める。\n"
        "\n"
        "様式規範(宇宙刑事・特撮ヒーローの文法):\n"
        "- 兜は頭部を包み、visor(shape:'v'推奨) + chin_guard + 側頭の pad_dome(イヤーポッド)を基本とする\n"
        "- 蒸着スーツはメタリックの大面 + 細い発光配管(width_deg≈2のemissive子午線溝)で構成する\n"
        "- 胸は pec_plates + 腹部の ring_grooves 2-3段。共鳴核は pad_dome(zone:'emissive')\n"
        "- ベルトは waist の buckle。ブーツ/前腕は cuff_flange でフレアを作る\n"
        "- 依頼者の言葉こそ意匠の根拠。言葉にない装飾を盛りすぎない。ただし英雄として成立させる\n"
        "\n"
        "設計規則:\n"
        "- cross_section: 数値 1.4(鋭い/獣/昆虫)〜2.0(英雄的)〜3.6(重装/箱)。文字列 sharp/rounded/squared も可\n"
        "- profile: [高さ0-1, 半径倍率0.2-1.2] のカーブでシルエットの痩せ/張りを作る\n"
        "- ring_grooves/meridian_grooves: パネル分割線。depth 0.1-1.0。zone: accent/emissive/trim。\n"
        "  ring_groove は center_deg/sector_deg で前面限定にできる(口元ベント等)\n"
        "- features: visor / chin_guard / crest_fin(クレスト:1-3枚) / horn_pair(角・radius_m小=アンテナ) /\n"
        "  v_core / pec_plates / cuff_flange / pad_dome / buckle / bulge(筋肉の張り) /\n"
        "  spike_row(棘列: count,arc_deg,length_m,pitch_deg) / wing_pair(背の翼: span_m,rise_m,sweep,droop) /\n"
        "  overlay_plate(浮き装甲板: position,t_span,angle_deg,arc_deg,lift_m,corner,taper,rim,bolts,mirror) /\n"
        "  panel_step(パネル段差: position,t_span,angle_deg,arc_deg,raise -1〜1,mirror) /\n"
        "  vent_slats(ベントルーバー: position,t_span,angle_deg,arc_deg,slats 2-8,depth,mirror) /\n"
        "  rivet_row(リベット列: position,angle_deg,arc_deg,count,mirror / along:'meridian'で縦列) /\n"
        "  sash(斜め帯・襷: band_top,band_bottom,from_deg,to_deg,width_m,lift_m,mirror=X字クロス。\n"
        "    ライダー系の胸Xや隊員章の襷は胸のsashで作る) /\n"
        "  collar(襟甲・ネックガード: position≈0.94,height_m,flare,sector_deg 170-215。\n"
        "    パーツの外側に置く: chest は center_deg=0、back は center_deg=180。内側は体に埋まる)\n"
        "- 胴の分節規範: 胸は collar(襟甲) + デコルテの panel_step + 腹部の overlay_plate 2段(瓦)で\n"
        "  鎖骨/胸郭/腹部が別セグメントに読めること。板を1枚張った胸は失格\n"
        "- 実在感の規範: 各部位に panel_step か vent_slats か rivet_row を最低1つ。板は rim>0.5、\n"
        "  四角い板(corner<0.5)には bolts:true。工業的な製造痕こそ実在感である\n"
        "- 機能→装備の演繹: 依頼の役割・能力から小物を導け(剣士→背の鞘帯sash+腰の留め具、\n"
        "  パトロール→肩の警告灯buckle(emissive)+腿ホルスター、飛行→脛後ろのスラスタbuckle+\n"
        "  排気vent、探査→前腕のセンサーbuckle(emissive)+兜のセンサーpod)。\n"
        "  飾りを置くな — すべての小物は依頼が主張した機能の痕跡であること\n"
        "- physique: 体格。torso_bulk/shoulder_bulk/limb_bulk/helmet_bulk (0.85-1.6)。重装なら厚く、俊敏なら細く\n"
        "- palette: 依頼の色語を最優先。base_surfaceは落ち着いた色、emissiveは誓いの光(明色)。#RRGGBB 6桁\n"
        "- partごとに palette_override {base_surface/accent/emissive/trim} で部分配色可\n"
        "  (ベルトは黒、手袋は黒、ブーツだけ白 等 — 衣装の配色は部位で変わるのが普通)\n"
        "- partごとに finish_override {ゾーン: {metallic 0-1, roughness 0.05-1}} で質感可変。\n"
        "  黒い装甲・布・マット樹脂は metallic低+roughness高(暗い金属鏡面は銀に見えてしまう)\n"
        "- 数値は必ずスキーマの範囲内。迷ったら控えめに。逸脱は起動拒否である。\n"
        "出力方言(厳守):\n"
        "- 各partは {module, silhouette:{...}, surface:{...}, features:[...]} の入れ子構造\n"
        "- featureの種別キーは 'kind'('type'は不可)。crest_finのheight/lengthは割合0-1\n"
        "- pad_dome等の角度は 'angle_deg'(左右に置くなら+と-で2要素書く。'count'不可)\n"
        "- ring_groove は 'position'(高さ0-1)必須、meridian_groove は 'angle_deg' 必須で1本ずつ列挙\n"
        "- 兜のprofileは頭頂を閉じる: 先頭点の倍率≤0.75(首の絞り)、最終点(高さ1.0)の倍率0.4-0.55\n"
        "設計依頼:\n"
        f"{(intent or '').strip()}\n"
    )


def _extract_json(text: str) -> dict[str, Any]:
    """Parse an LLM reply into JSON, tolerating code fences and prose edges."""
    body = (text or "").strip()
    if body.startswith("```"):
        body = re.sub(r"^```[a-zA-Z]*\s*", "", body)
        body = re.sub(r"\s*```\s*$", "", body)
    start = body.find("{")
    end = body.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in LLM reply")
    return json.loads(body[start:end + 1])


_TOP_KEYS = {"schema_version", "blueprint_id", "design_intent", "emotion_axes",
             "palette", "physique", "parts"}
_SIL_KEYS = {"cross_section", "profile", "crown_height", "front_bias", "wrap_deg"}
_SURF_KEYS = {"edge_style", "smoothness", "shell_thickness_m", "rim_trim",
              "ring_grooves", "meridian_grooves"}
_PART_KEYS = {"module", "silhouette", "surface", "features", "palette_override"}
_FEAT_KEYS = {"kind", "band_bottom", "band_top", "wrap_deg", "shape", "v_dip",
              "length", "height", "sweep", "thickness_m", "curve", "radius_m",
              "pitch_deg", "width_deg", "apex", "top", "strength",
              "lobe_offset_deg", "lobe_width_deg", "center", "flare",
              "position", "width", "angle_deg", "width_m", "height_m",
              "depth_m", "count", "arc_deg", "length_m", "span_m", "rise_m",
              "droop", "zone", "t_span", "lift_m", "bulge_m", "corner", "taper", "mirror",
              "raise", "slats", "depth", "rim", "bolts", "along",
              "from_deg", "to_deg"}
_RING_KEYS = {"position", "width", "depth", "center_deg", "sector_deg", "zone"}
_MERID_KEYS = {"angle_deg", "width_deg", "depth", "zone"}


def _prune(d: dict, keys: set[str]) -> dict:
    return {k: v for k, v in d.items() if k in keys}


# numeric bounds mirrored from the schema; out-of-range values are clamped,
# not refused — the design survives, the deviation is corrected.
_NUM_BOUNDS = {
    "band_bottom": (0.2, 0.9), "band_top": (0.25, 0.95), "wrap_deg": (40, 220),
    "v_dip": (0, 0.25), "length": (0.05, 0.95), "height": (0.02, 0.6),
    "sweep": (-1, 1), "thickness_m": (0.004, 0.04), "curve": (0, 1),
    "radius_m": (0.004, 0.05), "pitch_deg": (0, 80), "width_deg": (1, 60),
    "apex": (0.05, 0.6), "top": (0.3, 0.95), "strength": (0, 0.3),
    "lobe_offset_deg": (10, 60), "lobe_width_deg": (6, 40), "center": (0.2, 0.9),
    "flare": (0, 0.4), "position": (0.05, 0.95), "width": (0.008, 0.2),
    "angle_deg": (-180, 180), "width_m": (0.02, 0.12), "height_m": (0.01, 0.12),
    "depth_m": (0.008, 0.05), "count": (1, 24), "arc_deg": (10, 300),
    "length_m": (0.015, 0.14), "span_m": (0.1, 0.45), "rise_m": (0.05, 0.35),
    "droop": (0, 0.5), "depth": (0.1, 1.0), "center_deg": (-180, 180),
    "t_span": (0.05, 0.8), "lift_m": (0.002, 0.04), "bulge_m": (0, 0.05),
    "corner": (0, 1), "taper": (-0.7, 0.7),
    "raise": (-1, 1), "slats": (2, 8), "rim": (0, 1),
    "from_deg": (-180, 180), "to_deg": (-180, 180),
    "sector_deg": (10, 360), "crown_height": (0, 0.5), "front_bias": (-0.35, 0.35),
    "shell_thickness_m": (0.004, 0.03), "smoothness": (0, 1),
}
_ZONES = {"accent", "emissive", "trim", "base_surface"}


def _clamp_fields(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if k in _NUM_BOUNDS and isinstance(v, (int, float)) and not isinstance(v, bool):
            lo, hi = _NUM_BOUNDS[k]
            v = max(lo, min(hi, v))
            if k in ("count", "slats"):
                v = int(round(v))
        if k == "zone" and v not in _ZONES:
            v = "accent"
        out[k] = v
    return out


def _repair_part(part: dict[str, Any]) -> dict[str, Any]:
    """Hoist misplaced fields into silhouette/surface and prune unknowns."""
    sil = dict(part.get("silhouette") or {})
    surf = dict(part.get("surface") or {})
    for key in list(part.keys()):
        if key in _SIL_KEYS:
            sil.setdefault(key, part[key])
        elif key in _SURF_KEYS:
            surf.setdefault(key, part[key])
    known_kinds = {"visor", "crest_fin", "horn_pair", "v_core", "pec_plates",
                   "chin_guard", "cuff_flange", "pad_dome", "buckle", "bulge",
                   "spike_row", "wing_pair", "overlay_plate", "edge_blade",
                   "panel_step", "vent_slats", "rivet_row", "sash", "collar"}
    # LLM dialect: alias common key variants back to the contract vocabulary
    aliases = {"type": "kind", "position_deg": "angle_deg", "angle": "angle_deg",
               "position_h": "position", "position_t": "position"}

    def _alias(d: dict) -> dict:
        out = {}
        for k, v in d.items():
            out.setdefault(aliases.get(k, k), v)
        return out

    feats = []
    for f in part.get("features") or []:
        if not isinstance(f, dict):
            continue
        f = _alias(f)
        if f.get("kind") not in known_kinds:
            continue
        # dialect: position as [t, angle] pair
        if isinstance(f.get("position"), (list, tuple)):
            vals = [x for x in f["position"] if isinstance(x, (int, float))]
            if vals:
                if len(vals) > 1:
                    f.setdefault("angle_deg", vals[1])
                f["position"] = vals[0]
            else:
                f.pop("position", None)
        # dialect: band as [bottom, top] range in band_bottom
        if isinstance(f.get("band_bottom"), (list, tuple)):
            vals = [x for x in f["band_bottom"] if isinstance(x, (int, float))]
            if len(vals) > 1:
                f.setdefault("band_top", vals[1])
            f["band_bottom"] = vals[0] if vals else None
        # dialect: ANY bounded numeric field emitted as a list -> first value
        for k, v in list(f.items()):
            if k in _NUM_BOUNDS and isinstance(v, (list, tuple)):
                nums = [x for x in v if isinstance(x, (int, float))]
                if nums:
                    f[k] = nums[0]
                else:
                    f.pop(k)
        # absolute metres on crest fins -> fractional contract values
        if f["kind"] == "crest_fin":
            if "height_m" in f and "height" not in f:
                f["height"] = float(f.pop("height_m")) * 3.0
            if "length_m" in f and "length" not in f:
                f["length"] = float(f.pop("length_m")) * 3.0
        if f["kind"] in ("pad_dome", "buckle"):
            if "radius_m" in f and "width_m" not in f:
                r = float(f.pop("radius_m"))
                f["width_m"] = r * 1.6
                f.setdefault("height_m", r * 1.6)
            f.setdefault("position", 0.5)
            # "count: 2" at one angle means a mirrored pair
            n = f.pop("count", 1)
            ang = f.get("angle_deg", 0)
            if isinstance(n, (int, float)) and n >= 2 and abs(float(ang)) > 5:
                for sign in (1.0, -1.0):
                    feats.append(_clamp_fields(_prune({**f, "angle_deg": sign * abs(float(ang))}, _FEAT_KEYS)))
                continue
        feats.append(_clamp_fields(_prune(f, _FEAT_KEYS)))
    # grooves: alias, expand count->even spread, drop unusable, clamp
    ring_in = [(_alias(g)) for g in surf.get("ring_grooves") or [] if isinstance(g, dict)]
    surf["ring_grooves"] = [
        _clamp_fields(_prune(g, _RING_KEYS))
        for g in ring_in if isinstance(g.get("position"), (int, float))
    ][:4]
    merid_out = []
    for g in (surf.get("meridian_grooves") or []):
        if not isinstance(g, dict):
            continue
        g = _alias(g)
        if isinstance(g.get("angle_deg"), (int, float)):
            merid_out.append(_clamp_fields(_prune(g, _MERID_KEYS)))
        elif isinstance(g.get("count"), (int, float)) and g.get("count", 0) >= 1:
            n = min(6, int(g["count"]))
            for i in range(n):
                ang = -180 + 360.0 * i / n
                merid_out.append(_clamp_fields(_prune({**g, "angle_deg": round(ang, 1)}, _MERID_KEYS)))
    surf["meridian_grooves"] = merid_out[:6]
    # silhouette: clamp scalars, sanitize profile points, accept enum cross
    sil = _clamp_fields(_prune(sil, _SIL_KEYS))
    cross = sil.get("cross_section")
    if isinstance(cross, (int, float)) and not isinstance(cross, bool):
        sil["cross_section"] = max(1.2, min(5.0, float(cross)))
    elif cross not in ("sharp", "rounded", "squared", None):
        sil.pop("cross_section", None)
    prof = sil.get("profile")
    if isinstance(prof, list):
        pts = []
        for pt in prof[:8]:
            try:
                t, sc = float(pt[0]), float(pt[1])
            except (TypeError, ValueError, IndexError):
                continue
            pts.append([max(0.0, min(1.0, t)), max(0.2, min(1.2, sc))])
        pts.sort(key=lambda p: p[0])
        if len(pts) >= 2:
            if part.get("module") == "helmet":
                # a helmet must CLOSE: taper the neck and shut the crown, no
                # matter what silhouette the designer dreamed in between
                pts[0][1] = min(pts[0][1], 0.75)
                pts[-1][1] = min(pts[-1][1], 0.52)
                if pts[-1][0] < 0.95:
                    pts.append([1.0, 0.48])
                pts = pts[:8]
            sil["profile"] = pts
        else:
            sil.pop("profile", None)
    else:
        sil.pop("profile", None)
    if str(surf.get("edge_style")) not in ("machined", "razor", "organic"):
        surf.pop("edge_style", None)
    # multiple sashes on one part must not stack on the same diagonal —
    # spread them so straps read as separate gear, not z-fighting ribbons
    sash_i = 0
    for f in feats:
        if f.get("kind") == "sash":
            if sash_i > 0:
                shift = 9.0 * sash_i
                f["from_deg"] = max(-180, min(180, float(f.get("from_deg", -25)) - shift))
                f["to_deg"] = max(-180, min(180, float(f.get("to_deg", 30)) + shift))
                f["lift_m"] = min(0.03, float(f.get("lift_m", 0.012)) + 0.004 * sash_i)
            sash_i += 1

    out = {"module": part.get("module"),
           "silhouette": sil,
           "surface": _clamp_fields(_prune(surf, _SURF_KEYS)),
           "features": feats[:16]}
    override = part.get("palette_override")
    if isinstance(override, dict):
        clean = {k: v for k, v in override.items()
                 if k in ("base_surface", "accent", "emissive", "trim")
                 and isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v)}
        if clean:
            out["palette_override"] = clean
    finish = part.get("finish_override")
    if isinstance(finish, dict):
        clean_f = {}
        for k, v in finish.items():
            if k not in ("base_surface", "accent", "emissive", "trim") or not isinstance(v, dict):
                continue
            entry = {}
            if isinstance(v.get("metallic"), (int, float)):
                entry["metallic"] = max(0.0, min(1.0, float(v["metallic"])))
            if isinstance(v.get("roughness"), (int, float)):
                entry["roughness"] = max(0.05, min(1.0, float(v["roughness"])))
            if entry:
                clean_f[k] = entry
        if clean_f:
            out["finish_override"] = clean_f
    return out


def _normalize_llm_blueprint(raw: dict[str, Any], intent: str,
                             modules: tuple[str, ...] | list[str]) -> dict[str, Any]:
    """Repair the easy deviations so a good design isn't refused on a typo:
    fix id/version, restore the original intent, and fill any missing modules
    from the rule compiler so the full body always assembles."""
    bp = dict(raw)
    bp["schema_version"] = "armor-blueprint.v1"
    bid = str(bp.get("blueprint_id", ""))
    if not re.match(r"^ABP-[A-Z0-9-]{4,32}$", bid):
        bp["blueprint_id"] = f"ABP-{_slug(intent)}-LLM"
    bp["design_intent"] = (intent or "").strip()[:2000]
    # parts may arrive as a list or a module-keyed dict — accept both
    raw_parts = bp.get("parts", [])
    if isinstance(raw_parts, dict):
        parts_list = []
        for key, val in raw_parts.items():
            if isinstance(val, dict):
                val.setdefault("module", str(key))
                parts_list.append(val)
    else:
        parts_list = [p for p in raw_parts if isinstance(p, dict)]
    parts_list = [_repair_part(p) for p in parts_list]
    have = {str(p.get("module")) for p in parts_list}
    missing = [m for m in modules if m not in have]
    if missing:
        filler = compile_blueprint(intent, modules=tuple(missing))
        parts_list.extend(filler["parts"])
    # keep only requested modules, in canonical order
    by_mod = {str(p.get("module")): p for p in parts_list}
    bp["parts"] = [by_mod[m] for m in modules if m in by_mod]
    if isinstance(bp.get("physique"), dict):
        phys = {}
        bounds = {"torso_bulk": (0.85, 1.45), "shoulder_bulk": (0.85, 1.6),
                  "limb_bulk": (0.85, 1.4), "helmet_bulk": (0.9, 1.25)}
        for k, (lo, hi) in bounds.items():
            v = bp["physique"].get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                phys[k] = round(max(lo, min(hi, float(v))), 3)
        bp["physique"] = phys
    else:
        bp.pop("physique", None)
    if isinstance(bp.get("palette"), dict):
        pal = {}
        for k in ("base_surface", "accent", "emissive", "trim"):
            v = str(bp["palette"].get(k, ""))
            if re.match(r"^#[0-9A-Fa-f]{6}$", v):
                pal[k] = v
        bp["palette"] = _ensure_palette_contrast(pal)  # LLM palettes drown too
    else:
        bp.pop("palette", None)
    if isinstance(bp.get("emotion_axes"), dict):
        bp["emotion_axes"] = {a: round(max(0.0, min(1.0, float(v))), 3)
                              for a, v in bp["emotion_axes"].items()
                              if a in AXES and isinstance(v, (int, float))}
    else:
        bp.pop("emotion_axes", None)
    return _prune(bp, _TOP_KEYS)


def compile_blueprint_llm(
    intent: str,
    modules: tuple[str, ...] | list[str] = _DEFAULT_MODULES,
    timeout_seconds: int = 90,
) -> tuple[dict[str, Any], str]:
    """Route B: one Gemini text call interprets 思い/言葉 into the blueprint.

    Returns (blueprint, route_tag). Any failure — no key, network, bad JSON,
    schema refusal — falls back to the deterministic rule compiler, so the
    forge never dies on stage. The LLM writes ONLY the design JSON; geometry
    stays with the deterministic Blender builder.
    """
    from ._env import load_dotenv

    dotenv = load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY") or dotenv.get("GEMINI_API_KEY", "")
    model = (os.getenv("GEMINI_TEXT_MODEL") or dotenv.get("GEMINI_TEXT_MODEL")
             or "gemini-2.5-flash")
    if not api_key or api_key.startswith("YOUR_"):
        return compile_blueprint(intent, modules=modules), "rule_fallback:no_key"

    payload = {
        "contents": [{"parts": [{"text": llm_prompt(intent, modules)}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    request = Request(url=url, data=json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                      method="POST")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            reply = json.loads(response.read().decode("utf-8"))
        text = "".join(
            part.get("text", "")
            for cand in reply.get("candidates", [])[:1]
            for part in cand.get("content", {}).get("parts", [])
        )
        blueprint = _normalize_llm_blueprint(_extract_json(text), intent, modules)
        validate_against_schema(blueprint, "armor-blueprint")
        return blueprint, f"llm:{model}"
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
        fallback = compile_blueprint(intent, modules=modules)
        reason = str(exc).replace("\n", " ")[:160]
        return fallback, f"rule_fallback:{type(exc).__name__}:{reason}"
