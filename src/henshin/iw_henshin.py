"""IWSDK-ready voice triggered armor deposition module.

The real IWSDK/mocopi live receiver can call into this module later. For now it
provides a deterministic core that can be run from CLI and tested without
network credentials.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .archive import ensure_session_dir, write_json
from .bodyfit import BodyFrame, CoverScale, Vec2, run_body_sequence
from .ids import generate_session_id
from .sakura_ai_engine import (
    SakuraAIEngineClient,
    SakuraAIEngineConfig,
    SakuraAIEngineError,
    TranscriptionResult,
    resolve_sakura_config,
    save_speech,
)
from .transform import ProtocolStateMachine


DEFAULT_TRIGGER_PHRASE = "生成"
DEFAULT_EXPLANATION = (
    "生成とは、観測された身体輪郭と意志信号を同期し、"
    "装甲を身体表面へ確定させる変身プロトコルである。"
    "いま、追跡骨格を基準に全身アーマーを蒸着する。"
)


DEFAULT_TRIGGER_PHRASE = "\u751f\u6210"
DEFAULT_TRIGGER_ALIASES: frozenset[str] = frozenset(
    (
        "\u5148\u751f",  # 先生
        "\u305b\u3044\u305b\u3044",  # せいせい
        "\u305b\u3048\u305b\u3048",  # せえせえ
        "\u305b\u30fc\u305b\u30fc",  # せーせー
        "\u30bb\u30a4\u30bb\u30a4",  # セイセイ
        "\u30bb\u30fc\u30bb\u30fc",  # セーセー
    )
)
DEFAULT_EXPLANATION = (
    "\u751f\u6210\u3068\u306f\u3001\u89b3\u6e2c\u3055\u308c\u305f\u8eab\u4f53\u8f2a\u90ed\u3068\u610f\u5fd7\u4fe1\u53f7\u3092\u540c\u671f\u3057\u3001"
    "\u88c5\u7532\u3092\u8eab\u4f53\u8868\u9762\u3078\u78ba\u5b9a\u3055\u305b\u308b\u5909\u8eab\u30d7\u30ed\u30c8\u30b3\u30eb\u3067\u3042\u308b\u3002"
    "\u3044\u307e\u3001\u8ffd\u8de1\u9aa8\u683c\u3092\u57fa\u6e96\u306b\u5168\u8eab\u30a2\u30fc\u30de\u30fc\u3092\u84b8\u7740\u3059\u308b\u3002"
)
DEFAULT_TRIGGER_ALIASES = DEFAULT_TRIGGER_ALIASES | frozenset(
    (
        "\u305b\u3044\u305c\u3044",
        "\u305b\u3048\u305c\u3048",
        "\u30bb\u30a4\u30bc\u30a4",
        "\u7cbe\u88fd",
    )
)


@dataclass(slots=True)
class IWSDKHenshinConfig:
    trigger_phrase: str = DEFAULT_TRIGGER_PHRASE
    explanation_text: str = DEFAULT_EXPLANATION
    mirror: bool = True
    dock_center_x: float = 0.55
    dock_center_y: float = -0.25
    dock_radius: float = 0.18
    hold_to_equip_sec: float = 0.6
    trigger_joint: str = "right_wrist"
    tts_enabled: bool = True


@dataclass(slots=True)
class IWSDKHenshinRequest:
    transcript: str | None = None
    audio_path: str | Path | None = None
    mocopi_payload: dict[str, Any] | None = None
    session_id: str | None = None
    root: str | Path = "sessions"
    dry_run: bool = False
    config: IWSDKHenshinConfig | None = None
    sakura_config: SakuraAIEngineConfig | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_trigger_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    return re.sub(r"[\s\u3000、。,.!！?？「」『』\"'`・…-]+", "", normalized)


def _normalize_voice_intent_text(text: str) -> str:
    punctuation = {
        " ",
        "\t",
        "\n",
        "\r",
        "\u3000",
        "\u3001",
        "\u3002",
        ",",
        ".",
        "!",
        "\uff01",
        "?",
        "\uff1f",
        "\u300c",
        "\u300d",
        "\u300e",
        "\u300f",
        '"',
        "'",
        "`",
        "\u30fb",
        "\u2026",
        "-",
        "\u30fc",
    }
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    return "".join(char for char in normalized if char not in punctuation and not char.isspace())


def analyze_generation_trigger(text: str, trigger_phrase: str = DEFAULT_TRIGGER_PHRASE) -> dict[str, Any]:
    normalized = _normalize_voice_intent_text(text)
    trigger = _normalize_voice_intent_text(trigger_phrase or DEFAULT_TRIGGER_PHRASE)
    if trigger and trigger in normalized:
        return {
            "detected": True,
            "mode": "exact",
            "matched": trigger_phrase or DEFAULT_TRIGGER_PHRASE,
            "confidence": 1.0,
            "source": "exact_trigger",
            "normalized": normalized,
        }

    for alias in DEFAULT_TRIGGER_ALIASES:
        normalized_alias = _normalize_voice_intent_text(alias)
        if normalized == normalized_alias or (
            normalized.startswith(normalized_alias) and len(normalized) <= len(normalized_alias) + 4
        ):
            return {
                "detected": True,
                "mode": "voice_intent",
                "matched": alias,
                "canonical": DEFAULT_TRIGGER_PHRASE,
                "confidence": 0.82,
                "source": "generation_homophone_lexicon",
                "normalized": normalized,
            }

    return {
        "detected": False,
        "mode": "none",
        "matched": None,
        "canonical": trigger_phrase or DEFAULT_TRIGGER_PHRASE,
        "confidence": 0.0,
        "source": "no_match",
        "normalized": normalized,
    }


def detect_generation_trigger(text: str, trigger_phrase: str = DEFAULT_TRIGGER_PHRASE) -> bool:
    return bool(analyze_generation_trigger(text, trigger_phrase).get("detected"))


def _frame_dt(raw: dict[str, Any]) -> float:
    for key in ("dt_sec", "deltaTime", "delta_time", "dt"):
        if key in raw:
            try:
                return float(raw[key])
            except (TypeError, ValueError):
                break
    return 0.1


JOINT_ALIASES: dict[str, tuple[str, ...]] = {
    "left_shoulder": ("left_shoulder", "LeftShoulder", "leftShoulder", "l_shoulder"),
    "right_shoulder": ("right_shoulder", "RightShoulder", "rightShoulder", "r_shoulder"),
    "left_elbow": ("left_elbow", "LeftLowerArm", "LeftElbow", "leftElbow", "l_elbow"),
    "right_elbow": ("right_elbow", "RightLowerArm", "RightElbow", "rightElbow", "r_elbow"),
    "left_wrist": ("left_wrist", "LeftHand", "LeftWrist", "leftWrist", "l_wrist"),
    "right_wrist": ("right_wrist", "RightHand", "RightWrist", "rightWrist", "r_wrist"),
    "left_hip": ("left_hip", "LeftUpperLeg", "LeftHip", "leftHip", "l_hip"),
    "right_hip": ("right_hip", "RightUpperLeg", "RightHip", "rightHip", "r_hip"),
    "left_knee": ("left_knee", "LeftLowerLeg", "LeftKnee", "leftKnee", "l_knee"),
    "right_knee": ("right_knee", "RightLowerLeg", "RightKnee", "rightKnee", "r_knee"),
    "left_ankle": ("left_ankle", "LeftFoot", "LeftAnkle", "leftAnkle", "l_ankle"),
    "right_ankle": ("right_ankle", "RightFoot", "RightAnkle", "rightAnkle", "r_ankle"),
}


def _extract_xy(value: Any) -> tuple[float, float] | None:
    if isinstance(value, dict):
        x = value.get("x")
        y = value.get("y")
    elif isinstance(value, (list, tuple)) and len(value) >= 2:
        x, y = value[0], value[1]
    else:
        return None

    try:
        xf = float(x)
        yf = float(y)
    except (TypeError, ValueError):
        return None

    if 0.0 <= xf <= 1.0 and 0.0 <= yf <= 1.0:
        return xf, yf
    if -1.5 <= xf <= 1.5 and -1.5 <= yf <= 1.5:
        return (xf + 1.0) * 0.5, (1.0 - yf) * 0.5
    return None


def _source_joints(raw: dict[str, Any]) -> dict[str, Any]:
    for key in ("joints", "bones", "skeleton", "pose"):
        value = raw.get(key)
        if isinstance(value, dict):
            return value
    return raw


def normalize_mocopi_frames(payload: dict[str, Any] | None, *, fallback: bool = True) -> list[BodyFrame]:
    if not payload:
        return create_demo_body_frames() if fallback else []

    raw_frames = payload.get("frames") or payload.get("mocopi_frames") or []
    frames: list[BodyFrame] = []
    for raw in raw_frames:
        if not isinstance(raw, dict):
            continue
        source = _source_joints(raw)
        joints: dict[str, tuple[float, float]] = {}
        for canonical, aliases in JOINT_ALIASES.items():
            for alias in aliases:
                if alias not in source:
                    continue
                xy = _extract_xy(source[alias])
                if xy is not None:
                    joints[canonical] = xy
                    break
        if joints:
            frames.append(BodyFrame(dt_sec=_frame_dt(raw), joints_xy01=joints))

    return frames or (create_demo_body_frames() if fallback else [])


def create_demo_body_frames() -> list[BodyFrame]:
    base = {
        "left_shoulder": (0.62, 0.38),
        "right_shoulder": (0.38, 0.38),
        "left_elbow": (0.67, 0.48),
        "right_elbow": (0.33, 0.48),
        "left_wrist": (0.70, 0.61),
        "right_wrist": (0.225, 0.625),
        "left_hip": (0.57, 0.58),
        "right_hip": (0.43, 0.58),
        "left_knee": (0.57, 0.76),
        "right_knee": (0.43, 0.76),
        "left_ankle": (0.57, 0.92),
        "right_ankle": (0.43, 0.92),
    }
    return [BodyFrame(dt_sec=0.1, joints_xy01=dict(base)) for _ in range(8)]


def _machine_for_completed_deposition() -> ProtocolStateMachine:
    machine = ProtocolStateMachine()
    for state in [
        "POSTED",
        "FIT_AUDIT",
        "MORPHOTYPE_LOCKED",
        "DESIGN_ISSUED",
        "DRY_FIT_SIM",
        "TRY_ON",
        "APPROVAL_PENDING",
        "APPROVED",
        "DEPOSITION",
        "SEALING",
        "ACTIVE",
        "ARCHIVED",
    ]:
        note = "Voice trigger: armor deposition completed" if state == "DEPOSITION" else ""
        machine.transition(state, note=note)
    return machine


def _serialize_body_frames(frames: Iterable[BodyFrame]) -> list[dict[str, Any]]:
    return [
        {
            "dt_sec": frame.dt_sec,
            "joints": {name: [xy[0], xy[1]] for name, xy in frame.joints_xy01.items()},
        }
        for frame in frames
    ]


def _write_body_sim(path: Path, sim: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sim, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _transcribe(
    request: IWSDKHenshinRequest,
    client: SakuraAIEngineClient | None,
) -> tuple[str, dict[str, Any]]:
    if request.transcript is not None:
        return request.transcript, {"source": "transcript", "model": None}
    dry_run_phrase = request.config.trigger_phrase if request.config else DEFAULT_TRIGGER_PHRASE
    if not request.audio_path:
        return dry_run_phrase if request.dry_run else "", {"source": "empty", "model": None}
    if request.dry_run:
        return dry_run_phrase, {"source": "dry_run_audio", "model": None}
    if client is None:
        client = SakuraAIEngineClient(request.sakura_config or resolve_sakura_config())
    result: TranscriptionResult = client.transcribe_file(request.audio_path)
    return result.text, {"source": "sakura_whisper", "model": result.model, "raw": result.raw}


def _maybe_synthesize_tts(
    *,
    session_dir: Path,
    config: IWSDKHenshinConfig,
    request: IWSDKHenshinRequest,
    client: SakuraAIEngineClient | None,
) -> dict[str, Any]:
    if not config.tts_enabled:
        return {"status": "disabled", "text": config.explanation_text, "audio_path": None}
    if request.dry_run:
        return {"status": "dry_run", "text": config.explanation_text, "audio_path": None}

    resolved_config = request.sakura_config or resolve_sakura_config()
    if not resolved_config.token:
        return {"status": "skipped_missing_token", "text": config.explanation_text, "audio_path": None}

    if client is None:
        client = SakuraAIEngineClient(resolved_config)
    try:
        result = client.synthesize_speech(config.explanation_text)
    except SakuraAIEngineError as exc:
        return {
            "status": "failed",
            "text": config.explanation_text,
            "audio_path": None,
            "error": str(exc),
        }
    output = save_speech(
        result,
        session_dir / "artifacts" / f"generation-explainer.{result.response_format}",
    )
    return {
        "status": "generated",
        "text": config.explanation_text,
        "audio_path": str(output),
        "model": result.model,
        "voice": result.voice,
        "response_format": result.response_format,
    }


def run_iwsdk_henshin(
    request: IWSDKHenshinRequest,
    *,
    client: SakuraAIEngineClient | None = None,
) -> dict[str, Any]:
    config = request.config or IWSDKHenshinConfig()
    session_id = request.session_id or generate_session_id()
    session_dir = ensure_session_dir(session_id, root=request.root)

    events: list[dict[str, Any]] = [
        {"type": "iw.session.started", "timestamp": utc_now_iso(), "session_id": session_id}
    ]

    try:
        transcript, transcription_meta = _transcribe(request, client)
    except SakuraAIEngineError as exc:
        return {"ok": False, "session_id": session_id, "error": str(exc)}

    trigger_match = analyze_generation_trigger(transcript, config.trigger_phrase)
    triggered = bool(trigger_match["detected"])
    events.append(
        {
            "type": "iw.voice.transcribed",
            "timestamp": utc_now_iso(),
            "text": transcript,
            "trigger_phrase": config.trigger_phrase,
            "triggered": triggered,
            "trigger_match": trigger_match,
            "meta": transcription_meta,
        }
    )

    frames = normalize_mocopi_frames(request.mocopi_payload)
    body_sim = run_body_sequence(
        frames,
        mirror=config.mirror,
        cover_scale=CoverScale(1.0, 1.0),
        dock_center=Vec2(config.dock_center_x, config.dock_center_y),
        dock_radius=config.dock_radius,
        hold_to_equip_sec=config.hold_to_equip_sec,
        trigger_joint=config.trigger_joint,
    )

    if triggered:
        machine = _machine_for_completed_deposition()
        tts = _maybe_synthesize_tts(
            session_dir=session_dir,
            config=config,
            request=request,
            client=client,
        )
        events.extend(
            [
                {"type": "iw.command.detected", "timestamp": utc_now_iso(), "command": config.trigger_phrase},
                {"type": "iw.armor.deposition.started", "timestamp": utc_now_iso()},
                {
                    "type": "iw.armor.deposition.completed",
                    "timestamp": utc_now_iso(),
                    "equipped": bool(body_sim.get("equipped")),
                    "equip_frame": body_sim.get("equip_frame"),
                },
            ]
        )
    else:
        machine = ProtocolStateMachine()
        tts = {"status": "not_triggered", "text": config.explanation_text, "audio_path": None}

    body_sim_path = _write_body_sim(session_dir / "body-sim.json", body_sim)
    replay = {
        "schema_version": "0.1",
        "session_id": session_id,
        "created_at": utc_now_iso(),
        "source": {
            "speech": transcription_meta,
            "tracking": "mocopi",
            "iwsdk_bridge": "event_stream_v0",
        },
        "trigger": {
            "phrase": config.trigger_phrase,
            "transcript": transcript,
            "detected": triggered,
            "match": trigger_match,
        },
        "tts": tts,
        "protocol": {
            "final_state": machine.state,
            "events": [asdict(event) for event in machine.events],
        },
        "tracking": {
            "frames": _serialize_body_frames(frames),
            "frame_count": len(frames),
        },
        "deposition": {
            "completed": bool(triggered and body_sim.get("equipped")),
            "body_sim_path": str(body_sim_path),
            "equip_frame": body_sim.get("equip_frame"),
            "segments": body_sim.get("segments", []),
        },
        "iwsdk_events": events,
    }
    replay_path = write_json(session_dir / "artifacts" / "iwsdk-deposition-replay.json", replay)
    events_path = session_dir / "artifacts" / "iwsdk-events.jsonl"
    events_path.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )

    return {
        "ok": bool(triggered and body_sim.get("equipped")),
        "session_id": session_id,
        "triggered": triggered,
        "equipped": bool(body_sim.get("equipped")),
        "equip_frame": body_sim.get("equip_frame"),
        "final_state": machine.state,
        "transcript": transcript,
        "trigger_phrase": config.trigger_phrase,
        "trigger_match": trigger_match,
        "body_sim_path": str(body_sim_path),
        "replay_path": str(replay_path),
        "events_path": str(events_path),
        "tts": tts,
    }
