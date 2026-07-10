# Exhibition Service + mocopi Roadmap - 2026-05-04

Purpose: continue planning after the Quest mocopi spike by turning the
Web-service, GCP, PlayCanvas, and mocopi lanes into a compact implementation
schedule for the exhibition route.

Lore route:

```text
Web creates the suit.
Quest runs the transform trial.
Replay preserves the experience.
```

The spine is still Web -> Quest -> Replay. GCP, PlayCanvas, and mocopi are
adapters around that spine, not new sources of truth.

## 2026-05-05 Carry-In Update

The executable stage table for the current Windows / GPU-unknown / Quest USB /
shared-network / unused-mocopi-hardware situation is now
`docs/exhibition-mocopi-external-pc-stage-plan-2026-05-05.md`.

Interpretation:

- External-PC `local-pass` remains the only required visitor gate.
- BODY/static fallback is mandatory and must run without internet, cloud,
  provider secrets, or mocopi.
- Web serviceization is the anshin lane: run it to reduce deployment anxiety,
  but do not make it the exhibition dependency unless a separate service
  release is explicitly declared.
- mocopi starts as operator-only. It promotes from `DEMO-ONLY` to `GO` only
  after physical sensors, pairing, calibration, Quest diagnostic `MOCOPI`,
  latency/freeze thresholds, centerline QA, consent/retention, and 60-second
  BODY/static recovery all have evidence.

## Operating Decisions

1. The exhibition baseline is local-first on the external PC: Web/API on
   `8010`, Quest Vite on `5173`, USB `adb reverse` preferred, LAN/HTTPS only as
   fallback.
2. Web serviceization starts from the current `/v1` contract shape. Do not
   redesign payloads just because the future target is Cloud Run or Cloud SQL.
3. mocopi is an optional enhancement until physical sensors, receiver path,
   latency, calibration, Quest diagnostics, and BODY/static fallback all pass.
4. PlayCanvas is a preview/editor/QA adapter. Suit selection, placement,
   acceptance policy, replay identity, and mocopi provenance stay in the API and
   runtime package.
5. Replay is the long-term memory. It must reference `suit_id`, `recall_code`,
   runtime package version, transform events, artifacts, and mocopi provenance
   when mocopi contributes motion.
6. The Web/Quest placement post-fix path is already evidenced by recall code
   `3601`; do not re-open it as an architecture blocker unless new evidence
   contradicts `runtime-render-placement.v1` parity.
7. Quest `adb devices = unauthorized` is an operator trust/setup blocker. The
   owner fixes headset authorization before API, Vite, or browser debugging.

## Preflight Contract

Required local preflight:

- The required lane is `external_pc_local`.
- `local-pass` is prerequisite for visitor operation.
- `local-pass/fail` is decided only by the packaged exhibition PC running the
  local Web/API on `8010`, Quest viewer on `5173`, USB ADB reverse or verified
  LAN, local assets, forge/recall smoke, and replay portability checks.
- Core demo must run without live GCP, internet, provider secrets, or mocopi.
- `local-pass cannot be overridden` by a green GCP, PlayCanvas, or mocopi
  rehearsal. If local is `local-fail`, public operation stops or switches to
  the last-known-good/offline fallback.

Automated release-package evidence strings:

- local-pass is prerequisite for visitor operation
- service endpoint must pass the same forge, recall, replay, and no-local-path checks
- PlayCanvas must consume an exported runtime package snapshot
- mocopi cannot promote the visitor path unless the packaged-PC local baseline remains pass

Optional enhancement preflight:

- GCP/service exits as `service-pass/fail/not-included`. A service endpoint must
  pass the same forge, recall, replay, and no-local-path checks before it can be
  shown as a service rehearsal.
- PlayCanvas exits as `playcanvas-pass/fail/not-included`. PlayCanvas must
  consume an exported runtime package snapshot and must not become variant,
  placement, code, or Replay authority. Before `playcanvas-pass`, run
  `python tools/validate_playcanvas_snapshot.py <runtime-package.snapshot.json> --report-json`.
- mocopi exits as `mocopi-GO/DEMO-ONLY/NO-GO/not-included`. mocopi cannot
  promote the visitor path unless the packaged-PC local baseline remains pass
  and BODY/static fallback is rehearsed.
- mocopi labels must be backed by `tools/capture_quest_debug_snapshot.ps1`
  evidence packs from the physical Quest route, not only by PC-side logs or
  visual memory.

## Implementation Schedule

Promotion rule: do not promote GCP, PlayCanvas, or mocopi into the visitor path
until the external-PC local baseline is already labeled `local-pass`. Optional
lanes can rehearse in parallel, but they must exit as
`service-pass/fail/not-included`, `playcanvas-pass/fail/not-included`, and
`mocopi-GO/DEMO-ONLY/NO-GO/not-included` without changing the local show-floor
fallback.

| Phase | Dates | Focus | Acceptance gate |
|---|---:|---|---|
| 0. Quest spike handoff | 2026-05-04 | Preserve the Quest mocopi spike as diagnostic-only behavior. | Quest can distinguish `BODY`, `MOCOPI`, and `MOCOPI+LIVE` archive motion without changing the public visitor flow. |
| 1. Web service contract freeze | 2026-05-04 to 2026-05-06 | Lock forge, recall, runtime package, store, artifact, and replay identity fields. | `POST /v1/suits/forge` and `GET /v1/quest/recall/{code}` can be mapped to DB/object storage without local paths, secrets, or debug-only state in public responses. |
| 2. External PC local baseline | 2026-05-06 to 2026-05-08 | Make the packaged PC run Web -> Quest -> Replay without cloud or mocopi. | Clean PC generates a code, Quest recalls it through `5173`, transform trial runs, replay artifact is written or a frozen fallback replay is verified. |
| 3. mocopi receiver integration spike | 2026-05-08 to 2026-05-13 | Add the narrowest receiver/import path that can produce normalized motion and replay provenance. | Physical rehearsal shows Quest diagnostic `MOCOPI`, median visible latency `<= 120 ms`, p95 `<= 250 ms`, no left/right swap, and BODY/MOCOPI/recovery evidence packs exist. |
| 4. GCP service mapping | 2026-05-11 to 2026-05-14 | Map local stores to Cloud Run, Cloud SQL, GCS, Cloud Tasks, Secret Manager, IAM, and logs. | A written mapping exists for suit, version, recall, trial, event, replay, artifact, consent, and retention records; local exhibition baseline remains unblocked. |
| 5. PlayCanvas adapter proof | 2026-05-14 to 2026-05-15 | Evaluate PlayCanvas only as a runtime-package consumer for web preview or QA. | PlayCanvas loads a manifest/runtime package snapshot and renders accepted assets without owning variant selection or placement decisions. |
| 6. Integrated rehearsal and exit | 2026-05-16 to 2026-05-17 | Rehearse local baseline first, then optional GCP, PlayCanvas, and mocopi lanes. | Route is labeled `local-pass`, `service-pass/fail/not-included`, `playcanvas-pass/fail/not-included`, `mocopi-GO/DEMO-ONLY/NO-GO/not-included`, with replay portability checked. |

## Exhibition Deployment Ladder

| Rung | Mode | Required by | What runs | What can fail without blocking visitors |
|---|---|---:|---|---|
| 1 | Dev local proof | 2026-05-06 | Current dev machine, Web/API, Quest viewer, local assets, local JSON. | External PC packaging, GCP, PlayCanvas, mocopi. |
| 2 | External PC local proof | 2026-05-08 | Clean Windows PC, ports `8010`/`5173`, packaged assets, local JSON/artifacts, offline/mock fallback. | GCP, provider calls, mocopi, PlayCanvas. |
| 3 | LAN Quest route | 2026-05-09 | Quest Browser reaches `http://<PC_LAN_IP>:5173/...`; API through `8010`. | USB path can still be fallback. |
| 4 | USB/ADB Quest route | 2026-05-10 | `adb devices = device`, reverse `5173` and `8010`, Quest opens `http://localhost:5173/...`. | LAN path can be blocked by venue network. |
| 5 | Offline show loop | 2026-05-12 | Packaged assets, mock/provider-off mode, fresh local recall code, replay artifact. | Internet, provider services, GCP. |
| 6 | GCP service smoke | 2026-05-14+ | Cloud Run/API, Cloud SQL metadata, GCS artifacts, Cloud Tasks jobs, Secret Manager. | Visitor loop, unless separately promoted after local pass. |
| 7 | PlayCanvas adapter | 2026-05-15+ | Runtime package snapshot consumer for preview/editor/QA. | Web/Quest/Replay truth. |

## External-PC Local Baseline Preflight

This is the only required exhibition pass. Run it before any service or mocopi
rehearsal:

1. `python tools/validate_exhibition_release_package.py --report-json` returns
   no missing files, no pattern gaps, and either no critical untracked files or
   an explicitly saved local-snapshot report.
2. `python tools/smoke_web_glb_load.py --repo-root . --report-json` reports no
   GLB failures and `previewFallbackParts=0`.
3. Web/API listens on `8010`, Quest Vite listens on `5173`, and `npm run
   dev:quest:adb` forwards both ports when USB is used.
4. `python tools/exhibition_smoke_check.py --forge` creates a fresh code,
   recalls it, reports `runtime-render-placement.v1`, 18 render placements,
   zero selected-variant mismatches, zero runtime surface failures, and
   `unsafe_public_ref_count=0`.
5. Replay portability is checked: the record or frozen fallback replay uses
   bundle-relative, `gs://`, or approved `https://` artifact refs and does not
   depend on `C:\...`, `file://`, old browser cache, or a developer machine.
6. The operator writes the exit label: `local-pass` or `local-fail`. A local
   failure blocks visitor operation even if GCP, PlayCanvas, or mocopi demos are
   interesting on their own.

Optional lane preflight is deliberately later:

- GCP/service can be labeled `service-pass` only after the same forge, recall,
  artifact, replay, and no-local-path checks pass against the service endpoint.
  The current smoke entry point is:

  ```powershell
  python tools/exhibition_smoke_check.py --code 3601 --service-api-base https://<service-host>
  ```

  For service-owned fresh-code rehearsal, use `--service-forge` instead of
  assuming the local `3601` exists on the hosted service. A service failure is
  recorded as `service-fail`; it does not override the packaged-PC
  `local-pass/fail` result.
- PlayCanvas can be labeled adapter-ready only when it consumes an exported
  runtime package snapshot and cannot write canonical variant, placement,
  recall-code, or replay state. Required validator:
  `python tools/validate_playcanvas_snapshot.py <runtime-package.snapshot.json> --report-json`.
  Result labels are `playcanvas-pass`, `playcanvas-fail`, or `not-included`;
  none can override the packaged-PC `local-pass/fail` result.
- mocopi can be labeled `mocopi-GO` only after physical sensors, calibration,
  receiver, Quest diagnostics, latency thresholds, privacy/retention notes, and
  BODY/static fallback rehearsal all pass on the packaged PC.

### mocopi evidence pack gate

Run this only after `local-pass` is decided. The mocopi lane is optional; it
must never be allowed to change the default visitor route before BODY/static has
already passed on the same packaged PC.

Capture command for the Quest debug snapshot:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline
```

Use the screenshot variant for the final decision folder and any visual dispute:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline -Screencap
```

Evidence folders are written to `qa\logs\quest-3601-<timestamp>\` and must
contain `adb-devices.txt`, `adb-reverse.txt`, `quest-debug-latest.json`, and
`operator-summary.txt`; `screencap.png` is required for final visual sign-off or
failure triage. Review `adb-devices.txt` for `device`, `adb-reverse.txt` for
`tcp:5173` and `tcp:8010`, and `operator-summary.txt` for `telemetryCode`,
`xrSession`, `uxState`, `centerlineVerdict`, `centerlineClassification`, and
`centerlineDisplayLine`.

Required packs:

1. BODY fallback baseline: mocopi off or ignored, current Web -> Quest -> Replay
   path works and can be shown publicly.
2. MOCOPI candidate: imported mocopi or physical sensors produce a visible
   `MOCOPI <n>f` or `MOCOPI+LIVE` Quest token with usable frames.
3. Fallback recovery: mocopi is disabled or bypassed, then the route returns to
   BODY/static within 60 seconds without changing the public visitor URL.

Decision material:

- `mocopi-GO`: `local-pass` plus all three packs; physical sensors/receiver or
  accepted import path is documented; Quest shows usable mocopi frames; latency,
  freeze, left/right, privacy, consent, retention, and centerline QA are within
  gate; recovery to BODY/static is proven.
- `mocopi-DEMO-ONLY`: local baseline and BODY fallback are safe, but mocopi is
  replay/import-only, operator-assisted, latency-warn, centerline-warn, or lacks
  enough physical rehearsal to enter the default visitor flow.
- `mocopi-NO-GO`: local baseline is missing, the MOCOPI token is absent or
  `0f`, ADB reverse/Quest telemetry cannot be captured, Quest is
  `unauthorized`, fallback exceeds 60 seconds, left/right swaps, freezes exceed
  gate, consent/retention is missing, or mocopi testing destabilizes the
  BODY/static baseline.

Order that keeps the baseline intact:

1. Label `local-pass/fail` from the external-PC local baseline.
2. If `local-pass`, capture the BODY fallback baseline pack.
3. Rehearse mocopi in an operator lane only.
4. Capture the MOCOPI candidate pack.
5. Disable or bypass mocopi and capture the fallback recovery pack.
6. Write `mocopi-GO/DEMO-ONLY/NO-GO/not-included`.
7. Promote nothing into the public route unless the result is `mocopi-GO`.

Acceptance order:

1. Decide `local-pass/fail`.
2. Only if local is `local-pass`, record optional lane results:
   `service-pass/fail/not-included`, `playcanvas-pass/fail/not-included`, and
   `mocopi-GO/DEMO-ONLY/NO-GO/not-included`.
3. If local is `local-fail`, optional results may be kept as engineering notes
   but cannot open the public visitor route.

## Acceptance Gates

### mocopi Phase Gates

Phase 0 is the only committed exhibition baseline today. It is a safety and
truthfulness gate: Quest may label replay motion as `MOCOPI` only when usable
motion frames exist, and a missing mocopi/body-sim artifact must fall back to
replay/static instead of breaking the viewer.

Phase 1 is the shortest path toward a real mocopi rehearsal. Use imported mocopi
JSON/export first, run it through the existing `--mocopi` and body-sim path, and
prove the Quest diagnostic, replay provenance, and BODY/static fallback on the
external PC. Exit evidence requires the BODY fallback baseline pack, the MOCOPI
candidate pack, and the fallback recovery pack from
`capture_quest_debug_snapshot.ps1`.

Phase 2 is live receiver candidate work. Do not start it until Phase 1 passes on
real hardware. The receiver can be a file drop, app/export bridge, or WebSocket
adapter, but the acceptance gate is the same: stable pairing, correct
calibration, `<= 120 ms` median visible latency, `<= 250 ms` p95, no left/right
swap, saved Quest telemetry/screenshot evidence, and a rehearsed fallback under
60 seconds.

### Gate A: Web Creates Suit

Pass requires:

- Public Web Forge produces `suit_id`, `suit_version_id`, `recall_code`,
  manifest/runtime package version, preview pointer, and artifact pointers.
- Generated suit records avoid absolute local paths and machine-specific URLs.
- Web preview and Quest recall resolve the same selected variants, asset refs,
  render placements, and catalog version.
- Operator/debug details can exist, but the visitor path stays focused on
  name, height, concept brief, compact style controls, generate, code, Quest
  link, and preview.

### Gate B: Quest Runs Transform Trial

Pass requires:

- Physical Quest Browser recalls a Web-generated code from the external PC.
- Armor appears through the same runtime package contract used by Web preview.
- Transform trial records trigger, phase, motion source, errors, and completion
  as append-only events.
- mocopi mode is never claimed publicly unless Quest diagnostics show `MOCOPI`.
- If mocopi fails, BODY or static fallback is operator-confirmed before visitors
  continue.

### Gate C: Replay Preserves Experience

Pass requires:

- Replay record references `suit_id`, `recall_code`, manifest/runtime package,
  transform session, source events, playback view, and artifacts.
- Artifact refs are bundle-relative, `gs://`, or approved `https://` refs, not
  `C:\...`, `file://`, or dev-machine absolute paths.
- mocopi provenance is stored when used: provider, source session, frame rate,
  frame count, coordinate space, source artifact, derived artifact, consent, and
  retention class.
- The replay bundle can move to another PC or cloud resolver and still validate
  required artifacts before playback.

### Gate D: Service/GCP Does Not Fork Truth

Pass requires:

- Cloud SQL owns searchable metadata: suits, versions, recall codes, trials,
  events, replay indexes, consent, and retention.
- GCS owns large artifacts: GLBs, manifests, previews, textures, replay scripts,
  body/mocopi motion, voice/audio, and exports.
- Cloud Tasks owns async generation, validation, preview, and replay media jobs
  only after synchronous contract behavior is stable.
- Structured logs include suit id, recall code, manifest id, runtime package
  version, trial id, job id, and mocopi session ref when present.

Minimum GCP configuration:

- One Cloud Run service keeps the current API/UI boundary and exposes the `/v1`
  contract without changing payload semantics.
- One Cloud SQL database owns relational metadata and code lookup.
- One Cloud Storage bucket namespace owns large and portable artifacts.
- One Cloud Tasks queue owns slow generation/validation/preview/replay jobs only
  after idempotency keys and retry behavior are explicit.
- Secret Manager owns provider keys and deployment secrets.
- IAM service accounts are separated for runtime, task execution, and artifact
  read/write.

Avoid as too early:

- GKE, service mesh, or many microservices.
- Firestore as durable suit, recall, trial, or replay history.
- Pub/Sub/Eventarc fanout before a single queue proves the job model.
- BigQuery/analytics/CDN/signed URL strategy as show-floor blockers.
- Cloud-only demo assumptions before the external-PC local loop passes.

### Gate D2: Data Boundaries Stay Explicit

Pass requires:

- The 4-digit recall code is only a short-lived lookup handle for the active
  suit version. It is not a durable identity and not a secret.
- Quest receives a runtime package snapshot from recall and never owns variant
  selection, placement resolution, catalog acceptance, code lifecycle, or replay
  derivation.
- Replay records the visible `recall_code` for traceability, but durable replay
  linkage uses `suit_id`, `suit_version_id`, `trial_id`, `manifest_id`, runtime
  package version, and artifact refs.
- Artifact refs are portable: bundle-relative, `gs://`, or approved `https://`.
  `C:\...`, `file://`, and dev-machine absolute paths invalidate cloud or
  external-PC portability.
- Raw voice/audio and raw mocopi motion have consent and retention state before
  being copied into service or cloud storage.

### Gate E: PlayCanvas Remains Adapter

Pass requires:

- PlayCanvas reads a manifest/runtime package snapshot or exported artifact
  bundle.
- `python tools/validate_playcanvas_snapshot.py <runtime-package.snapshot.json> --report-json`
  passes before labeling the lane `playcanvas-pass`.
- It does not mutate canonical suit records, recall bindings, placement policy,
  or replay history.
- Any PlayCanvas-specific state is either disposable UI state or written back as
  a reviewed artifact through the service contract.

## External PC And Exhibition Constraints

- Core demo must run without live GCP, internet, provider secrets, or mocopi.
- External PC package must include the repo/runtime files, accepted assets,
  schemas, config examples, smoke tools, runbooks, and any frozen fallback
  suit/replay seeds.
- Do not depend on `C:\dev\codex\gavai-henshin`, old Quest tabs, browser cache,
  private LAN IPs, developer `.env`, global npm/Python quirks, or files outside
  the release package.
- Quest port `5173` and Web/API port `8010` are the documented exhibition
  baseline. If a port changes, update adb reverse, headset URL, runbook, and
  smoke scripts together.
- Raw mocopi motion and voice/audio are identifying data. Retain raw captures
  only under explicit consent and retention policy; prefer derived replay motion
  for public bundles.
- Show-floor decisions must be labeled plainly: `local-pass/fail`,
  `service-pass/fail/not-included`, `playcanvas-pass/fail/not-included`,
  `mocopi-GO/DEMO-ONLY/NO-GO/not-included`.

## Immediate Next Engineering Tasks

1. Treat Web placement post-fix as current baseline and keep `3601` only as
   historical evidence; generate fresh codes for new external-PC proof.
2. Resolve Quest USB `unauthorized` before browser/API debugging: headset prompt,
   `adb devices = device`, reverse `5173` and `8010`, then Quest Browser.
3. Define the `/v1` public field inventory for forge, recall, transform events,
   replay records, artifact refs, and mocopi provenance.
4. Add a local store/artifact abstraction plan that can swap JSON/files for
   Cloud SQL/GCS without changing Web or Quest payloads.
5. Build a replay portability preflight spec: schema validation, artifact
   resolution, runtime package snapshot check, consent/retention check, and
   missing-artifact failure behavior.
6. Decide the mocopi receiver path for the first physical rehearsal: live
   receiver, imported JSON, or phone/export bridge. Record what is in scope and
   what remains BODY fallback.
7. Write the external-PC smoke order for the service lane: install, start
   `8010`, start `5173`, generate suit, recall on Quest, run transform, verify
   replay artifact, then run mocopi only if the baseline passes.
8. Draft the GCP table/object mapping for `suit`, `suit_version`, `recall_code`,
   `trial`, `transform_event`, `replay_record`, `artifact`, `mocopi_session`,
   `consent`, and `generation_job`.
9. Create a PlayCanvas adapter checklist that proves it consumes exported
   runtime packages and cannot become a second placement or variant-selection
   authority.

## Dependencies To Keep Visible

- Physical Quest rehearsal remains the strongest truth test for placement,
  trigger, mic/WebXR policy, and replay diagnostics.
- mocopi cannot be promoted from `DEMO-ONLY` to `GO` without real sensors,
  straps, calibration, receiver, PC, Quest, and fallback rehearsal together.
- GCP readiness is valuable, but it must not block the local exhibition
  fallback unless a separate service release is explicitly declared.
- PlayCanvas can improve shareability and QA, but only after Web/Quest/Replay
  contract drift is boring.
