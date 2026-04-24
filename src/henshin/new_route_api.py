"""Phase 1 API contract skeleton for the GCP new route.

This module keeps the first API surface independent from the local dashboard
handler so the same contract can later be mirrored by a Cloud Run/Hono service.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any

from .validators import validate_against_schema


@dataclass(frozen=True, slots=True)
class ApiResponse:
    status: int
    body: dict[str, Any]


class NewRouteApi:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

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
        return None

    def _load_json(self, rel_path: str) -> dict[str, Any]:
        target = (self.repo_root / rel_path).resolve()
        try:
            target.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError(f"Path is outside repository root: {rel_path}") from exc
        return json.loads(target.read_text(encoding="utf-8"))
