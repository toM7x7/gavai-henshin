"""Phase 1 API contract skeleton for the GCP new route.

This module keeps the first API surface independent from the local dashboard
handler so the same contract can later be mirrored by a Cloud Run/Hono service.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Any

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
        suit = {
            "schema_version": "0.1",
            "suit_id": suit_id,
            "suitspec_schema_version": saved_suitspec["schema_version"],
            "status": previous_suit.get("status", "DRAFT"),
            "manifest_id": previous_suit.get("manifest_id"),
            "artifacts": {
                **previous_suit.get("artifacts", {}),
                "suitspec_path": self._relative_path(suitspec_path),
            },
            "metadata": {"created_at": now, "updated_at": now},
        }
        self._write_json(suitspec_path, saved_suitspec)
        self._write_json(suit_path, suit)
        return ApiResponse(
            status=HTTPStatus.CREATED,
            body={
                "ok": True,
                "suit_id": suit_id,
                "schema_version": saved_suitspec["schema_version"],
                "status": suit["status"],
                "suitspec_path": self._relative_path(suitspec_path),
                "links": {"manifest": f"/v1/suits/{suit_id}/manifest"},
                "suit": suit,
                "suitspec": saved_suitspec,
                "storage": self._storage_info(suitspec_path),
            },
        )

    def get_suit(self, suit_id: str) -> ApiResponse:
        if not _SUIT_ID_RE.fullmatch(suit_id):
            return self._bad_request("suit_id format is invalid")
        suit_path = self._suit_path(suit_id)
        suitspec_path = self._suitspec_path(suit_id)
        if not suit_path.exists() or not suitspec_path.exists():
            return ApiResponse(status=HTTPStatus.NOT_FOUND, body={"ok": False, "error": f"Unknown suit: {suit_id}"})
        return ApiResponse(
            status=HTTPStatus.OK,
            body={"ok": True, "suit": self._read_json(suit_path), "suitspec": self._read_json(suitspec_path)},
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
        state_after = str(payload.get("state_after") or state_before)
        if state_after not in _TRANSFORM_STATES:
            return self._bad_request(f"state_after must be one of {sorted(_TRANSFORM_STATES)}")

        actor = payload.get("actor") or {"type": "system"}
        if not isinstance(actor, dict):
            return self._bad_request("actor must be a JSON object")
        event = {
            "event_id": event_id,
            "session_id": session_id,
            "sequence": len(events),
            "event_type": event_type,
            "occurred_at": now,
            "actor": actor,
            "state_before": state_before,
            "state_after": state_after,
            "payload": payload.get("payload") if isinstance(payload.get("payload"), dict) else {},
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
        prefix = "/v1/manifests/"
        if normalized.startswith(prefix):
            return self.get_manifest(normalized[len(prefix) :])
        suit_prefix = "/v1/suits/"
        if normalized.startswith(suit_prefix):
            suffix = normalized[len(suit_prefix) :]
            if suffix.endswith("/manifest"):
                return self.get_latest_suit_manifest(suffix[: -len("/manifest")])
            return self.get_suit(suffix)
        trial_prefix = "/v1/trials/"
        if normalized.startswith(trial_prefix):
            suffix = normalized[len(trial_prefix) :]
            return self.get_trial(suffix)
        return None

    def post(self, path: str, payload: dict[str, Any]) -> ApiResponse | None:
        normalized = "/" + path.strip("/")
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

    def _find_manifest_path(self, manifest_id: str) -> Path | None:
        if not self.suit_store_root.exists():
            return None
        for path in self.suit_store_root.glob(f"*/manifests/{manifest_id}.json"):
            return path
        return None

    def _relative_path(self, path: Path) -> str:
        resolved = path.resolve()
        try:
            return resolved.relative_to(self.repo_root).as_posix()
        except ValueError:
            return resolved.as_posix()

    def _storage_info(self, path: Path) -> dict[str, str]:
        return {"backend": "local-json", "path": self._relative_path(path)}

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
