"""Phase 1 API contract skeleton for the GCP new route.

This module keeps the first API surface independent from the local dashboard
handler so the same contract can later be mirrored by a Cloud Run/Hono service.
"""

from __future__ import annotations

import json
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
from http import HTTPStatus
from pathlib import Path
from typing import Any

from .ids import (
    generate_approval_id,
    generate_morphotype_id,
    next_recall_code,
    next_suit_id,
    normalize_recall_code,
    parse_suit_id,
)
from .manifest import project_suitspec_to_manifest
from .validators import validate_against_schema, validate_suitspec

_SUIT_ID_RE = re.compile(r"^VDA-[A-Z0-9]+-[A-Z0-9]+-[0-9]{2}-[0-9]{4}$")
_MANIFEST_ID_RE = re.compile(r"^MNF-[0-9]{8}-[A-Z0-9]{4}$")
_SESSION_ID_RE = re.compile(r"^S-[A-Z0-9][A-Z0-9-]{2,63}$")
_EVENT_ID_RE = re.compile(r"^EVT-[0-9]{8}-[A-Z0-9]{6}$")
_SUIT_STATUSES = {"DRAFT", "READY", "ACTIVE", "RETIRED"}
_TRANSFORM_STATES = {
    "IDLE",
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
    "REFUSED",
}
_TRANSFORM_STATE_ORDER = [
    "IDLE",
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
    "REFUSED",
]
_TRANSFORM_STATE_RANK = {state: index for index, state in enumerate(_TRANSFORM_STATE_ORDER)}
_FORGE_DEFAULT_PARTS = {
    "helmet",
    "chest",
    "back",
    "waist",
    "left_shoulder",
    "right_shoulder",
    "left_forearm",
    "right_forearm",
    "left_shin",
    "right_shin",
    "left_boot",
    "right_boot",
}
_FORGE_REQUIRED_PARTS = {"helmet", "chest", "back"}
_FORGE_DEFAULT_HEIGHT_CM = 170.0
_FORGE_MIN_HEIGHT_CM = 90.0
_FORGE_MAX_HEIGHT_CM = 230.0
_FORGE_VRM_BASELINE_REF = "viewer/assets/vrm/default.vrm"
_FORGE_TEXTURE_PROVIDER_PROFILE = "nano_banana"
_FORGE_TEXTURE_MODE = "mesh_uv"
_FORGE_UV_REFINE = True
_FORGE_ASSET_CONTRACT = "vrm-base-suit+mesh-v1-overlay"
_RECALL_AMBIGUOUS_TRANSLATION = str.maketrans({"0": "O", "O": "O", "1": "I", "I": "I", "L": "I"})
_TRANSFORM_EVENT_TYPES = {
    "SESSION_CREATED",
    "TRIGGER_DETECTED",
    "VOICE_CAPTURED",
    "TRACKING_FRAME_BATCH",
    "STATE_TRANSITION",
    "FIT_AUDIT_RECORDED",
    "MORPHOTYPE_LOCKED",
    "BLUEPRINT_ISSUED",
    "APPROVAL_GRANTED",
    "DEPOSITION_STARTED",
    "DEPOSITION_PROGRESS",
    "DEPOSITION_COMPLETED",
    "SEAL_VERIFIED",
    "REFUSAL_RECORDED",
    "ERROR_RECORDED",
    "SESSION_ARCHIVED",
}
_MAX_REPLAY_MOTION_FRAMES = 240


@dataclass(frozen=True, slots=True)
class ApiResponse:
    status: int
    body: dict[str, Any]


class NewRouteApi:
    def __init__(self, repo_root: Path, *, suit_store_root: Path | None = None) -> None:
        self.repo_root = repo_root.resolve()
        self.suit_store_root = (suit_store_root or self.repo_root / "sessions" / "new-route" / "suits").resolve()
        self.trial_store_root = self.suit_store_root.parent / "trials"

    def health(self) -> ApiResponse:
        return ApiResponse(
            status=HTTPStatus.OK,
            body={
                "ok": True,
                "service": "new-route-api",
                "phase": "phase1",
                "contracts": ["SuitManifest", "PartCatalog", "TransformSession", "ReplayScript"],
            },
        )

    def create_suit(self, payload: dict[str, Any]) -> ApiResponse:
        if not isinstance(payload, dict):
            return self._bad_request("request body must be a JSON object")

        suitspec = payload.get("suitspec")
        if not isinstance(suitspec, dict):
            return self._bad_request("suitspec must be a JSON object")
        try:
            validate_suitspec(suitspec)
            validate_against_schema(suitspec, "suitspec")
        except ValueError as exc:
            return self._bad_request(str(exc))

        suit_id = str(suitspec["suit_id"])
        suit_path = self._suit_path(suit_id)
        suitspec_path = self._suitspec_path(suit_id)
        overwrite = bool(payload.get("overwrite", False))
        if suitspec_path.exists() and not overwrite:
            return ApiResponse(status=HTTPStatus.CONFLICT, body={"ok": False, "error": f"Suit already exists: {suit_id}"})

        now = self._utc_now()
        display_name = self._display_name(payload.get("display_name"))
        try:
            recall_code = self._resolve_recall_code(
                payload.get("recall_code"),
                suit_id=suit_id,
                previous_suit=self._read_json(suit_path) if suit_path.exists() else None,
            )
        except ValueError as exc:
            return self._bad_request(str(exc))
        saved_suitspec = self._clone_json(suitspec)
        metadata = saved_suitspec.setdefault("metadata", {})
        if not isinstance(metadata, dict):
            return self._bad_request("suitspec.metadata must be a JSON object")
        metadata.setdefault("created_at", now)
        metadata["updated_at"] = now
        try:
            validate_against_schema(saved_suitspec, "suitspec")
        except ValueError as exc:
            return self._bad_request(str(exc))

        previous_suit = self._read_json(suit_path) if suit_path.exists() else {}
        previous_metadata = previous_suit.get("metadata") if isinstance(previous_suit.get("metadata"), dict) else {}
        issue = previous_metadata.get("issue") if isinstance(previous_metadata.get("issue"), dict) else {}
        issue = {**issue, **parse_suit_id(suit_id), "recall_code": recall_code}
        issue.setdefault("issued_at", now)
        issue.setdefault("source", "new-route-api")
        suit_metadata = {
            **previous_metadata,
            "created_at": previous_metadata.get("created_at", now),
            "updated_at": now,
            "issue": issue,
        }
        if display_name:
            suit_metadata["display_name"] = display_name
        suit = {
            "schema_version": "0.1",
            "suit_id": suit_id,
            "recall_code": recall_code,
            "suitspec_schema_version": saved_suitspec["schema_version"],
            "status": previous_suit.get("status", "DRAFT"),
            "manifest_id": previous_suit.get("manifest_id"),
            "artifacts": {
                **previous_suit.get("artifacts", {}),
                "suitspec_path": self._relative_path(suitspec_path),
            },
            "metadata": suit_metadata,
        }
        self._write_json(suitspec_path, saved_suitspec)
        self._write_json(suit_path, suit)
        return ApiResponse(
            status=HTTPStatus.CREATED,
            body={
                "ok": True,
                "suit_id": suit_id,
                "recall_code": recall_code,
                "schema_version": saved_suitspec["schema_version"],
                "status": suit["status"],
                "suitspec_path": self._relative_path(suitspec_path),
                "links": {"manifest": f"/v1/suits/{suit_id}/manifest"},
                "suit": suit,
                "suitspec": saved_suitspec,
                "storage": self._storage_info(suitspec_path),
            },
        )

    def issue_suit_id(self, payload: dict[str, Any]) -> ApiResponse:
        if not isinstance(payload, dict):
            return self._bad_request("request body must be a JSON object")
        try:
            rev = int(payload.get("rev", 0))
            suit_id = next_suit_id(
                self._all_suit_ids(),
                series=str(payload.get("series", "AXIS")),
                role=str(payload.get("role", "OP")),
                rev=rev,
            )
        except (TypeError, ValueError) as exc:
            return self._bad_request(str(exc))

        now = self._utc_now()
        display_name = self._display_name(payload.get("display_name"))
        try:
            recall_code = self._resolve_recall_code(payload.get("recall_code"), suit_id=suit_id)
        except ValueError as exc:
            return self._bad_request(str(exc))
        issue = {**parse_suit_id(suit_id), "recall_code": recall_code, "issued_at": now, "source": "new-route-api"}
        suit = {
            "schema_version": "0.1",
            "suit_id": suit_id,
            "recall_code": recall_code,
            "suitspec_schema_version": None,
            "status": "DRAFT",
            "manifest_id": None,
            "artifacts": {},
            "metadata": {
                "created_at": now,
                "updated_at": now,
                "display_name": display_name,
                "issue": issue,
            },
        }
        suit_path = self._suit_path(suit_id)
        self._write_json(suit_path, suit)
        return ApiResponse(
            status=HTTPStatus.CREATED,
            body={
                "ok": True,
                "suit_id": suit_id,
                "recall_code": recall_code,
                "display_name": display_name,
                "issue": issue,
                "suit": suit,
                "links": {"create_suit": "/v1/suits", "suit": f"/v1/suits/{suit_id}"},
                "storage": self._storage_info(suit_path),
            },
        )

    def forge_suit(self, payload: dict[str, Any]) -> ApiResponse:
        if not isinstance(payload, dict):
            return self._bad_request("request body must be a JSON object")

        display_name = self._display_name(payload.get("display_name") or payload.get("name"))
        try:
            rev = int(payload.get("rev", 0))
            suit_id = next_suit_id(
                self._all_suit_ids(),
                series=str(payload.get("series", "AXIS")),
                role=str(payload.get("role", "WEB")),
                rev=rev,
            )
            recall_code = self._resolve_recall_code(payload.get("recall_code"), suit_id=suit_id)
            body_profile = self._forge_body_profile(payload)
            self._forge_palette(
                payload.get("palette"),
                {"primary": "#F4F1E8", "secondary": "#8C96A3", "emissive": "#D8F7FF"},
            )
            self._forge_enabled_parts(payload)
        except (TypeError, ValueError) as exc:
            return self._bad_request(str(exc))
        try:
            suitspec = self._forge_suitspec_from_payload(payload, suit_id=suit_id, display_name=display_name)
        except ValueError as exc:
            return self._bad_request(str(exc))

        create = self.create_suit({
            "suitspec": suitspec,
            "display_name": display_name,
            "recall_code": recall_code,
            "overwrite": True,
        })
        if create.status != HTTPStatus.CREATED:
            return create

        manifest_response = self.attach_manifest(suit_id, {"status": "READY"})
        if manifest_response.status != HTTPStatus.CREATED:
            self._discard_suit(suit_id)
            return manifest_response

        return ApiResponse(
            status=HTTPStatus.CREATED,
            body={
                "ok": True,
                "recall_code": recall_code,
                "display_name": display_name,
                "status": "READY",
                "readiness": {
                    "suitspec_ready": True,
                    "manifest_ready": manifest_response.body["manifest"]["status"] == "READY",
                },
                "body_profile": body_profile,
                "preview": self._forge_public_preview(create.body["suitspec"]),
                "asset_pipeline": self._forge_public_asset_pipeline(create.body["suitspec"]),
                "links": {
                    "quest_recall": f"/v1/quest/recall/{recall_code}",
                    "quest_viewer": f"/viewer/quest-iw-demo/?code={recall_code}&newRoute=1",
                },
            },
        )

    def get_suit_by_recall_code(self, recall_code: str) -> ApiResponse:
        try:
            code = normalize_recall_code(recall_code)
        except ValueError as exc:
            return self._bad_request(str(exc))
        suit_id = self._find_suit_id_by_recall_code(code)
        if suit_id is None:
            return ApiResponse(status=HTTPStatus.NOT_FOUND, body={"ok": False, "error": f"Unknown recall_code: {code}"})
        response = self.get_suit(suit_id)
        if response.body.get("ok"):
            response.body["recall_code"] = self._recall_code_from_suit(response.body.get("suit", {})) or code
        return response

    def get_quest_recall(self, recall_code: str) -> ApiResponse:
        try:
            code = normalize_recall_code(recall_code)
        except ValueError as exc:
            return self._bad_request(str(exc))
        suit_id = self._find_suit_id_by_recall_code(code)
        if suit_id is None:
            return ApiResponse(status=HTTPStatus.NOT_FOUND, body={"ok": False, "error": f"Unknown recall_code: {code}"})
        suit_path = self._suit_path(suit_id)
        suitspec_path = self._suitspec_path(suit_id)
        if not suit_path.exists():
            return ApiResponse(status=HTTPStatus.NOT_FOUND, body={"ok": False, "error": f"Unknown recall_code: {code}"})

        suit = self._read_json(suit_path)
        canonical_code = self._recall_code_from_suit(suit) or code
        suitspec = self._read_json(suitspec_path) if suitspec_path.exists() else None
        metadata = suit.get("metadata") if isinstance(suit.get("metadata"), dict) else {}
        manifest_id = suit.get("manifest_id")
        manifest = None
        if isinstance(manifest_id, str):
            manifest_response = self.get_manifest(manifest_id)
            if manifest_response.status == HTTPStatus.OK:
                manifest = manifest_response.body["manifest"]
        runtime_suit = {
            "suit_id": suit_id,
            "recall_code": canonical_code,
            "display_name": metadata.get("display_name") or "",
            "status": suit.get("status", "DRAFT"),
            "manifest_id": manifest_id if isinstance(manifest_id, str) else None,
        }
        return ApiResponse(
            status=HTTPStatus.OK,
            body={
                "ok": True,
                "recall_code": canonical_code,
                "suit_id": suit_id,
                "display_name": runtime_suit["display_name"],
                "status": runtime_suit["status"],
                "manifest_id": runtime_suit["manifest_id"],
                "suitspec_ready": suitspec is not None,
                "manifest_ready": manifest is not None,
                "suit": runtime_suit,
                "suitspec": suitspec,
                "manifest": manifest,
                "links": {
                    "suit": f"/v1/suits/{suit_id}",
                    "manifest": f"/v1/suits/{suit_id}/manifest",
                },
            },
        )

    def get_suit(self, suit_id: str) -> ApiResponse:
        if not _SUIT_ID_RE.fullmatch(suit_id):
            return self._bad_request("suit_id format is invalid")
        suit_path = self._suit_path(suit_id)
        suitspec_path = self._suitspec_path(suit_id)
        if not suit_path.exists():
            return ApiResponse(status=HTTPStatus.NOT_FOUND, body={"ok": False, "error": f"Unknown suit: {suit_id}"})
        suit = self._read_json(suit_path)
        return ApiResponse(
            status=HTTPStatus.OK,
            body={
                "ok": True,
                "suit": suit,
                "suitspec": self._read_json(suitspec_path) if suitspec_path.exists() else None,
                "recall_code": self._recall_code_from_suit(suit),
            },
        )

    def get_latest_suit_manifest(self, suit_id: str) -> ApiResponse:
        if not _SUIT_ID_RE.fullmatch(suit_id):
            return self._bad_request("suit_id format is invalid")
        suit_path = self._suit_path(suit_id)
        if not suit_path.exists():
            return ApiResponse(status=HTTPStatus.NOT_FOUND, body={"ok": False, "error": f"Unknown suit: {suit_id}"})
        suit = self._read_json(suit_path)
        manifest_id = suit.get("manifest_id")
        if not isinstance(manifest_id, str):
            return ApiResponse(status=HTTPStatus.NOT_FOUND, body={"ok": False, "error": f"No manifest for suit: {suit_id}"})
        return self.get_manifest(manifest_id)

    def attach_manifest(self, suit_id: str, payload: dict[str, Any]) -> ApiResponse:
        if not _SUIT_ID_RE.fullmatch(suit_id):
            return self._bad_request("suit_id format is invalid")
        suit_path = self._suit_path(suit_id)
        suitspec_path = self._suitspec_path(suit_id)
        if not suit_path.exists() or not suitspec_path.exists():
            return ApiResponse(status=HTTPStatus.NOT_FOUND, body={"ok": False, "error": f"Unknown suit: {suit_id}"})
        if not isinstance(payload, dict):
            return self._bad_request("request body must be a JSON object")

        try:
            manifest = self._manifest_from_payload(suit_id, payload, suitspec_path)
        except ValueError as exc:
            return self._bad_request(str(exc))
        try:
            validate_against_schema(manifest, "suitmanifest")
        except ValueError as exc:
            return self._bad_request(str(exc))
        if manifest.get("suit_id") != suit_id:
            return self._bad_request("manifest.suit_id must match the URL suit_id")

        manifest_id = str(manifest["manifest_id"])
        manifest_path = self._manifest_path(suit_id, manifest_id)
        self._write_json(manifest_path, manifest)

        suit = self._read_json(suit_path)
        suit["manifest_id"] = manifest_id
        if "recall_code" not in suit:
            suit["recall_code"] = self._resolve_recall_code(None, suit_id=suit_id, previous_suit=suit)
        suit["status"] = manifest.get("status", suit.get("status", "DRAFT"))
        suit.setdefault("artifacts", {})["manifest_path"] = self._relative_path(manifest_path)
        suit.setdefault("metadata", {})["updated_at"] = self._utc_now()
        self._write_json(suit_path, suit)

        return ApiResponse(
            status=HTTPStatus.CREATED,
            body={
                "ok": True,
                "suit_id": suit_id,
                "manifest_id": manifest_id,
                "manifest_path": self._relative_path(manifest_path),
                "suit": suit,
                "manifest": manifest,
                "storage": self._storage_info(manifest_path),
            },
        )

    def create_trial(self, payload: dict[str, Any]) -> ApiResponse:
        if not isinstance(payload, dict):
            return self._bad_request("request body must be a JSON object")
        suit_id = str(payload.get("suit_id") or "")
        manifest_id = payload.get("manifest_id")
        if manifest_id is not None and not isinstance(manifest_id, str):
            return self._bad_request("manifest_id must be a string")
        if manifest_id is not None and not _MANIFEST_ID_RE.fullmatch(manifest_id):
            return self._bad_request("manifest_id format is invalid")

        if suit_id:
            if not _SUIT_ID_RE.fullmatch(suit_id):
                return self._bad_request("suit_id format is invalid")
            suit_path = self._suit_path(suit_id)
            if not suit_path.exists():
                return ApiResponse(status=HTTPStatus.NOT_FOUND, body={"ok": False, "error": f"Unknown suit: {suit_id}"})
            suit = self._read_json(suit_path)
            manifest_id = manifest_id or suit.get("manifest_id")
            if not isinstance(manifest_id, str):
                return ApiResponse(status=HTTPStatus.CONFLICT, body={"ok": False, "error": f"No manifest for suit: {suit_id}"})

        if not isinstance(manifest_id, str):
            return self._bad_request("manifest_id or suit_id with a saved manifest is required")
        manifest_response = self.get_manifest(manifest_id)
        if manifest_response.status != HTTPStatus.OK:
            return manifest_response
        manifest = manifest_response.body["manifest"]
        manifest_suit_id = str(manifest.get("suit_id") or "")
        if suit_id and manifest_suit_id != suit_id:
            return self._bad_request("manifest.suit_id must match suit_id")
        suit_id = suit_id or manifest_suit_id

        session_id = str(payload.get("session_id") or self._generate_session_id())
        if not _SESSION_ID_RE.fullmatch(session_id):
            return self._bad_request("session_id format is invalid")
        session_path = self._trial_path(session_id)
        if session_path.exists():
            return ApiResponse(status=HTTPStatus.CONFLICT, body={"ok": False, "error": f"Trial already exists: {session_id}"})

        state = str(payload.get("state") or "POSTED")
        if state not in _TRANSFORM_STATES:
            return self._bad_request(f"state must be one of {sorted(_TRANSFORM_STATES)}")
        tracking_source = str(payload.get("tracking_source") or "manual")
        now = self._utc_now()
        session = {
            "schema_version": "0.1",
            "session_id": session_id,
            "manifest_id": manifest_id,
            "suit_id": suit_id,
            "operator_id": payload.get("operator_id"),
            "device_id": payload.get("device_id"),
            "tracking_source": tracking_source,
            "state": state,
            "started_at": now,
            "events": [
                {
                    "event_id": self._generate_event_id(now),
                    "session_id": session_id,
                    "sequence": 0,
                    "event_type": "SESSION_CREATED",
                    "occurred_at": now,
                    "actor": {"type": "system"},
                    "state_after": state,
                    "payload": {"source": "new-route-api", "manifest_id": manifest_id},
                }
            ],
            "artifacts": {},
            "metadata": {"created_at": now, "updated_at": now},
        }
        session = self._strip_none(session)
        try:
            validate_against_schema(session, "transform-session")
        except ValueError as exc:
            return self._bad_request(str(exc))
        self._write_json(session_path, session)
        return ApiResponse(
            status=HTTPStatus.CREATED,
            body={
                "ok": True,
                "trial_id": session_id,
                "session_id": session_id,
                "session": session,
                "trial": session,
                "trial_path": self._relative_path(session_path),
                "links": {
                    "events": f"/v1/trials/{session_id}/events",
                    "replay": f"/v1/trials/{session_id}/replay",
                },
                "storage": self._storage_info(session_path),
            },
        )

    def get_trial(self, session_id: str) -> ApiResponse:
        if not _SESSION_ID_RE.fullmatch(session_id):
            return self._bad_request("session_id format is invalid")
        session_path = self._trial_path(session_id)
        if not session_path.exists():
            return ApiResponse(status=HTTPStatus.NOT_FOUND, body={"ok": False, "error": f"Unknown trial: {session_id}"})
        return ApiResponse(status=HTTPStatus.OK, body={"ok": True, "trial": self._read_json(session_path)})

    def list_trials(self) -> ApiResponse:
        trials = self._all_trials()
        return ApiResponse(
            status=HTTPStatus.OK,
            body={
                "ok": True,
                "count": len(trials),
                "latest": self._trial_summary(trials[0]) if trials else None,
                "trials": [self._trial_summary(trial) for trial in trials],
            },
        )

    def get_latest_trial(self) -> ApiResponse:
        trials = self._all_trials()
        if not trials:
            return ApiResponse(status=HTTPStatus.NOT_FOUND, body={"ok": False, "error": "No trials have been recorded"})
        latest = trials[0]
        session_id = str(latest["session_id"])
        return ApiResponse(
            status=HTTPStatus.OK,
            body={
                "ok": True,
                "trial_id": session_id,
                "summary": self._trial_summary(latest),
                "trial": latest,
                "links": {
                    "self": f"/v1/trials/{session_id}",
                    "replay": f"/v1/trials/{session_id}/replay",
                },
            },
        )

    def get_trial_replay(self, session_id: str) -> ApiResponse:
        if not _SESSION_ID_RE.fullmatch(session_id):
            return self._bad_request("session_id format is invalid")
        session_path = self._trial_path(session_id)
        if not session_path.exists():
            return ApiResponse(status=HTTPStatus.NOT_FOUND, body={"ok": False, "error": f"Unknown trial: {session_id}"})

        session = self._read_json(session_path)
        events = session.get("events", [])
        if not events:
            return ApiResponse(status=HTTPStatus.CONFLICT, body={"ok": False, "error": "Replay requires at least one event"})

        replay = self._build_replay_script(session)
        try:
            validate_against_schema(replay, "replay-script")
        except ValueError as exc:
            return self._bad_request(str(exc))
        replay_path = self._replay_path(session_id)
        self._write_json(replay_path, replay)

        session.setdefault("artifacts", {})["replay_script_path"] = self._relative_path(replay_path)
        session.setdefault("metadata", {})["updated_at"] = self._utc_now()
        try:
            validate_against_schema(session, "transform-session")
        except ValueError as exc:
            return self._bad_request(str(exc))
        self._write_json(session_path, session)

        return ApiResponse(
            status=HTTPStatus.OK,
            body={
                "ok": True,
                "trial_id": session_id,
                "replay_id": replay["replay_id"],
                "replay": replay,
                "replay_path": self._relative_path(replay_path),
                "session": session,
                "storage": self._storage_info(replay_path),
            },
        )

    def append_trial_event(self, session_id: str, payload: dict[str, Any]) -> ApiResponse:
        if not _SESSION_ID_RE.fullmatch(session_id):
            return self._bad_request("session_id format is invalid")
        session_path = self._trial_path(session_id)
        if not session_path.exists():
            return ApiResponse(status=HTTPStatus.NOT_FOUND, body={"ok": False, "error": f"Unknown trial: {session_id}"})
        if not isinstance(payload, dict):
            return self._bad_request("request body must be a JSON object")

        session = self._read_json(session_path)
        events = session.setdefault("events", [])
        idempotency_key = payload.get("idempotency_key")
        if isinstance(idempotency_key, str):
            for event in events:
                if event.get("idempotency_key") == idempotency_key:
                    return ApiResponse(status=HTTPStatus.OK, body={"ok": True, "event": event, "trial": session})

        now = str(payload.get("occurred_at") or self._utc_now())
        event_id = str(payload.get("event_id") or self._generate_event_id(now))
        if not _EVENT_ID_RE.fullmatch(event_id):
            return self._bad_request("event_id format is invalid")
        event_type = str(payload.get("event_type") or "STATE_TRANSITION")
        if event_type not in _TRANSFORM_EVENT_TYPES:
            return self._bad_request(f"event_type must be one of {sorted(_TRANSFORM_EVENT_TYPES)}")

        state_before = str(session["state"])
        requested_state_after = str(payload.get("state_after") or state_before)
        if requested_state_after not in _TRANSFORM_STATES:
            return self._bad_request(f"state_after must be one of {sorted(_TRANSFORM_STATES)}")
        state_after = self._non_regressive_state_after(state_before, requested_state_after)

        actor = payload.get("actor") or {"type": "system"}
        if not isinstance(actor, dict):
            return self._bad_request("actor must be a JSON object")
        event_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
        event_payload = self._clone_json(event_payload)
        if state_after != requested_state_after:
            event_payload.setdefault("requested_state_after", requested_state_after)
            event_payload.setdefault("state_transition_note", "ignored_regressive_state_after")
        event = {
            "event_id": event_id,
            "session_id": session_id,
            "sequence": len(events),
            "event_type": event_type,
            "occurred_at": now,
            "actor": actor,
            "state_before": state_before,
            "state_after": state_after,
            "payload": event_payload,
        }
        if isinstance(idempotency_key, str):
            event["idempotency_key"] = idempotency_key

        events.append(event)
        session["state"] = state_after
        if state_after in {"ACTIVE", "ARCHIVED", "REFUSED"}:
            session["completed_at"] = now
        session.setdefault("metadata", {})["updated_at"] = now
        try:
            validate_against_schema(session, "transform-session")
        except ValueError as exc:
            return self._bad_request(str(exc))
        self._write_json(session_path, session)
        return ApiResponse(
            status=HTTPStatus.CREATED,
            body={"ok": True, "trial_id": session_id, "event": event, "session": session, "trial": session},
        )

    def get_part_catalog(self) -> ApiResponse:
        catalog = self._load_json("examples/partcatalog.seed.json")
        validate_against_schema(catalog, "partcatalog")
        return ApiResponse(
            status=HTTPStatus.OK,
            body={
                "ok": True,
                "catalog_id": catalog["catalog_id"],
                "schema_version": catalog["schema_version"],
                "status": catalog["status"],
                "parts": catalog["parts"],
                "material_slots": catalog["material_slots"],
                "runtime_contract": catalog.get("runtime_contract", {}),
            },
        )

    def get_manifest(self, manifest_id: str) -> ApiResponse:
        if not manifest_id:
            return ApiResponse(status=HTTPStatus.BAD_REQUEST, body={"ok": False, "error": "manifest_id is required"})
        if not _MANIFEST_ID_RE.fullmatch(manifest_id):
            return self._bad_request("manifest_id format is invalid")

        local_manifest_path = self._find_manifest_path(manifest_id)
        if local_manifest_path is not None:
            manifest = self._read_json(local_manifest_path)
            validate_against_schema(manifest, "suitmanifest")
            return ApiResponse(status=HTTPStatus.OK, body={"ok": True, "manifest": manifest})

        manifest = self._load_json("examples/suitmanifest.sample.json")
        validate_against_schema(manifest, "suitmanifest")
        if manifest.get("manifest_id") != manifest_id:
            return ApiResponse(
                status=HTTPStatus.NOT_FOUND,
                body={"ok": False, "error": f"Unknown manifest: {manifest_id}"},
            )
        return ApiResponse(status=HTTPStatus.OK, body={"ok": True, "manifest": manifest})

    def get(self, path: str) -> ApiResponse | None:
        normalized = "/" + path.strip("/")
        if normalized == "/health":
            return self.health()
        if normalized == "/v1/catalog/parts":
            return self.get_part_catalog()
        if normalized == "/v1/trials":
            return self.list_trials()
        if normalized == "/v1/trials/latest":
            return self.get_latest_trial()
        quest_recall_prefix = "/v1/quest/recall/"
        if normalized.startswith(quest_recall_prefix):
            return self.get_quest_recall(normalized[len(quest_recall_prefix) :])
        prefix = "/v1/manifests/"
        if normalized.startswith(prefix):
            return self.get_manifest(normalized[len(prefix) :])
        suit_prefix = "/v1/suits/"
        if normalized.startswith(suit_prefix):
            suffix = normalized[len(suit_prefix) :]
            code_prefix = "code/"
            if suffix.startswith(code_prefix):
                return self.get_suit_by_recall_code(suffix[len(code_prefix) :])
            if suffix.endswith("/manifest"):
                return self.get_latest_suit_manifest(suffix[: -len("/manifest")])
            return self.get_suit(suffix)
        trial_prefix = "/v1/trials/"
        if normalized.startswith(trial_prefix):
            suffix = normalized[len(trial_prefix) :]
            if suffix.endswith("/replay"):
                return self.get_trial_replay(suffix[: -len("/replay")])
            return self.get_trial(suffix)
        return None

    def post(self, path: str, payload: dict[str, Any]) -> ApiResponse | None:
        normalized = "/" + path.strip("/")
        if normalized == "/v1/suits/forge":
            return self.forge_suit(payload)
        if normalized == "/v1/suits/issue-id":
            return self.issue_suit_id(payload)
        if normalized == "/v1/suits":
            return self.create_suit(payload)
        if normalized == "/v1/trials":
            return self.create_trial(payload)
        prefix = "/v1/suits/"
        suffix = normalized[len(prefix) :] if normalized.startswith(prefix) else ""
        if suffix.endswith("/manifest"):
            suit_id = suffix[: -len("/manifest")]
            return self.attach_manifest(suit_id, payload)
        trial_prefix = "/v1/trials/"
        trial_suffix = normalized[len(trial_prefix) :] if normalized.startswith(trial_prefix) else ""
        if trial_suffix.endswith("/events"):
            session_id = trial_suffix[: -len("/events")]
            return self.append_trial_event(session_id, payload)
        return None

    def _load_json(self, rel_path: str) -> dict[str, Any]:
        target = (self.repo_root / rel_path).resolve()
        try:
            target.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError(f"Path is outside repository root: {rel_path}") from exc
        return json.loads(target.read_text(encoding="utf-8"))

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(path)

    def _suit_path(self, suit_id: str) -> Path:
        return self.suit_store_root / suit_id / "suit.json"

    def _suitspec_path(self, suit_id: str) -> Path:
        return self.suit_store_root / suit_id / "suitspec.json"

    def _manifest_path(self, suit_id: str, manifest_id: str) -> Path:
        return self.suit_store_root / suit_id / "manifests" / f"{manifest_id}.json"

    def _trial_path(self, session_id: str) -> Path:
        return self.trial_store_root / session_id / "transform-session.json"

    def _replay_path(self, session_id: str) -> Path:
        return self.trial_store_root / session_id / "replay-script.json"

    def _find_manifest_path(self, manifest_id: str) -> Path | None:
        if not self.suit_store_root.exists():
            return None
        for path in self.suit_store_root.glob(f"*/manifests/{manifest_id}.json"):
            return path
        return None

    def _find_suit_id_by_recall_code(self, recall_code: str) -> str | None:
        code = normalize_recall_code(recall_code)
        if not self.suit_store_root.exists():
            return None
        fuzzy_matches: list[str] = []
        lookup_key = self._recall_ambiguity_key(code)
        for path in self.suit_store_root.glob("*/suit.json"):
            suit = self._read_json(path)
            suit_code = self._recall_code_from_suit(suit)
            if suit_code == code:
                return str(suit.get("suit_id") or path.parent.name)
            if suit_code and self._recall_ambiguity_key(suit_code) == lookup_key:
                fuzzy_matches.append(str(suit.get("suit_id") or path.parent.name))
        unique_matches = sorted(set(fuzzy_matches))
        if len(unique_matches) == 1:
            return unique_matches[0]
        return None

    def _recall_ambiguity_key(self, recall_code: str) -> str:
        return normalize_recall_code(recall_code).translate(_RECALL_AMBIGUOUS_TRANSLATION)

    def _all_recall_codes(self, *, exclude_suit_id: str | None = None) -> list[str]:
        if not self.suit_store_root.exists():
            return []
        codes = []
        for path in self.suit_store_root.glob("*/suit.json"):
            suit = self._read_json(path)
            if exclude_suit_id and str(suit.get("suit_id") or path.parent.name) == exclude_suit_id:
                continue
            code = self._recall_code_from_suit(suit)
            if code:
                codes.append(code)
        return codes

    def _recall_code_from_suit(self, suit: dict[str, Any]) -> str | None:
        metadata = suit.get("metadata") if isinstance(suit.get("metadata"), dict) else {}
        issue = metadata.get("issue") if isinstance(metadata.get("issue"), dict) else {}
        for value in (suit.get("recall_code"), metadata.get("recall_code"), issue.get("recall_code")):
            if not value:
                continue
            try:
                return normalize_recall_code(str(value))
            except ValueError:
                continue
        return None

    def _resolve_recall_code(self, value: Any, *, suit_id: str, previous_suit: dict[str, Any] | None = None) -> str:
        previous_code = self._recall_code_from_suit(previous_suit or {})
        if value is None or str(value).strip() == "":
            if previous_code:
                return previous_code
            existing_codes = self._all_recall_codes(exclude_suit_id=suit_id)
            for _ in range(128):
                code = next_recall_code(existing_codes)
                if self._find_suit_id_by_recall_code(code) is None:
                    return code
                existing_codes.append(code)
            raise ValueError("Unable to allocate a unique recall_code")
        code = normalize_recall_code(str(value))
        owner = self._find_suit_id_by_recall_code(code)
        if owner is not None and owner != suit_id:
            raise ValueError(f"recall_code already exists: {code}")
        return code

    def _forge_suitspec_from_payload(self, payload: dict[str, Any], *, suit_id: str, display_name: str) -> dict[str, Any]:
        suitspec = self._clone_json(self._load_json("examples/suitspec.sample.json"))
        suitspec["suit_id"] = suit_id
        suitspec["approval_id"] = generate_approval_id()
        suitspec["morphotype_id"] = generate_morphotype_id()
        suitspec["palette"] = self._forge_palette(payload.get("palette"), suitspec.get("palette", {}))
        suitspec["operator_profile"] = self._forge_operator_profile(payload)
        suitspec["body_profile"] = self._forge_body_profile(payload)
        suitspec["style_tags"] = self._forge_style_tags(payload)
        suitspec["generation"] = self._forge_generation(payload, suitspec["style_tags"], suitspec["body_profile"])
        suitspec["text"] = self._forge_text(payload, display_name)

        enabled_parts = self._forge_enabled_parts(payload)
        modules = suitspec.get("modules")
        if not isinstance(modules, dict):
            raise ValueError("forge template modules must be a JSON object")
        for part_name, module in modules.items():
            if not isinstance(module, dict):
                continue
            module["enabled"] = part_name in enabled_parts
            module.pop("texture_path", None)
        return suitspec

    def _forge_palette(self, value: Any, fallback: dict[str, Any]) -> dict[str, str]:
        payload = value if isinstance(value, dict) else {}
        return {
            "primary": self._forge_color(payload.get("primary"), fallback.get("primary", "#F4F1E8")),
            "secondary": self._forge_color(payload.get("secondary"), fallback.get("secondary", "#8C96A3")),
            "emissive": self._forge_color(payload.get("emissive"), fallback.get("emissive", "#D8F7FF")),
        }

    def _forge_color(self, value: Any, fallback: Any) -> str:
        text = str(value or fallback or "").strip()
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", text):
            return text.upper()
        raise ValueError(f"color must be #RRGGBB: {text}")

    def _forge_body_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile = payload.get("body_profile") if isinstance(payload.get("body_profile"), dict) else {}
        raw_height = payload.get("height_cm", profile.get("height_cm", _FORGE_DEFAULT_HEIGHT_CM))
        try:
            height_cm = round(float(raw_height), 1)
        except (TypeError, ValueError) as exc:
            raise ValueError("height_cm must be a number") from exc
        if not (_FORGE_MIN_HEIGHT_CM <= height_cm <= _FORGE_MAX_HEIGHT_CM):
            raise ValueError(f"height_cm must be between {int(_FORGE_MIN_HEIGHT_CM)} and {int(_FORGE_MAX_HEIGHT_CM)}")
        return {
            "height_cm": height_cm,
            "source": "web_forge_declared",
            "vrm_baseline_ref": str(profile.get("vrm_baseline_ref") or _FORGE_VRM_BASELINE_REF),
            "fit_note": "Declared height scales the Web armor stand and seeds later body-fit calibration.",
        }

    def _forge_operator_profile(self, payload: dict[str, Any]) -> dict[str, str]:
        profile = payload.get("operator_profile") if isinstance(payload.get("operator_profile"), dict) else {}
        archetype = str(payload.get("archetype") or profile.get("protect_archetype") or "citizens").strip()[:40]
        temperament = str(payload.get("temperament") or profile.get("temperament_bias") or "calm").strip()[:40]
        mood = str(payload.get("color_mood") or profile.get("color_mood") or "clear_white").strip()[:40]
        note = str(payload.get("brief") or profile.get("note") or "Web forge base-suit overlay request.").strip()[:180]
        return {
            "protect_archetype": archetype or "citizens",
            "temperament_bias": temperament or "calm",
            "color_mood": mood or "clear_white",
            "note": note or "Web forge base-suit overlay request.",
        }

    def _forge_style_tags(self, payload: dict[str, Any]) -> list[str]:
        raw_tags = payload.get("style_tags")
        tags = []
        if isinstance(raw_tags, list):
            tags.extend(str(tag).strip() for tag in raw_tags if str(tag).strip())
        motif = str(payload.get("motif") or payload.get("archetype") or "guardian").strip()
        tags.extend(["base_suit", "armor_overlay", motif])
        cleaned = []
        for tag in tags:
            normalized = "".join(ch for ch in tag.lower().replace(" ", "_") if ch.isalnum() or ch in {"_", "-"})
            if normalized and normalized not in cleaned:
                cleaned.append(normalized[:32])
        return cleaned[:12] or ["base_suit", "armor_overlay"]

    def _forge_generation(
        self,
        payload: dict[str, Any],
        style_tags: list[str],
        body_profile: dict[str, Any],
    ) -> dict[str, Any]:
        brief = str(payload.get("brief") or "Generate a fitted base suit with selected armor overlays.").strip()
        enabled_parts = sorted(self._forge_enabled_parts(payload))
        prompt = (
            f"{brief} "
            f"Declared wearer height: {body_profile['height_cm']}cm. "
            f"Style tags: {', '.join(style_tags)}. "
            "Preserve the lore: Web establishes the suit, Quest performs the transformation trial, replay preserves it."
        )
        texture_plan = {
            "provider_profile": _FORGE_TEXTURE_PROVIDER_PROFILE,
            "texture_mode": _FORGE_TEXTURE_MODE,
            "uv_refine": _FORGE_UV_REFINE,
            "update_suitspec": True,
            "use_cache": True,
            "target_resolution": "2K",
            "discipline": ["uv_guide_reference", "flat_texture_atlas", "part_catalog_resolved"],
        }
        model_plan = {
            "asset_contract": _FORGE_ASSET_CONTRACT,
            "base_suit": "VRM baseline body-fit substrate",
            "overlay_parts": enabled_parts,
            "runtime_target": "validated GLB/gltf derived artifact",
            "material_slots": ["base_surface", "accent", "emissive", "trim"],
        }
        return {
            "model_id": "local-web-forge-v0",
            "prompt": prompt[:1200],
            "body_profile": body_profile,
            "model_plan": model_plan,
            "texture_plan": texture_plan,
            "planned_quality_gates": ["mesh_bounds", "fit_clearance", "uv_contract", "quest_recall_ready"],
            "quality_policy": {
                "texture_quality": "warning_only_until_generation_completes",
                "blocking_gate": "quest_recall_ready",
            },
            "job_defaults": {
                "provider_profile": texture_plan["provider_profile"],
                "texture_mode": texture_plan["texture_mode"],
                "uv_refine": texture_plan["uv_refine"],
                "update_suitspec": texture_plan["update_suitspec"],
                "use_cache": texture_plan["use_cache"],
                "priority_mode": "exhibition",
                "parts": enabled_parts,
                "generation_brief": prompt[:1200],
                "requires": ["server_resolved_suitspec_path"],
            },
            "part_prompts": {
                part: f"{part} armor overlay, compatible with a fitted base suit and mesh-UV texture atlas"
                for part in enabled_parts
            },
        }

    def _forge_text(self, payload: dict[str, Any], display_name: str) -> dict[str, Any]:
        callout = str(payload.get("callout") or display_name or "Web forge suit").strip()[:120]
        return {
            "callout": callout,
            "deposition_log_lines": [
                "Web forge accepted the operator parameters.",
                "Base suit substrate locked.",
                "Armor overlay manifest ready for Quest recall.",
            ],
        }

    def _forge_public_preview(self, suitspec: dict[str, Any]) -> dict[str, Any]:
        modules = suitspec.get("modules") if isinstance(suitspec.get("modules"), dict) else {}
        preview_modules = {}
        for part_name, module in modules.items():
            if not isinstance(module, dict):
                continue
            record = {
                "enabled": bool(module.get("enabled")),
                "asset_ref": module.get("asset_ref"),
            }
            for key in ("fit", "vrm_anchor", "attachment_slot"):
                if key in module:
                    record[key] = self._clone_json(module[key])
            preview_modules[part_name] = record
        return {
            "palette": self._clone_json(suitspec.get("palette", {})),
            "body_profile": self._clone_json(suitspec.get("body_profile", {})),
            "asset_pipeline": self._forge_public_asset_pipeline(suitspec),
            "modules": preview_modules,
        }

    def _forge_public_asset_pipeline(self, suitspec: dict[str, Any]) -> dict[str, Any]:
        generation = suitspec.get("generation") if isinstance(suitspec.get("generation"), dict) else {}
        model_plan = generation.get("model_plan") if isinstance(generation.get("model_plan"), dict) else {}
        texture_plan = generation.get("texture_plan") if isinstance(generation.get("texture_plan"), dict) else {}
        job_defaults = generation.get("job_defaults") if isinstance(generation.get("job_defaults"), dict) else {}
        planned_quality_gates = (
            generation.get("planned_quality_gates") if isinstance(generation.get("planned_quality_gates"), list) else []
        )
        quality_policy = generation.get("quality_policy") if isinstance(generation.get("quality_policy"), dict) else {}
        return {
            "model_plan": self._clone_json(model_plan),
            "texture_plan": self._clone_json(texture_plan),
            "job_defaults": self._clone_json(job_defaults),
            "planned_quality_gates": self._clone_json(planned_quality_gates),
            "quality_policy": self._clone_json(quality_policy),
        }

    def _forge_enabled_parts(self, payload: dict[str, Any]) -> set[str]:
        modules = self._load_json("examples/suitspec.sample.json").get("modules", {})
        allowed = set(modules.keys()) if isinstance(modules, dict) else set()
        raw_parts = payload.get("parts")
        if isinstance(raw_parts, list):
            selected = {str(part).strip() for part in raw_parts if str(part).strip()}
        else:
            selected = set(_FORGE_DEFAULT_PARTS)
        unknown = sorted(part for part in selected if part not in allowed)
        if unknown:
            raise ValueError(f"unknown forge parts: {unknown}")
        return (selected | _FORGE_REQUIRED_PARTS) & allowed

    def _discard_suit(self, suit_id: str) -> None:
        target = (self.suit_store_root / suit_id).resolve()
        root = self.suit_store_root.resolve()
        if target.parent != root or not _SUIT_ID_RE.fullmatch(suit_id):
            raise ValueError(f"refusing to discard invalid suit path: {suit_id}")
        if target.exists():
            shutil.rmtree(target)

    def _all_suit_ids(self) -> list[str]:
        if not self.suit_store_root.exists():
            return []
        suit_ids = set()
        for path in self.suit_store_root.iterdir():
            if path.is_dir() and _SUIT_ID_RE.fullmatch(path.name):
                suit_ids.add(path.name)
        return sorted(suit_ids)

    def _all_trials(self) -> list[dict[str, Any]]:
        if not self.trial_store_root.exists():
            return []
        trials = [self._read_json(path) for path in self.trial_store_root.glob("*/transform-session.json")]
        return sorted(trials, key=self._trial_sort_key, reverse=True)

    def _trial_sort_key(self, trial: dict[str, Any]) -> str:
        metadata = trial.get("metadata") if isinstance(trial.get("metadata"), dict) else {}
        return str(metadata.get("updated_at") or trial.get("completed_at") or trial.get("started_at") or "")

    def _trial_summary(self, trial: dict[str, Any]) -> dict[str, Any]:
        events = trial.get("events") if isinstance(trial.get("events"), list) else []
        artifacts = trial.get("artifacts") if isinstance(trial.get("artifacts"), dict) else {}
        metadata = trial.get("metadata") if isinstance(trial.get("metadata"), dict) else {}
        last_event = events[-1] if events and isinstance(events[-1], dict) else {}
        return {
            "session_id": trial.get("session_id"),
            "suit_id": trial.get("suit_id"),
            "manifest_id": trial.get("manifest_id"),
            "state": trial.get("state"),
            "event_count": len(events),
            "last_event_type": last_event.get("event_type"),
            "replay_script_path": artifacts.get("replay_script_path"),
            "updated_at": metadata.get("updated_at") or trial.get("completed_at") or trial.get("started_at"),
        }

    def _non_regressive_state_after(self, state_before: str, requested_state_after: str) -> str:
        before_rank = _TRANSFORM_STATE_RANK.get(state_before, -1)
        requested_rank = _TRANSFORM_STATE_RANK.get(requested_state_after, before_rank)
        if requested_rank < before_rank:
            return state_before
        return requested_state_after

    def _relative_path(self, path: Path) -> str:
        resolved = path.resolve()
        try:
            return resolved.relative_to(self.repo_root).as_posix()
        except ValueError:
            return resolved.as_posix()

    def _storage_info(self, path: Path) -> dict[str, str]:
        return {"backend": "local-json", "path": self._relative_path(path)}

    def _display_name(self, value: Any) -> str:
        text = str(value or "").strip()
        return text[:80]

    def _bad_request(self, message: str) -> ApiResponse:
        return ApiResponse(status=HTTPStatus.BAD_REQUEST, body={"ok": False, "error": message})

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _generate_session_id(self) -> str:
        return f"S-TRIAL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex.upper()[:6]}"

    def _generate_event_id(self, occurred_at: str) -> str:
        date = datetime.now(timezone.utc).strftime("%Y%m%d")
        try:
            date = datetime.fromisoformat(occurred_at.replace("Z", "+00:00")).strftime("%Y%m%d")
        except ValueError:
            pass
        return f"EVT-{date}-{uuid.uuid4().hex.upper()[:6]}"

    def _build_replay_script(self, session: dict[str, Any]) -> dict[str, Any]:
        events = session["events"]
        starts = [self._event_offset_seconds(events[0], event) for event in events]
        deposition_start_sec = next(
            (starts[idx] for idx, event in enumerate(events) if event.get("event_type") == "DEPOSITION_STARTED"),
            0.0,
        )
        timeline = []
        for idx, event in enumerate(events):
            timeline.append({
                "segment_id": f"SEG-{idx:04d}",
                "start_time_sec": starts[idx],
                "duration_sec": 0.5,
                "source_event_ids": [event["event_id"]],
                "actions": [self._replay_action_for_event(event, starts[idx])],
            })
            motion_segment = self._motion_replay_segment(event, starts[idx], deposition_start_sec, idx)
            if motion_segment:
                timeline.append(motion_segment)
        duration_sec = max((segment["start_time_sec"] + segment["duration_sec"] for segment in timeline), default=0)
        replay_id = self._build_replay_id(str(session["session_id"]), str(events[0]["occurred_at"]))
        return {
            "schema_version": "0.1",
            "replay_id": replay_id,
            "session_id": session["session_id"],
            "manifest_id": session["manifest_id"],
            "source_events": {
                "transform_session_schema_version": session["schema_version"],
                "event_ids": [event["event_id"] for event in events],
            },
            "duration_sec": duration_sec,
            "timeline": sorted(timeline, key=lambda segment: (segment["start_time_sec"], segment["segment_id"])),
            "metadata": {"created_at": self._utc_now(), "generator": "new-route-api"},
        }

    def _motion_replay_segment(
        self,
        event: dict[str, Any],
        event_start_sec: float,
        deposition_start_sec: float,
        index: int,
    ) -> dict[str, Any] | None:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            return None
        motion_capture = payload.get("motion_capture")
        if not isinstance(motion_capture, dict):
            return None
        frames = motion_capture.get("frames")
        if not isinstance(frames, list) or not frames:
            return None

        timebase = str(motion_capture.get("timebase") or "").lower()
        if timebase in {"event", "event_elapsed_sec"}:
            segment_start_sec = event_start_sec
        elif timebase in {"deposition", "deposition_elapsed_sec"}:
            segment_start_sec = deposition_start_sec
        elif event.get("event_type") in {"DEPOSITION_COMPLETED", "DEPOSITION_PROGRESS"}:
            segment_start_sec = deposition_start_sec
        else:
            segment_start_sec = event_start_sec

        normalized_frames: list[tuple[float, int, dict[str, Any]]] = []
        for original_index, frame in enumerate(frames[:_MAX_REPLAY_MOTION_FRAMES]):
            if not isinstance(frame, dict):
                continue
            try:
                frame_t = max(0.0, float(frame.get("t", 0.0)))
            except (TypeError, ValueError):
                frame_t = 0.0
            normalized_frames.append((frame_t, original_index, frame))
        if not normalized_frames:
            return None
        normalized_frames.sort(key=lambda item: (item[0], item[1]))

        actions: list[dict[str, Any]] = []
        last_t = 0.0
        for frame_t, _original_index, frame in normalized_frames:
            last_t = max(last_t, frame_t)
            actions.append({
                "action_type": "deposition_progress",
                "at_time_sec": round(segment_start_sec + frame_t, 3),
                "params": {
                    "event_type": "TRACKING_FRAME_BATCH",
                    "motion_capture_format": motion_capture.get("format", "unknown"),
                    "tracking": motion_capture.get("tracking"),
                    "timebase": timebase or "auto",
                    "coordinate_space": motion_capture.get("coordinate_space"),
                    "motion_frame": frame,
                },
            })
        if not actions:
            return None

        return {
            "segment_id": f"SEG-MOTION-{index:04d}",
            "start_time_sec": segment_start_sec,
            "duration_sec": round(last_t, 3),
            "source_event_ids": [event["event_id"]],
            "actions": actions,
        }

    def _event_offset_seconds(self, first_event: dict[str, Any], event: dict[str, Any]) -> float:
        try:
            first = datetime.fromisoformat(str(first_event["occurred_at"]).replace("Z", "+00:00"))
            current = datetime.fromisoformat(str(event["occurred_at"]).replace("Z", "+00:00"))
            return max(0.0, round((current - first).total_seconds(), 3))
        except ValueError:
            return float(event.get("sequence", 0))

    def _replay_action_for_event(self, event: dict[str, Any], at_time_sec: float) -> dict[str, Any]:
        event_type = str(event["event_type"])
        action_type = "state_marker"
        if event_type in {"VOICE_CAPTURED", "TRIGGER_DETECTED"}:
            action_type = "text"
        elif event_type in {"DEPOSITION_STARTED", "DEPOSITION_COMPLETED", "SEAL_VERIFIED"}:
            action_type = "fx"
        elif event_type == "DEPOSITION_PROGRESS":
            action_type = "deposition_progress"
        return {
            "action_type": action_type,
            "at_time_sec": at_time_sec,
            "params": {
                "event_type": event_type,
                "state_before": event.get("state_before"),
                "state_after": event.get("state_after"),
                "payload": self._replay_payload_summary(event.get("payload", {})),
            },
        }

    def _replay_payload_summary(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        summary = self._clone_json(payload)
        motion_capture = summary.get("motion_capture")
        if isinstance(motion_capture, dict) and isinstance(motion_capture.get("frames"), list):
            frames = motion_capture["frames"]
            compact_motion = {key: value for key, value in motion_capture.items() if key != "frames"}
            compact_motion["frame_count"] = len(frames)
            compact_motion["frames_ref"] = "timeline.deposition_progress.params.motion_frame"
            summary["motion_capture"] = compact_motion
        return summary

    def _build_replay_id(self, session_id: str, occurred_at: str) -> str:
        date = datetime.now(timezone.utc).strftime("%Y%m%d")
        try:
            date = datetime.fromisoformat(occurred_at.replace("Z", "+00:00")).strftime("%Y%m%d")
        except ValueError:
            pass
        digest = sha1(session_id.encode("utf-8")).hexdigest().upper()[:4]
        return f"RPL-{date}-{digest}"

    def _clone_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        return json.loads(json.dumps(payload, ensure_ascii=False))

    def _strip_none(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in payload.items() if value is not None}

    def _manifest_from_payload(self, suit_id: str, payload: dict[str, Any], suitspec_path: Path) -> dict[str, Any]:
        supplied_manifest = payload.get("manifest")
        if supplied_manifest is not None:
            if not isinstance(supplied_manifest, dict):
                raise ValueError("manifest must be a JSON object")
            return supplied_manifest

        status = str(payload.get("status") or "DRAFT")
        if status not in _SUIT_STATUSES:
            raise ValueError(f"status must be one of {sorted(_SUIT_STATUSES)}")
        manifest_id = payload.get("manifest_id")
        if manifest_id is not None and not isinstance(manifest_id, str):
            raise ValueError("manifest_id must be a string")
        projection_version = str(payload.get("projection_version") or "0.1")
        part_catalog = self._load_json("examples/partcatalog.seed.json")
        validate_against_schema(part_catalog, "partcatalog")
        suitspec = self._read_json(suitspec_path)
        if suitspec.get("suit_id") != suit_id:
            raise ValueError("stored suitspec.suit_id must match the URL suit_id")
        validate_suitspec(suitspec)
        return project_suitspec_to_manifest(
            suitspec,
            part_catalog=part_catalog,
            manifest_id=manifest_id,
            status=status,
            projection_version=projection_version,
        )
