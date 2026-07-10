# Web Service Phase 0 Task Breakdown - 2026-05-02

Updated: 2026-05-04 JST
Source: `docs/web-service-readiness-2026-05-02.md`

## Goal

Phase 0 is the contract hardening phase before GCP, PlayCanvas, or any larger service split. The current Python dashboard/API, static Web Forge, Quest Vite viewer, `viewer/assets`, Nanobanana, and SakuraAI integrations remain the working source. The job is to make that local system easy to move to an external exhibition PC and later to GCP without changing Web/Quest/Replay semantics.

Priority:

1. Freeze the Web Forge -> SuitSpec/Manifest -> 4-digit recall code -> Quest recall loop.
2. Keep local file paths, provider secrets, raw provider responses, and debug-only state out of public responses.
3. Introduce store/artifact boundaries that can swap local JSON/files for Cloud SQL/GCS later.
4. Verify the generated suit is visible in Web and recallable in Quest before serviceizing.
5. Preserve Replay anchors so the experience can be archived without re-running generation.

Current status to carry forward:

- Web/Quest runtime placement has a post-fix evidence code `3601` with `runtime-render-placement.v1`, 18 placements, selected variant identity, runtime rotation, and GLB gate checks.
- Quest `adb devices = unauthorized` is a headset trust/setup blocker. Resolve by accepting USB debugging before debugging API, port, or browser behavior.
- Final exhibition readiness requires an external Windows PC baseline, not only the current dev machine.

## Exhibition Preflight Split

Required local preflight:

- `local-pass` is prerequisite for visitor operation.
- `local-pass cannot be overridden` by GCP, PlayCanvas, mocopi, or any hosted
  service result.
- Core demo must run without live GCP, internet, provider secrets, or mocopi.
- External PC local baseline means Web/API on `8010`, Quest viewer on `5173`,
  fresh forge code, Quest recall, runtime package parity, no local-path leakage,
  and Replay portability.

Optional enhancement preflight:

- GCP/service exits as `service-pass/fail/not-included`. The service endpoint
  must pass the same forge, recall, replay, and no-local-path checks before it
  can be used as a service rehearsal.
- PlayCanvas exits as `playcanvas-pass/fail/not-included`. PlayCanvas must
  consume an exported runtime package snapshot and must not own variant,
  placement, code, or Replay truth. Before `playcanvas-pass`, run
  `python tools/validate_playcanvas_snapshot.py <runtime-package.snapshot.json> --report-json`.
- mocopi exits as `mocopi-GO/DEMO-ONLY/NO-GO/not-included`; mocopi cannot
  promote the visitor path unless the packaged-PC local baseline remains pass.

## Phase 0 Done Criteria

- `POST /v1/suits/forge` returns recall code, SuitSpec/SuitManifest identity, preview/artifact refs, schema version, catalog version, and runtime package version.
- `GET /v1/quest/recall/{code}` returns a Quest-usable payload for the active suit version.
- Recall payload includes `schema_version`, `catalog_version`, `artifact_base_url`, `cache_policy`, selected variants, render placements, and texture/model gates.
- Nanobanana generated assets are linked through suit version artifacts, not loose local files.
- SakuraAI/Nanobanana mock fallback and real provider output have the same public shape.
- `viewer/assets/armor-parts` is treated as a release seed with catalog version and source hash.
- Web and Quest smoke pass without hiding missing/corrupt GLBs through fallback rendering.
- `.env.example` and demo setup docs name Phase 0 environment variables without leaking secrets.
- External PC smoke can run Web/API on `8010`, Quest viewer on `5173`, generate a fresh code, recall it, and write or validate Replay artifacts.

## P0 Tasks

### P0-01: Public Contract Inventory

Purpose: list every field allowed in public Web, Quest, and Replay responses, and list what must never leave the server/operator surface.

Implementation:

- Inventory current Web Forge output, SuitSpec, SuitManifest, Quest recall payload, TransformSession, TransformEvent, and ReplayScript/ReplayRecord fields.
- Treat `/api/*` as compatibility and `/v1/*` as the new external contract lane.
- Remove or redact local paths, provider raw responses, debug state, and secrets from public response shapes.
- Assign each public field to one owner: suit, suit version, recall code, runtime package, artifact, trial, event, replay, or provider job.

Acceptance:

- `/v1/*` responses contain no `C:\...`, `file://`, provider tokens, raw provider payloads, or debug-only fields.
- A field inventory exists in docs or tests so later GCP/PlayCanvas work does not guess.
- Hosted/service rehearsals use the same smoke shape as local:

```powershell
python tools/exhibition_smoke_check.py --code 3601 --service-api-base https://<service-host>
python tools/exhibition_smoke_check.py --service-api-base https://<service-host> --service-forge
```

The result must report `optional_enhancement_lanes.gcp_service = service-pass`
before the service lane can be shown, and `service-fail` must not override a
packaged-PC `local-pass/fail` decision.

PlayCanvas uses the same optional-lane rule: `playcanvas-pass` requires
`python tools/validate_playcanvas_snapshot.py <runtime-package.snapshot.json> --report-json`,
`playcanvas-fail` or `not-included` must be recorded otherwise, and no
PlayCanvas result can override `local-pass/fail` or become Web/Quest/Replay
truth.

### P0-02: Environment Variables

Purpose: use stable concept names across local, external-PC demo, future staging, and future production.

Candidate variables:

- `APP_ENV`
- `PUBLIC_API_BASE_URL`
- `PUBLIC_ASSET_BASE_URL`
- `PUBLIC_VIEWER_BASE_URL`
- `CORS_ALLOWED_ORIGINS`
- `STORE_DRIVER`
- `ARTIFACT_STORE_DRIVER`
- `QUEST_API_TARGET`
- `QUEST_VIEWER_PORT`
- `DASHBOARD_PORT`
- `REPLAY_ARTIFACT_ROOT`
- `SAKURA_LLM_MODEL=gpt-oss-120b`
- provider-specific secret names and model names

Rules:

- Never put secrets in `PUBLIC_*`.
- Keep `STORE_DRIVER=json` and `ARTIFACT_STORE_DRIVER=local` as the Phase 0 default.
- Leave `DATABASE_URL`, `ARTIFACT_BUCKET`, and GCP-specific resource names as later-stage variables unless an adapter needs them.
- Add `.env.demo.example` for the external PC path if the runbook needs a visitor-safe config.

Acceptance:

- Local dev and external-PC demo can be described with the same variable names.
- The config surface does not require a real GCP project to run Phase 0.
- `.env.demo.example` is part of the release package and contains only local
  exhibition fallback values plus blank provider secrets.
- Pre-release service config is checked before handoff:

```powershell
python tools/validate_service_deployment_contract.py --mode local --web-base-url http://127.0.0.1:8010 --api-base-url http://127.0.0.1:8010 --quest-base-url http://localhost:5173 --env-file .env.demo.example --report-json
python tools/validate_service_deployment_contract.py --mode external --web-base-url https://<web-host> --api-base-url https://<api-host> --quest-base-url https://<quest-host> --env-file .env.demo.example --report-json --check-http
```

External mode must fail localhost/private-LAN URLs, non-HTTPS URLs, missing required env keys, CORS mismatches, and real secret values in demo/release env files.

### P0-03: Forge Response Contract

Purpose: make Web Forge output recallable, durable, and portable.

Implementation:

- Include `suit_id`, `suit_version_id`, `recall_code`, `schema_version`, `catalog_version`, and `runtime_package_version`.
- Include `manifest_uri` or manifest body, `preview_uri`, and `asset_base_url`.
- Accept an idempotency key. Phase 0 can implement simple local JSON idempotency.
- Use a shared error envelope that Web and Quest can display without exposing internals.

Acceptance:

- The forge response alone gives the next Quest recall step enough identity to proceed.
- Physical file paths are not primary public identifiers.

### P0-04: Quest Recall Contract

Purpose: make Quest resolve the same suit version from the 4-digit code.

Implementation:

- Resolve recall code to active suit version.
- Return selected variants, toppings, texture pointers, manifest/runtime package pointer, render placements, cache policy, and gate status.
- Distinguish `unknown`, `expired`, `revoked`, and `malformed` codes.
- Prefer `no-store` or short cache for recall payloads.
- Preserve `runtime-render-placement.v1` fields verified by the code `3601` post-fix path.

Acceptance:

- Quest runtime can render from the response without reading local dev paths.
- Code error states are visible enough for Web/Quest/operator UI.
- Stale codes are not reused as external-PC evidence.

### P0-05: Recall Code Lifecycle

Purpose: keep the 4-digit code useful for operators without making it a durable identity or secret.

Implementation:

- Bind code to `suit_version_id`.
- Enforce active-code uniqueness in local JSON store.
- Store `created_at`, `expires_at`, `revoked_at`, and collision retry count.
- Keep code generation separate from suit identity generation.

Acceptance:

- One active code maps to exactly one active suit version.
- Expiry/revocation behavior can be migrated to Cloud SQL without changing Quest.

### P0-06: Local Store Boundary

Purpose: keep Phase 0 on JSON files while making Cloud SQL migration obvious.

Implementation:

- Define repository interfaces for `suit`, `suit_version`, `recall_code`, `generation_job`, `trial`, `transform_event`, and `replay_record`.
- Keep `STORE_DRIVER=json` as default.
- Define local file location, schema version, atomic write behavior, and broken JSON recovery policy.

Acceptance:

- API handlers do not know raw JSON file paths.
- A generated local store can be deleted/recreated through documented demo steps.

### P0-07: Artifact Store Boundary

Purpose: make `viewer/assets` and generated files replaceable by object storage later.

Implementation:

- Keep `ARTIFACT_STORE_DRIVER=local` as default.
- Define logical artifact URIs for GLBs, textures, previews, manifests, replay scripts, motion data, and media.
- Resolve GLB/texture/preview through `PUBLIC_ASSET_BASE_URL`.
- Store generated artifacts under suit version, trial, or replay identity.

Acceptance:

- Public responses return logical URIs or public/signed delivery URLs.
- Quest contracts do not include `viewer/assets/...` as a machine-local physical path.

### P0-08: Manifest Versioning

Purpose: detect contract drift across Web, Quest, providers, Replay, and future PlayCanvas.

Implementation:

- Add `schema_version` to SuitSpec, SuitManifest, runtime package, TransformSession/Event, and ReplayRecord where applicable.
- Include catalog version, asset base URL, selected variants, toppings, texture pointers, and render placement contract.
- Validate generated texture and manifest linkage.

Acceptance:

- Manifest/runtime package has enough information to reproduce Quest rendering.
- Schema mismatch is visible as warning or error, not silent fallback.

### P0-09: Armor Parts Catalog As Release Seed

Purpose: treat `viewer/assets/armor-parts` as versioned source assets, not an ad hoc write path.

Implementation:

- Define catalog version for canonical, variant, and topping GLBs.
- Include source hash for `variant_catalog.json` and referenced files.
- Validate module, variant key, topping path, sidecar, and physical file consistency.
- Add or document `/v1/catalog/parts` with catalog version and asset base URL.

Acceptance:

- API/Quest can confirm catalog version from payloads.
- Missing GLBs, sidecar mismatch, and unknown variants are caught before the external-PC package freezes.

### P0-10: Provider Adapter Boundary

Purpose: keep SakuraAI/Nanobanana as adapters, not hidden state owners.

Implementation:

- Put provider base URL, token, model names, and mock/real mode behind env/config.
- Normalize SakuraAI variant selection into valid catalog keys before runtime.
- Keep Nanobanana raw provider response private; public artifacts are stored separately.
- Record generation job status: `queued`, `running`, `succeeded`, `failed`, `partial`, or `skipped`.

Acceptance:

- Provider unavailable does not break the offline external-PC demo path.
- Real and mock provider outputs have the same public contract shape.

### P0-11: Web/Quest Smoke

Purpose: verify the full loop, not just individual endpoints.

Implementation:

- Web Forge smoke: generate -> preview -> recall code -> Quest URL/copy.
- Quest recall smoke: code input -> armor hidden before recall/transform -> recall -> transform/stand display command.
- Log GLB count, texture pointer, selected variants, render placement count, rotation count, fallback count, and scale factor.
- Compare Web preview asset refs against Quest recall payload.
- For external PC, run both same-LAN and USB/ADB paths where possible.

Acceptance:

- Armor is not permanently visible before recall/transform.
- Web preview and Quest recall selected variants/asset refs match.
- `adb unauthorized` is resolved before browser/API debugging begins.

### P0-12: Replay Portability Preflight

Purpose: make Replay a portable record instead of a local debug side effect.

Implementation:

- Write or validate `TransformSession`, append-only `TransformEvent`, `ReplayScript`, and optional `ReplayRecord`.
- Store `suit_id`, `suit_version_id`, `recall_code`, `trial_id`, manifest id, runtime package version, and artifact refs.
- Reject replay records with absolute local paths, missing runtime package snapshot, missing required artifacts, or invalid consent/retention state.
- Keep artifact refs bundle-relative, `gs://`, or approved `https://`.

Acceptance:

- Replay proof can move to another PC or later to GCS without depending on `C:\dev\codex\gavai-henshin`.
- Missing required artifacts fail closed.

## Data Boundary Summary

| Data | Phase 0 local owner | Future GCP owner | Must not leak |
|---|---|---|---|
| Suit metadata | JSON repository | Cloud SQL | Provider prompts, private operator notes unless explicitly public |
| Suit version/runtime package | JSON + manifest artifact | Cloud SQL metadata + GCS manifest | Local physical paths |
| 4-digit recall code | JSON code index | Cloud SQL `recall_code` | Durable IDs encoded into the code |
| GLB/texture/preview | Local artifact store | GCS | Raw authoring paths, unapproved private media |
| Trial/session | Local session JSON | Cloud SQL `trial` | Raw device IDs in visitor UI |
| Transform events | Append-only local event file | Cloud SQL rows or event archive | Stack traces, private identifiers |
| Replay scripts/records | Local replay bundle | Cloud SQL replay index + GCS artifacts | `C:\...`, `file://`, missing-artifact fallback |
| Live diagnostics | Memory/logs | Firestore only if needed | Canonical history |
| Secrets | `.env` | Secret Manager | `PUBLIC_*`, Web response, Quest response, Replay record |

## Recommended Sequence

1. P0-01, P0-02: lock contract inventory and env names.
2. P0-03, P0-04, P0-05: implement forge/recall/code lifecycle shape.
3. P0-06, P0-07: add store/artifact boundaries.
4. P0-08, P0-09: strengthen manifest/catalog validation.
5. P0-10: contain provider adapters and fallback modes.
6. P0-11, P0-12: prove Web/Quest smoke and Replay portability.
7. Only after `local-pass`, rehearse optional GCP/service, PlayCanvas, and
   mocopi lanes without changing Web/Quest/Replay semantics.

## Platform Decision Note

GCP is the natural later target for API, relational metadata, object artifacts, async jobs, secrets, IAM, and logs. PlayCanvas is a candidate web 3D preview/editor/QA runtime. Neither should be decided before the contract is stable.

Do first:

- Local contract freeze.
- External PC local fallback.
- Same-LAN and USB/ADB Quest paths.
- Replay portability.

Do later:

- Cloud Run/Cloud SQL/GCS adapter.
- Cloud Tasks queue for known async jobs.
- PlayCanvas adapter spike that consumes runtime package snapshots.
- Snapshot import gate:
  `python tools/validate_playcanvas_snapshot.py <runtime-package.snapshot.json> --report-json`.

Do not do yet:

- Microservices or GKE.
- Firestore as durable suit/replay history.
- PlayCanvas as variant, placement, code, or Replay authority.
- Cloud-only exhibition path before local fallback passes.

## External References Checked

- Google Cloud Run overview: https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run
- Google Cloud SQL documentation: https://cloud.google.com/sql/docs
- Google Cloud Storage objects: https://cloud.google.com/storage/docs/objects
- Cloud Run with Cloud Tasks: https://cloud.google.com/run/docs/triggering/using-tasks
- PlayCanvas Engine: https://playcanvas.com/products/engine
