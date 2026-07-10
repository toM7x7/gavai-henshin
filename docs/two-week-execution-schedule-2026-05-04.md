# Two-Week Execution Schedule - 2026-05-04

Range: 2026-05-04 to 2026-05-17 JST
North star: Web establishes the suit, Quest verifies the transformation, Replay records the experience.

## Source Context

Read inputs:

- `docs/thread-handoff-2026-05-03.md`
- `docs/web-ui-service-gcp-playcanvas-direction-2026-05-03.md`
- `docs/web-quest-runtime-placement-check-2026-05-03.md`
- `docs/p1-limb-variant-order-acceptance-2026-05-03.md`
- `docs/modeler-delivery-coordinate-review-2026-05-03.md`
- `docs/modeler-triview-30variant-audit-table-2026-05-03.md`
- `docs/modeler-exhibition-readiness-risks-2026-05-04.md`
- `docs/web-service-readiness-2026-05-02.md`
- `docs/web-service-phase0-task-breakdown-2026-05-02.md`
- `docs/new-route-gcp-readiness.md`

## Current Status Snapshot - 2026-05-04

Use these as the starting facts for this schedule:

- Web/Quest placement fix is in place and documented by the post-fix recall code `3601` path. The current evidence shows `runtime-render-placement.v1`, 18 render placements, selected variant identity, runtime rotation, and GLB renderability gates.
- Quest USB setup can still stop at `adb devices = unauthorized`. This is an ADB/headset trust issue. Resolve headset authorization before spending time on Quest Browser, Vite proxy, or API debugging.
- Web placement and Quest recall are no longer the same risk as external-PC readiness. The next proof must be a clean external Windows PC with packaged assets, ports `8010`/`5173`, same-LAN and/or USB/ADB connectivity, and replay evidence.
- GCP and PlayCanvas are planning lanes. Neither is allowed to become a prerequisite for the 2026-05-16 local external-PC rehearsal.

## Operating Decisions

1. Web/Quest recall is the spine. Do not let PlayCanvas, GCP, or modeler intake become a second source of truth.
2. Current 30 line variants are technical/file pass but remain `fidelity_hold`. They are not promoted to runtime acceptance until the visual gate passes.
3. P1 limb work is all 24 ordered filesets: left/right `upperarm`, `forearm`, `hand`, and `thigh` across `line_rescue_knight`, `line_royal_insect`, and `line_final_oath`.
4. Public Web Forge becomes a suit-establishment flow. Operator diagnostics stay available, but leave the default user path.
5. GCP serviceization starts from the current API contract: Cloud Run, Cloud SQL, Cloud Storage, Cloud Tasks, Secret Manager, and structured logs. No platform rewrite before contract freeze.
6. PlayCanvas is an adapter for preview/editor/QA only. Variant selection, placement resolution, acceptance policy, and Replay truth stay in the runtime package and API.
7. The final demo runs on an external exhibition PC, not this dev machine. "Works locally" is not a readiness gate; reproducible setup, packaged assets, Quest connectivity, smoke scripts, and rollback are mandatory.
8. Lane order is explicit: local external-PC fallback is the required exhibition baseline, web service/GCP is the later durable-service lane, and mocopi is an optional hardware-enhancement lane that needs separate risk gates.
9. Exhibition experience gates are required and separate from ideal lanes: Japanese UI, existing 3D model quality check and strengthening, per-part 3D fit/size/position micro-tuning, and tri-view-conscious cool-suit visual QA must pass before the demo is called venue-ready.

## Lanes And Owners

| Lane owner | Owns | Primary acceptance |
|---|---|---|
| Schedule-PM | Scope, milestone order, gate tracking, dependency pressure | One current plan, dated decisions, no hidden blockers |
| WebUI lane | Public Web Forge simplification | First screen has name, height, brief, compact style controls, generate, code, Quest link, visual preview |
| Web/API lane | Contract, store/artifact boundary, GCP service shape | `/v1` payloads avoid local paths/secrets and can map to DB/object storage |
| Quest lane | Headset verification and runtime placement parity | Physical Quest pass records hand/controller, elbow, hip, knee, boot, waist, and back behavior |
| Replay lane | TransformSession/Event/ReplayScript schema | Replay records reference suit id, recall code, runtime package version, and event log |
| Modeler lane | P0 fidelity hold closeout and P1 limb delivery | Sidecars, review images, strict delivery validation, and human visual review are all present |
| PlayCanvas lane | Adapter evaluation | Reads manifest/runtime package only; does not own suit truth |
| Local external-PC fallback lane | External Windows PC setup, packaging, smoke, recovery, operator runbook | A clean PC can run Web -> Quest -> Replay without this dev machine or cloud services |
| Japanese UI lane | Venue-facing Japanese copy, labels, status, operator text | Public Web/Quest/operator surfaces are readable in Japanese without debug-language noise |
| Existing 3D model quality lane | Current GLB/model read, defects, and strengthening priority | Existing demo models are checked before being packaged, and weak parts have strengthen/waive decisions |
| Per-part 3D fit lane | Size, position, rotation, and visible fit micro-tuning per armor part | Helmet/chest/back/waist/limbs/boots read as worn suit parts in Web and Quest |
| Tri-view visual QA lane | Cool-suit review against front/side/back/3q references | The suit reads cool, heroic, and line-specific before optional hardware/cloud lanes |
| Web service/GCP lane | Durable `/v1` service, DB/artifact mapping, deploy readiness | Cloud Run/GCP plan preserves the local API contract and does not block the local exhibition fallback |
| mocopi hardware-enhancement lane | mocopi hardware inventory, live input risk, fallback policy | mocopi improves VR body motion only after hardware, receiver, latency, and fallback gates pass |

## Milestones

| Date | Milestone | Acceptance gate |
|---|---|---|
| 2026-05-04 | Plan lock and gate baseline | This schedule is published; blockers are explicit; no implementation lane is asked to guess priority. |
| 2026-05-05 | Replay schema draft and headset runbook ready | Replay v0.1 fields are named; Quest physical checklist is executable from one recall code. |
| 2026-05-06 | Headset verification pass or defect list | Quest Browser verifies recall, transform, placement, and Replay diagnostics on device, or defects are logged by part/state. |
| 2026-05-07 | WebUI simplification and Japanese UI copy cut | Public flow removes default tables/diagnostics; venue-facing Web/Quest/operator copy has Japanese labels, OK/error states, and no raw debug text in the happy path. |
| 2026-05-08 | Web/API serviceization cut, existing model quality check, and per-part 3D fit baseline | `/v1` boundaries are assigned; current model quality and per-part size/position/rotation defects are listed for helmet, chest, back, waist, arms/hands, thighs, shins, and boots. |
| 2026-05-09 | Replay schema v0.1 and tri-view cool-suit QA setup | Replay fields are named; front/side/back/3q visual QA checklist and screenshot set are ready. |
| 2026-05-10 | Week 1 integration and experience review | Web code -> Quest recall -> Replay record is demonstrable; Japanese UI, existing 3D model quality, 3D fit baseline, and tri-view cool-suit QA have explicit pass/fix/hold notes. |
| 2026-05-11 | P1 limb intake and mocopi inventory gate | Order manifest is confirmed with modeler delivery expectations; mocopi hardware, receiver software, phone/device pairing, and operator availability are inventoried. |
| 2026-05-12 | P1 limb validation and clean-PC install gate | Open-order validation is clean; strict delivery is run if files land; runtime activation remains separate; external PC dependency/runtime install is rehearsed or blocked explicitly. |
| 2026-05-13 | Modeler fidelity, tri-view cool-suit, and mocopi risk gate | P0 30 variants receive pass/fix/hold decisions; cool-suit QA is signed off or defects are listed; mocopi receives `GO`, `DEMO-ONLY`, or `NO-GO`. |
| 2026-05-14 | GCP serviceization and offline/online assumptions gate | Cloud Run, Cloud SQL, GCS, Cloud Tasks, Secret Manager, IAM, and logging map to current local contracts; exhibition baseline remains local-first even if GCP is promising. |
| 2026-05-15 | Experience freeze, PlayCanvas adapter, and asset package gate | Japanese UI, existing 3D model strengthening decisions, per-part 3D fit tuning, and tri-view cool-suit QA are frozen for rehearsal; optional adapters remain non-blocking. |
| 2026-05-16 | External-PC integrated acceptance rehearsal | Local fallback and exhibition experience gates are rehearsed first; GCP and mocopi are exercised only as optional lanes after the local Web -> Quest -> Replay loop passes. |
| 2026-05-17 | Two-week exit review | Decide next two-week lane: promote accepted assets, serviceize `/v1`, or keep modeler/headset blockers as top priority. |

## P1 Limb Order

Delivery scope stays the existing 24-variant order manifest:

```text
docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json
```

Review order:

1. `forearm` + `hand`: first-person Quest clearance, controller visibility, wrist/knuckle scale.
2. `upperarm`: shoulder-to-forearm continuity, elbow escape, left/right mirror consistency.
3. `thigh`: waist-to-shin continuity, hip/knee clearance, full-body hero silhouette.

Line order inside each part family:

1. `line_rescue_knight`: establishes the practical baseline.
2. `line_royal_insect`: proves line differentiation without becoming creature-like.
3. `line_final_oath`: proves final-form density without blocking motion.

Runtime rule: P1 delivery does not modify runtime catalog until strict validation and human fidelity review pass.

## Acceptance Gates

### Headset Verification

Pass requires:

- Physical Quest Browser uses a Web-generated 4-digit recall code.
- Armor is not permanently visible before recall/transform.
- All visible GLBs load without fallback masking.
- `runtime-render-placement.v1` placement data is reflected on Quest.
- Hand/controller, elbow, hip, knee, back, waist, boot, and floor contact issues are recorded with screenshots or notes.
- Replay diagnostic state is visible enough for operator verification.

### WebUI Simplification

Pass requires:

- First screen stays focused on establishing one suit.
- Per-part tables, raw contracts, texture/modeler diagnostics, and warnings move behind operator/debug access.
- The public flow returns generated code and Quest launch/copy link without exposing local paths.

### Japanese UI Exhibition Gate

Pass requires:

- Public Web Forge happy path uses Japanese labels for input, generate, code, Quest launch/copy, and status.
- Quest visible status uses Japanese operator-readable text for recall, transform, OK, error, reset, and replay states.
- One-page operator checklist terms match the UI labels so a venue operator can cross-check without translating developer wording.
- Debug/raw contract text is hidden from the visitor path; if shown in operator mode, it is clearly marked as debug.
- Failure messages say the next action in Japanese, not only an internal exception or English trace.

### Existing 3D Model Quality Check And Strengthening

Pass requires:

- The exact existing 3D assets in the exhibition package are reviewed before the package is frozen; no unreviewed GLB is promoted by accident.
- Each demo-visible model receives `Pass`, `Strengthen`, `Waive`, or `Hold` for silhouette, material/readability, body attachment, and Quest visibility.
- Strengthening work is prioritized in this order: helmet/face, chest core, back silhouette, boots/floor contact, waist belt, shins, shoulders, arms/hands, thighs.
- A `Strengthen` item has a concrete target such as larger readable surface, clearer edge/bevel, stronger line identity, corrected material contrast, or reduced proxy/flat-panel feel.
- A `Waive` item is allowed only for show-day proof and must be listed in the package notes; it is not final asset acceptance.
- This gate is separate from mocopi and GCP. Better hardware motion or cloud service does not compensate for weak visible model quality.

### Per-Part 3D Fit/Size/Position Micro-Tuning

Pass requires:

- Each demo-visible part has an owner note for size, position, rotation, and body clearance: `helmet`, `chest`, `back`, `waist`, shoulders, upperarms, forearms, hands, thighs, shins, and boots.
- Web preview and Quest recall use the same `runtime-render-placement.v1` placement source; tuning does not create a second placement table.
- Minimum public-demo checks are recorded for head/neck view, chest/back float, waist clipping, hand/controller clearance, hip/knee clearance, shin/boot connection, and floor contact.
- Known bbox/fidelity waivers are explicitly listed; waived parts may be used for exhibition proof but not promoted as final accepted assets.
- If a part looks like a floating prop, flat proxy, or oversized blocker in Web or Quest, the experience gate is `Fix` or `Hold`, even if the file validator passes.

### Tri-View-Conscious Cool-Suit Visual QA

Pass requires:

- QA uses front, side, back, and 3q screenshots or renders for the exact demo suit package.
- Review answers three plain questions: "Does it look cool?", "Does it read as a worn hero suit?", and "Can visitors tell the selected line identity apart?"
- Helmet, chest, back, boots, shins, waist, shoulders, and visible P1 limbs receive `Pass`, `Fix`, or `Hold`.
- Tri-view QA is separate from modeler technical delivery. A GLB/manifest pass is not enough if the suit does not read well visually.
- The frozen exhibition package includes the screenshot set or notes used for the visual decision.

### Replay Schema

Pass requires:

- `TransformSession` stores suit id, suit version id, recall code, runtime package version, device/session metadata, state, and artifact pointers.
- `TransformEvent` is append-only and can capture trigger, transform phase, live pose sample summary, error, and completion.
- `ReplayScript` is derived from events plus runtime package, not manually authored as a second truth.
- Artifact paths align with `trials/{trial_id}/events.ndjson` and `trials/{trial_id}/replay/replay-script.json`.

### GCP Serviceization

Pass requires:

- Cloud SQL is canonical for suit, version, recall, trial, event, and audit rows.
- Cloud Storage is canonical for GLB, manifest copies, preview, texture, replay script, and media artifacts.
- Firestore is live state only, never durable history.
- Cloud Tasks owns async generation, validation, preview, and Replay media jobs after the sync contract is stable.
- Structured logs include suit id, recall code, manifest id, runtime package version, job id, and trial id where applicable.
- For exhibition planning, GCP is a later durable-service lane. It must not be required for the 2026-05-16 external-PC rehearsal unless the local fallback has already passed.

### mocopi Hardware Enhancement

Pass requires:

- Hardware set is identified: mocopi sensors, receiver phone/app or receiver PC path, charging, straps, USB/network, and spare batteries if applicable.
- Receiver path is rehearsed on or with the external PC by 2026-05-13.
- Input source can switch between `sim`/body fallback and `mocopi` without breaking the Quest trial or Replay record.
- Latency, dropouts, calibration drift, and sensor loss are recorded with a clear `GO`, `DEMO-ONLY`, or `NO-GO` decision.
- A mocopi failure does not block the local external-PC fallback. If mocopi is `NO-GO`, the operator uses the standard simulated/body replay path.
- Replay records must label whether motion input came from `mocopi`, `sim`, `body`, or fallback.

### PlayCanvas Adapter

Pass requires:

- PlayCanvas consumes manifest/runtime package snapshots.
- It may provide shareable 3D preview, non-Quest viewer, editor surface, or visual QA harness.
- It may not own variant selection, placement resolution, catalog acceptance, or Replay derivation.

### Modeler Fidelity Hold

Pass requires:

- P0 30 variants have `source_concept_ids`, `line_id`, `design_intent`, and `fidelity_notes` at sidecar level.
- Each line has front, side, back, 3q, source overlay front, helmet closeup, torso closeup, and boot side closeup evidence.
- Human review says line identity is readable in Web and Quest conditions.
- Until then, status stays `technical pass / fidelity_hold`.
- Any public-demo bbox/fidelity exception uses `docs/modeler-exhibition-readiness-risks-2026-05-04.md` waiver protocol and remains visibly separated from accepted assets.

### Exhibition PC Readiness

Pass requires:

- A fresh or clean external Windows exhibition PC can be prepared from a versioned bundle plus a short setup script/runbook.
- Required runtime dependencies are explicit: Git or zip extraction path, Python version, editable package install, Node/npm version, Quest Vite build/runtime, browser, ADB/Meta Quest Developer Hub option, and any provider credentials.
- Online/offline mode is declared. Online mode may call provider/API services; offline mode must use packaged assets, mock/fallback generation, local JSON store, and no secret-dependent path.
- Quest connectivity has two approved options: same LAN URL from the PC to Quest Browser, or USB/ADB reverse/tunnel if LAN is blocked. The chosen option is rehearsed before the event.
- Asset package includes `viewer/assets/armor-parts`, variant catalog, required GLBs/sidecars/previews, sample SuitSpec/manifest, Quest viewer build or source, and any replay seed artifacts needed for the demo.
- A single smoke-test script or command sequence verifies: API health, Web Forge page load, generate/recall code, Quest recall payload, visible GLB count, Replay artifact creation, and no missing public assets.
- Rollback/recovery is written: last-known-good bundle, clean restart steps, cache clearing, port conflict handling, network fallback, Quest browser refresh, and offline demo fallback.
- Operator checklist is executable by someone who did not develop the feature.

## Exhibition PC Plan

### Lane Priority

Use this order for exhibition readiness:

1. Required by 2026-05-16: local external-PC fallback. Web/API and Quest viewer run on the external PC, with packaged assets and offline-capable smoke.
2. Required by 2026-05-16: exhibition experience gates. Japanese UI, existing 3D model quality/strengthening, per-part 3D fit/size/position tuning, and tri-view-conscious cool-suit visual QA must pass or have explicit show-day waivers.
3. Later service lane: web service/GCP. Cloud Run/GCP can be prepared in parallel, but it is not the show-day dependency until the local fallback passes and a separate service smoke passes.
4. Optional enhancement lane: mocopi. Use only if the 2026-05-13 hardware risk gate is `GO` or `DEMO-ONLY` and the operator can return to fallback in under 5 minutes.

### Reproducible Setup

By 2026-05-10, freeze the first setup target:

- External PC OS: Windows 10/11, x64.
- Install runtimes: Python, Node/npm, Git or zip extraction, Chrome/Edge, ADB or Meta Quest Developer Hub if USB fallback is needed.
- Repository path: choose a simple local path such as `C:\henshin-demo` on the exhibition PC.
- Environment: provide `.env.demo.example` with non-secret public URLs, ports, mock/provider mode, Quest API target, and asset base URL.
- Startup: one operator command starts Web/API and one command starts Quest viewer if using Vite; if a static Quest build is used, record the exact served URL.

### Offline/Online Assumptions

Decision due 2026-05-14:

- Preferred: local-first online mode. The exhibition PC runs Web/API locally; Quest reaches the PC over LAN; provider calls are optional.
- Required fallback: offline mode. No external API is required for the demo loop; use packaged assets, deterministic sample input, local recall code, local Replay artifact, and mock provider outputs.
- Do not make the demo depend on this dev machine, uncommitted local paths, or a private LAN address from development.

### Quest Network And ADB Options

Prepare both by 2026-05-12:

- LAN option: PC and Quest on the same network; PC firewall allows the Web/API and Quest viewer ports; Quest Browser opens the PC LAN URL.
- USB/ADB option: PC has ADB/MQDH installed; operator can run reverse/tunnel setup if LAN blocks inbound access.
- Manual fallback: QR code or typed URL for Quest Browser, plus a typed 4-digit recall code if deep link copy fails.

### Asset Packaging

Package freeze on 2026-05-15:

- Include only accepted or intentionally held demo assets; label `fidelity_hold` assets clearly if used for proof, not final acceptance.
- Include hashes or a manifest for GLBs, sidecars, catalog, replay seeds, and sample inputs.
- Include the smoke-test script and expected output summary.
- Keep a last-known-good package separate from the active package.

### Smoke-Test Script

By 2026-05-12, define a script or command sequence named in the runbook. It must check:

1. Runtime versions and required commands are available.
2. Ports are free or assigned.
3. Web/API health responds.
4. Web Forge loads and creates a recall code from sample input.
5. Quest recall endpoint returns the same suit id, catalog version, runtime package version, selected variants, and render placements.
6. Asset URLs resolve for the expected GLB count.
7. Trial/Replay endpoint creates or reads a Replay artifact.
8. Logs and screenshots land in a dated folder on the exhibition PC.

### Rollback And Recovery

By 2026-05-15, document:

- Restart Web/API, Quest viewer, and browser in under 5 minutes.
- Clear browser cache/site data for the local demo origin.
- Switch from online/provider mode to offline/mock mode.
- Switch from LAN to USB/ADB option.
- Restore the last-known-good asset package.
- Preserve failure logs before overwriting or restarting.

### Operator Checklist

By 2026-05-16, the checklist must cover:

- Power, display, network, Quest battery, controllers, USB cable, and audio.
- Start services and confirm URLs.
- Run smoke test and confirm expected code path.
- Open Web Forge, generate code, open Quest URL, recall, transform, record Replay proof.
- If a step fails, follow rollback order before changing code.
- Record final pass/fail, recall code, screenshots, logs, and any headset notes.

### Day-Of Rehearsal Schedule - 2026-05-16

| Time | Action | Owner | Exit |
|---|---|---|---|
| 09:30 | External PC boot, power, display, Quest charge, controller battery check | Operator | Hardware ready |
| 10:00 | Install/update from frozen package only | Exhibition PC lane | No dev-machine dependency |
| 10:45 | Run smoke-test script and save output | Web/API lane | API/Web/Replay pass or defect recorded |
| 11:30 | Quest LAN run | Quest lane | Quest reaches PC URL and recalls suit |
| 12:15 | USB/ADB fallback run | Quest lane | Fallback works or is formally rejected |
| 12:45 | Japanese UI and operator wording pass | Japanese UI lane | Venue-facing labels/status are readable |
| 13:10 | Existing 3D model quality/strengthening check | Existing 3D model quality lane | Weak models are strengthened, waived, or held |
| 13:35 | Per-part fit/size/position spot check | Per-part 3D fit lane | No public-demo blocker remains unwaived |
| 14:00 | Tri-view-conscious cool-suit visual QA pass | Tri-view visual QA lane | Suit is Pass or explicit Fix/Hold list exists |
| 14:25 | Full Web -> Quest -> Replay rehearsal | Schedule-PM | One complete successful loop |
| 14:45 | Optional mocopi lane run only if gate is GO/DEMO-ONLY | mocopi lane | Motion improves VR or lane is disabled |
| 15:15 | Rollback rehearsal from last-known-good package | Local external-PC fallback lane | Recovery under 5 minutes or defect recorded |
| 15:45 | Optional GCP/service smoke only after local loop passes | Web service/GCP lane | Service lane status recorded, not required |
| 16:15 | Operator handoff using checklist only | Operator | Non-developer can run the local loop |
| 16:30 | Freeze day-of notes and open blockers | Schedule-PM | Go/no-go recommendation for 2026-05-17 review |

## Web Service / GCP / PlayCanvas Schedule Cut

This is the lane ordering for the final external-PC exhibition shape. The dates are gates, not encouragement to expand scope.

| Date | Lane | Work item | Exit condition |
|---|---|---|---|
| 2026-05-04 | Current state | Record Web placement post-fix as already fixed, and record Quest `unauthorized` as an ADB trust blocker. | Schedule no longer treats placement contract drift as the same risk as headset authorization. |
| 2026-05-05 | Local contract | Freeze `/v1` field inventory for forge, recall, trial/event, replay, artifact refs, and code lifecycle. | Public response inventory says what is public, operator-only, private, and future-cloud. |
| 2026-05-06 | Local smoke | Generate a fresh code on the dev machine and verify Web preview, Quest browser recall, and replay artifact path. | Evidence uses a fresh code; no stale `3601` reuse except as historical post-fix reference. |
| 2026-05-07 | External PC package | Draft package manifest, `.env.demo.example`, startup commands, asset list, and local JSON/artifact directories. | A clean PC operator can see what to install and what files must be present. |
| 2026-05-08 | External PC local baseline | Run Web/API `8010`, Quest `5173`, packaged assets, local store, and Web -> Quest -> Replay smoke on the external PC. | `local-pass` or a concrete defect list; cloud and mocopi remain disabled. |
| 2026-05-09 | LAN path | Rehearse Quest Browser access through PC LAN URL and firewall rules. | Same-LAN path is `pass`, `blocked`, or `not-used` with reason. |
| 2026-05-10 | USB/ADB path | Rehearse `adb devices`, resolve `unauthorized`, apply reverse for `5173` and `8010`, and open Quest `localhost:5173`. | USB path is `pass` or blocked by a named hardware/trust issue. |
| 2026-05-11 | Replay portability | Validate replay bundle refs, runtime package snapshot, and missing-artifact failure behavior. | Replay proof can move away from the dev machine. |
| 2026-05-12 | Offline fallback | Run deterministic/mock provider mode with packaged assets and local recall/replay. | Visitor loop does not require internet, provider secrets, or GCP. |
| 2026-05-13 | GCP mapping | Map local repositories/artifact refs to Cloud SQL, GCS, Cloud Tasks, Secret Manager, IAM, and logs. | Written mapping only; no cloud dependency added to show path. |
| 2026-05-14 | Minimal cloud slice | Define the smallest Cloud Run + Cloud SQL + GCS + Cloud Tasks + Secret Manager service smoke. | Cloud lane can be implemented after local proof without schema redesign. |
| 2026-05-15 | PlayCanvas adapter | Decide whether to run a manifest/runtime-package consumer spike. | `adapter-spike`, `defer`, or `reject`; no core rewrite. |
| 2026-05-16 | Integrated rehearsal | Run local external-PC loop first, then optional GCP/service smoke and PlayCanvas/mocopi only after local pass. | Show-floor status labels are recorded: `local-pass/fail`, `service-pass/fail/not-included`, `playcanvas-adapter/defer/not-included`. |
| 2026-05-17 | Exit review | Pick next two-week priority. | Promote serviceization only if local fallback and data boundaries are evidenced. |

### GCP Minimal Configuration

Use this as the smallest future service target:

- One Cloud Run service for current API/UI boundary and narrow HTTP worker endpoints.
- Cloud SQL for canonical metadata: `suit`, `suit_version`, `recall_code`, `trial`, `transform_event`, `replay_record`, `artifact`, `consent`, `retention`, `generation_job`, and audit rows.
- Cloud Storage for GLBs, manifests, runtime package snapshots, previews, textures, replay scripts, motion data, voice/audio, and exports.
- Cloud Tasks for async generation/validation/preview/replay jobs after idempotency keys exist.
- Secret Manager for provider keys and deployment secrets.
- Structured logs carrying `suit_id`, `recall_code`, `manifest_id`, `runtime_package_version`, `trial_id`, and `job_id`.

Avoid as premature before 2026-05-17:

- GKE, service mesh, many microservices, or separate frontend/backend products before `/v1` contracts freeze.
- Firestore as durable suit/replay history. Use it only for short-lived live state if a real-time display needs it.
- Pub/Sub/Eventarc fanout before a single idempotent queue exists.
- BigQuery, analytics exports, CDN/signed URL strategy, or multi-region design as exhibition blockers.
- PlayCanvas-hosted editor state as suit truth.

### Quest / Replay / 4-Digit Code Data Boundary

- The 4-digit code is a short-lived lookup handle to the active suit version. It is not the durable identity and not a secret-bearing token.
- Quest resolves the code and receives a runtime package snapshot. Quest does not select variants, resolve placement, or mutate acceptance state.
- Replay stores the human/operator-visible `recall_code`, but durable replay identity uses `suit_id`, `suit_version_id`, `trial_id`, `manifest_id`, and runtime package version.
- Replay artifact refs must be bundle-relative, `gs://`, or approved `https://`. `C:\...`, `file://`, and current-dev-machine paths are invalid for portable replay.
- Code states must be separated: `active`, `unknown`, `malformed`, `expired`, and `revoked`.
- Final rehearsal evidence must use a fresh code generated on the external PC path, not only historical code `3601`.

## Dependencies

| Dependency | Blocks | Mitigation |
|---|---|---|
| Physical Quest access | Headset verification, Quest gate promotion | Prepare desktop smoke and runbook on 2026-05-05 so headset time is not spent debugging setup. |
| External exhibition PC differs from dev machine | Final demo readiness | Build setup, asset package, smoke script, rollback, and operator checklist by 2026-05-16. |
| Exhibition network may block LAN access | Quest recall path | Prepare both same-LAN URL and USB/ADB fallback by 2026-05-12. |
| Offline/provider outage risk | Web generation and Replay proof | Package deterministic assets and mock/fallback generation; decide online/offline assumptions by 2026-05-14. |
| Japanese UI is incomplete | Venue operator and visitor comprehension | Freeze happy-path Japanese copy by 2026-05-07; allow debug English only behind operator/debug mode. |
| Existing 3D model quality is weak | Visitor-facing suit credibility | Check current packaged GLBs by 2026-05-08; strengthen, waive, or hold before 2026-05-15 freeze. |
| Per-part fit still looks wrong | Exhibition visual credibility | Record size/position/rotation defects by 2026-05-08 and tune or waive before 2026-05-15 package freeze. |
| Tri-view QA says suit is not cool enough | Visitor-facing impact | Run tri-view-conscious front/side/back/3q QA by 2026-05-13 and keep Fix/Hold separate from technical pass. |
| GCP service is not ready | Durable/public web service | Keep GCP as later lane; local external-PC fallback remains show baseline. |
| mocopi hardware pairing fails | Enhanced VR body motion | Decide GO/DEMO-ONLY/NO-GO by 2026-05-13; fallback to sim/body replay remains required. |
| mocopi latency/dropouts affect comfort | Quest experience quality | Run short rehearsal only; disable mocopi if calibration or dropout interrupts the visitor loop. |
| Modeler P0 fidelity hold | Runtime promotion of current 30 line variants | Keep assets visible as held candidates, not accepted catalog truth. |
| P1 limb missing filesets | Full hero suit continuity and controller/leg checks | Use the 24-variant order manifest and review order above. |
| Replay schema not fixed | GCP DB/artifact schema and PlayCanvas replay use | Freeze minimal v0.1 before cloud schema work expands. |
| WebUI still operator-heavy | Public suit-establishment proof | Move diagnostics to debug route/panel without deleting operator access. |
| Contract drift | GCP and PlayCanvas work | Keep current Python API and runtime package tests as the source until `/v1` contracts are stable. |

## Next 48 Hours

### 2026-05-04

- Schedule-PM: publish this schedule and mark all non-doc implementation as out of scope for this lane.
- Quest lane: turn `web-quest-runtime-placement-check-2026-05-03.md` into a headset checklist with the exact recall flow, screenshots required, and pass/fail fields.
- Replay lane: draft `TransformSession`, `TransformEvent`, and `ReplayScript` v0.1 fields from existing trial/replay routes.
- WebUI lane: define the public first-screen cut and the operator/debug escape hatch.
- Modeler lane: confirm P1 order manifest scope and resend strict acceptance rules to the delivery owner.
- Exhibition PC lane: inventory required runtimes, ports, assets, credentials, Quest connection options, and offline fallback needs for a clean external PC.
- Japanese UI lane: list all visitor/operator visible Web and Quest labels that must be Japanese by 2026-05-07.
- Existing 3D model quality lane: list current demo GLBs and mark obvious strengthen/waive/hold candidates.
- Per-part 3D fit lane: start the demo-visible part defect list with size, position, rotation, and clearance notes.
- Tri-view visual QA lane: define the exact screenshot/render set for front, side, back, and 3q cool-suit review.

### 2026-05-05

- Quest lane: run or schedule the physical headset pass; if blocked, produce a setup defect list before 2026-05-06.
- Web/API lane: inventory `/v1` public payload fields and flag local path, secret, or debug leakage.
- Replay lane: align replay artifact paths with local JSON now and GCS later.
- GCP lane: map local store/artifact concepts to Cloud Run, Cloud SQL, GCS, Firestore, Cloud Tasks, and Secret Manager.
- PlayCanvas lane: write the adapter non-ownership contract and required input fields.
- Exhibition PC lane: draft `.env.demo.example`, setup runbook, smoke-test command sequence, rollback order, and operator checklist skeleton.
- mocopi lane: list required mocopi hardware, receiver software, pairing steps, expected input source switch, and fallback owner.
- Japanese UI lane: draft Japanese OK/error/reset/replay wording and align it with the one-page operator checklist.
- Existing 3D model quality lane: pick the top model-strengthening targets that most affect first impression.
- Per-part 3D fit lane: identify the first 5 tuning blockers most visible in Web/Quest screenshots.
- Tri-view visual QA lane: prepare Pass/Fix/Hold review sheet for the exact demo suit.

## Exit Criteria For 2026-05-17

The two-week plan is successful if the team can say, with evidence:

1. Web establishes a suit through a simplified public flow and produces a recallable code.
2. Quest physical verification either passes or has a concrete part/state defect list.
3. Replay has a minimal schema that records the experience from trial events.
4. GCP serviceization has a contract-first path that does not split truth and is clearly later than the local fallback gate.
5. PlayCanvas is evaluated only as an adapter.
6. Modeler fidelity and P1 limb status are explicit, not hidden behind technical file pass.
7. External exhibition PC readiness is proven by setup, smoke, Quest connection, rollback, and operator checklist evidence from the external-PC path.
8. mocopi has a documented hardware risk decision and either improves the VR demo without blocking fallback, or is explicitly disabled.
9. Japanese UI, existing 3D model quality/strengthening, per-part 3D fit/size/position, and tri-view-conscious cool-suit visual QA have passed or have explicit show-day waivers.
