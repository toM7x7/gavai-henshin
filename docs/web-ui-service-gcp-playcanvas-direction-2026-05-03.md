# Web UI / Service / GCP / PlayCanvas Direction - 2026-05-03

Updated: 2026-05-04 JST

North star: Web establishes the suit, Quest verifies the transformation, Replay records the experience.

## Current Status Inputs

- Web/Quest runtime placement was fixed and verified in desktop browser evidence with recall code `3601`.
- `runtime-render-placement.v1` now carries placement count, selected variant identity, runtime rotation, and GLB renderability checks.
- Quest USB setup can currently stop at `adb devices = unauthorized`. Treat this as a PC/headset trust and operator setup gate, not an API or Quest viewer contract failure.
- The final exhibition proof must run on an external Windows PC. Local dev-machine success is evidence, but not final readiness.

## Product Cut

The public Web Forge should become a suit-establishment flow, not an operator console.

First-screen essentials:

- name
- height
- short concept brief
- compact style/mood controls
- generate button
- generated 4-digit recall code
- Quest launch/copy link
- visual preview

Move out of the main visitor flow:

- per-part tables
- manual variant selector details
- texture/modeler diagnostics
- raw runtime contract output
- asset pipeline internals
- build/acceptance warnings

Those details should remain available behind an operator/debug surface, not as the default user path.

## Deployment Ladder To Exhibition PC

Use this order. Each rung must preserve the same `/v1` payload shapes and runtime package semantics.

| Rung | Target | When | Purpose | Promotion gate |
|---|---|---:|---|---|
| 1 | Local dev loop | 2026-05-04 to 2026-05-06 | Fast contract and UI iteration on current machine. | Web generates a fresh 4-digit code; Quest viewer can recall it in browser smoke; replay artifact path is known. |
| 2 | External PC local loop | 2026-05-06 to 2026-05-08 | Prove the demo without cloud, provider secrets, or the dev machine. | Clean PC runs Web/API on `8010`, Quest viewer on `5173`, packaged assets, local JSON store, and smoke output. |
| 3 | Quest connection fallback | 2026-05-08 to 2026-05-12 | Make headset access robust under venue network conditions. | Same-LAN URL and USB/ADB reverse are both rehearsed or one is formally rejected with recovery steps. `unauthorized` must be resolved before browser debugging. |
| 4 | Offline/online rehearsal | 2026-05-12 to 2026-05-16 | Separate show baseline from optional service path. | Offline mode uses packaged assets/mock provider/local replay; online mode may call providers or GCP but is not required for visitors. |
| 5 | GCP web service lane | 2026-05-11 to 2026-05-17+ | Durable public/service archive after contract stability. | Cloud Run service maps to current API, Cloud SQL/GCS data boundaries are written, and local exhibition fallback remains independent. |
| 6 | PlayCanvas adapter lane | 2026-05-14 to 2026-05-17+ | Optional web preview/editor/visual QA surface. | Loads exported manifest/runtime package snapshots only; cannot own suit truth or placement policy. |

## Web Service Shape

Keep the contract-first Python implementation as the source of truth for now. The service boundary should mirror the existing local API before changing the stack.

Stable API concepts:

- `POST /v1/suits/forge`
- `GET /v1/quest/recall/{code}`
- `POST /v1/trials`
- `POST /v1/trials/{trial_id}/events`
- `GET /v1/trials/{trial_id}/replay`
- runtime package with `visual_layers`, `render_contract`, `render_placements`, selected variant identity, model/texture gate status, and runtime package version
- generated suit storage by suit id, suit version id, and recall code

Near-term target:

- Web Forge and Quest viewer both consume the same API contract.
- Replay records reference the same suit id, recall code, trial id, and runtime package version.
- Debug dashboards read the same stored records instead of becoming a separate truth.
- Public responses never expose local absolute paths, provider secrets, raw provider payloads, or debug-only state.

## Runtime Placement Public Response Contract

`runtime-render-placement.v1` is the adapter import contract for Web, Quest, future Cloud Run/GCP services, and a future PlayCanvas preview. Public responses must keep this shape portable:

- Authoritative selected placement lives in `runtime_package.render_placements`. The same selected records are mirrored into `asset_pipeline.render_placements` and `visual_layers.armor_overlay.render_placements` so Web and Quest can read without guessing.
- Each selected placement must include Web/VRM fields and Quest fields: `coordinate_space`, `quest_coordinate_space`, `offset_m`, `quest_rig_offset_m`, `surface_offset_clamped_m`, and `quest_surface_offset_clamped_m`.
- `surface_anchor.offset_clamped_m` must match `surface_offset_clamped_m`; `surface_anchor.quest_rig_offset_clamped_m` must match `quest_surface_offset_clamped_m`.
- Public payloads must not include machine-local refs such as `C:\...`, `/tmp/...`, `file://...`, or a `local_path` key. Use logical refs like `suits/...`, `trials/...`, `viewer/assets/...`, `gs://...`, or approved HTTPS URLs.
- `variant_render_placements` is an optional catalog/preview lane. It can expose candidate placements by variant, but it does not override `runtime_package.render_placements` until a variant is selected and promoted there.
- `texture_probe_job`, `generation_job`, GCP/service status, and PlayCanvas status are optional lanes. They can report jobs or previews, but cannot own variant selection, placement policy, recall-code truth, or Replay authority.

## Data Boundaries

| Domain | Canonical owner now | GCP owner later | Public response rule |
|---|---|---|---|
| Suit | Local JSON/repository interface | Cloud SQL table `suit` | Return `suit_id`, display summary, and current version pointer only. |
| Suit version | Local manifest/runtime package snapshot | Cloud SQL table `suit_version`; manifest copy in GCS | Return `suit_version_id`, `schema_version`, `catalog_version`, `runtime_package_version`, and artifact refs. |
| 4-digit recall code | Local code index | Cloud SQL table `recall_code` with active/expired/revoked state | Return the active code and lookup status. Never encode private IDs or secrets in the code. |
| Quest recall payload | Derived from active suit version | API read from Cloud SQL plus GCS manifest/runtime snapshot | Return enough to render Quest: selected variants, asset refs, render placements, texture refs, cache policy. |
| Replay trial/session | Local session JSON | Cloud SQL table `trial` | Return `trial_id`, state, device/session metadata class, not raw private device identifiers in public UI. |
| Transform events | Local append-only event file | Cloud SQL table `transform_event` or event rows plus GCS event archive | Append-only; include event type, phase, motion source, error summary, and artifact refs. |
| Replay record/script | Local replay JSON bundle | Cloud SQL replay index plus GCS JSON/media artifacts | Store portable refs: relative, `gs://`, or approved `https://`. No `C:\...` or `file://`. |
| GLB/texture/preview artifacts | `viewer/assets` and generated local files | Cloud Storage buckets | Public payload uses logical artifact refs or HTTPS delivery URLs, not physical file paths. |
| Live state | In-memory/local diagnostics | Firestore only if needed | Live display state is disposable; durable history stays in SQL/GCS. |
| Provider secrets | `.env` on local PC | Secret Manager | Never expose through `PUBLIC_*`, Web payloads, Quest payloads, or Replay records. |

Quest, Replay, and 4-digit code boundary:

- The 4-digit code is a short-lived lookup handle to one active suit version, not the durable identity.
- Quest reads by code and receives a runtime package snapshot. Quest does not mutate variant selection or placement policy.
- Replay records `recall_code` for operator traceability, but uses `suit_id`, `suit_version_id`, `trial_id`, manifest id, and runtime package version as durable anchors.
- Code lifecycle state must distinguish `unknown`, `malformed`, `expired`, `revoked`, and `active`.
- A reused or stale code is not acceptable exhibition evidence. Use a fresh Web-generated code for final external-PC rehearsal.

## GCP Direction

Recommended first cloud shape:

- Cloud Run for the API/UI service and any narrow HTTP worker endpoints.
- Cloud SQL for canonical relational metadata: suits, suit versions, recall codes, trials, transform events, replay indexes, consent, retention, generation jobs, audit rows.
- Cloud Storage for GLBs, manifests, runtime package snapshots, previews, screenshots, generated textures, replay scripts, motion data, voice/audio, and exports.
- Cloud Tasks for asynchronous generation, validation, preview build, modeler intake, and replay media jobs after synchronous behavior is stable.
- Secret Manager for provider keys, database credentials, signing secrets, and deployment-only secrets.
- Structured logs with suit id, recall code, manifest id, runtime package version, trial id, job id, and mocopi session ref where applicable.
- Firestore only for short-lived live state if the local experience needs it. Do not use it as canonical history.

Minimum GCP service slice:

1. One Cloud Run service hosting the current API/UI boundary.
2. One Cloud SQL database for metadata and code lookup.
3. One Cloud Storage bucket namespace split by artifact class and retention policy.
4. One Cloud Tasks queue only for slow generation/validation work that already has idempotency keys.
5. Secret Manager and least-privilege service accounts.
6. Structured logs and a small smoke endpoint that verifies DB, artifact resolver, and contract version.

Pre-release service contract gate:

```powershell
python tools/validate_service_deployment_contract.py --mode external --web-base-url https://<web-host> --api-base-url https://<api-host> --quest-base-url https://<quest-host> --env-file .env.demo.example --report-json --check-http
```

`external` mode requires HTTPS, rejects localhost/private-LAN URLs, checks Forge/Quest/API URL alignment, requires the public env keys, and fails real secret values in demo/release env files. `local` mode remains valid for `127.0.0.1:8010` and `localhost:5173`.

Phase0 service contract export:

```powershell
python tools/export_gcp_phase0_service_contract.py --env-file .env.demo.example --mode local --out qa/gcp-phase0-service-contract-latest.json --report-json
```

For a service rehearsal, pass the candidate HTTPS origins:

```powershell
python tools/export_gcp_phase0_service_contract.py --mode external --web-base-url https://<web-host> --api-base-url https://<api-host> --quest-base-url https://<quest-host> --env-file .env.demo.example --report-json
```

The exported JSON is the machine-readable phase0 handoff. It records required
env keys, public URL templates, `/v1` endpoint ownership, local-to-GCP storage
mapping, candidate Cloud Run services, and remaining `blocked_until` gates. It
does not call GCP APIs and does not replace the external PC `local-pass`
baseline.

Exhibition service gate:

```powershell
python tools/validate_exhibition_service_gate.py qa/gcp-phase0-service-contract-latest.json qa/service-deployment-contract-external.json --exhibition-smoke-report qa/exhibition_smoke_check_external_pc.json --report-json
```

Use `--strict` for public visitor readiness. The gate emits `GO`,
`DEMO-ONLY`, or `NO-GO`, plus `allowed_runtime_mode` and
`local_fallback_required`. External service use requires the phase0 contract,
the service deployment contract, HTTPS/public URLs, HTTP reachability evidence,
and local-pass smoke evidence. Missing reachability or smoke evidence is
demo-only by default and NO-GO under `--strict`; external service failure never
overrides the local fallback baseline.

Avoid for now:

- Splitting into many microservices before `/v1` contracts are frozen.
- Pub/Sub/Eventarc fanout before a single queue and idempotent job model exists.
- Kubernetes/GKE, Cloud Run multi-service mesh, or separate frontend/backend deployments unless traffic or team boundaries force it.
- Firestore as the durable suit/replay store.
- BigQuery analytics, Dataflow, CDN/cache invalidation strategy, or signed URL policy as blockers for the exhibition proof.
- PlayCanvas-hosted state, editor-only asset IDs, or browser local storage as canonical suit truth.
- A cloud-only show path before the external PC offline/local path passes.

## PlayCanvas Direction

PlayCanvas should not become the source of truth for the suit.

Useful later roles:

- shareable 3D preview surface
- lightweight editor/viewer for non-Quest users
- embedding target for public Web pages
- visual QA harness for accepted GLBs
- replay viewer for exported runtime package snapshots

Snapshot gate:

- PlayCanvas input is an exported runtime package snapshot JSON, not a live editing API response.
- Export a snapshot from a running local API by recall code:

```powershell
python tools/export_runtime_package_snapshot.py --api-base http://127.0.0.1:8010 --code 3601 --out qa/runtime-package-3601.snapshot.json --report-json
```

- Validate every snapshot before adapter import:

```powershell
python tools/validate_playcanvas_snapshot.py qa/runtime-package-3601.snapshot.json --report-json
```

- The validator must pass `render_placements`, selected variant identity, portable artifact refs, and no-local-path checks.
- The validator must fail any PlayCanvas write-back authority, mutation endpoint, source-of-truth role, or placement ownership field.
- A PlayCanvas pass only proves adapter import readiness. It does not promote variant selection, placement resolution, recall lookup, or Replay state.

Do not move these into PlayCanvas:

- variant selection
- placement resolution
- catalog acceptance policy
- 4-digit recall lookup
- Replay derivation
- mocopi provenance or consent/retention policy

Adoption decision:

- `No-go for core platform rewrite` before 2026-05-17.
- `Go for adapter spike` only if it consumes an exported manifest/runtime package snapshot and can be deleted without changing Web, Quest, or Replay semantics.

## Near-Term Sequence

1. Stabilize the runtime contract: size, offset, rotation, selected variant, asset gate, and replay anchors are verified.
2. Resolve Quest USB `unauthorized` as an operator/setup gate before judging browser or API behavior.
3. Simplify the public Web Forge UI while keeping operator diagnostics accessible.
4. Prove the external PC local baseline: Web/API `8010`, Quest `5173`, packaged assets, local JSON, smoke, rollback.
5. Define cloud storage records by copying the local API payload shape.
6. Add Replay record schema after Web/Quest recall is stable.
7. Evaluate PlayCanvas as an adapter only after the above contract is boring.

Decision: simplify the UI now, prepare Cloud Run/GCP around the current API contract, keep the external PC local path as the exhibition baseline, and keep PlayCanvas as a later renderer/editor adapter rather than a platform rewrite.

## External References Checked

- Google Cloud Run overview: https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run
- Google Cloud SQL documentation: https://cloud.google.com/sql/docs
- Google Cloud Storage objects: https://cloud.google.com/storage/docs/objects
- Cloud Run with Cloud Tasks: https://cloud.google.com/run/docs/triggering/using-tasks
- PlayCanvas Engine: https://playcanvas.com/products/engine
- PlayCanvas supported browsers: https://developer.playcanvas.com/user-manual/engine/supported-browsers/
