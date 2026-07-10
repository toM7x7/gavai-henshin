# Replay Record Contract

Status: draft for next implementation
Schema: `schemas/replay-record.v0.2.schema.json`
Sample: `examples/replay-record.sample.json`

## Purpose

`ReplayScript v0.1` is still the active demo playback script returned by
`GET /v1/trials/{trialId}/replay`. `ReplayRecord v0.2` is the next archival
envelope around that script. It preserves enough context to replay or audit the
experience without requiring a live Quest session, a mutable SuitSpec, or local
debug state.

The invariant is:

```text
Web suit issue -> Quest recall -> Transform trial events -> Replay record
```

The record must carry the public and internal identity (`recall_code`,
`suit_id`), the runtime package contract version used by the viewer, the
transform trial event trail, the selected replay view mode, voice/audio
metadata, and refs to generated artifacts.

## Required Anchors

- `suit_id`: durable internal suit identity.
- `recall_code`: four-character Quest lookup code shown to visitors/operators.
- `manifest_id`: runtime manifest used for the trial.
- `runtime_package.contract_version`: version imported by Quest/Web runtime.
- `runtime_package.render_placement_contract`: placement contract used for GLB
  scale/offset/rotation.
- `runtime_package.variant_render_placement_contract`: selected variant table
  contract used to keep manual Web Forge variant preview, Quest recall, and
  Replay alignment on the same placement record.
- `runtime_package.variant_placement_snapshot`: per-part relation between the
  selected variant key, `render_placements`, and the overlay
  `variant_render_placements` table.
- `transform_trial.session_id`: TransformSession/Trial ID.
- `source_events[]`: ordered TransformEvent summaries that produced playback.
- `playback.view_mode`: `self`, `mirror`, or `observer`.
- `playback.motion_source`: live/body/static diagnostic source used by replay.
- `audio.voice_capture`, `audio.trigger`, `audio.tts`: capture, recognition, and
  response metadata.
- `presentation`: Japanese UI labels for stored event and view mode codes.
- `motion_provenance`: mocopi/session/fps/frame-count provenance for replay
  motion.
- `operation`: whether the record was written by local demo code, a web service,
  or cloud service, plus the storage/runtime resolver rules.
- `portability`: bundle-relative/cloud URI policy and move validation.
- `media_retention`: retention class, export formats, and raw media policy.
- `privacy`: operator/participant consent assumptions and PII classes.
- `validity`: how to decide whether the record remains playable after moving to
  another PC or cloud.
- `artifacts`: refs to replay script, transform session, runtime package, and
  optional audio/body/video outputs.

## Compatibility

This contract intentionally does not replace `ReplayScript v0.1` yet. The next
implementation can build a `ReplayRecord v0.2` after the existing replay script
is generated:

1. Read `transform-session.json`.
2. Read or generate `replay-script.json`.
3. Attach `suit_id`, `recall_code`, `manifest_id`, and runtime package version
   from Quest recall.
4. Copy compact TransformEvent refs into `source_events`.
5. Copy timeline segments from `ReplayScript v0.1`.
6. Add playback mode and motion diagnostic from the Quest viewer event payload.
7. Attach voice capture, trigger, and TTS metadata from `/api/iw-henshin/voice`
   or the trial event payload.
8. Attach Japanese UI labels in `presentation.event_labels` for the stored
   source event types.
9. Attach mocopi or other motion provenance when motion frames are used.
10. Copy the runtime package `selected_variant_keys`,
    `visual_layers.armor_overlay.variant_render_placements`,
    `selected_variant_render_placements`, and `variant_placement_snapshot`.
11. Write `replay-record.json` beside `replay-script.json`.

No current demo endpoint needs to change until a dedicated
`GET /v1/trials/{trialId}/replay-record` or `GET /v1/replays/{replayId}` is
added.

## Variant Placement Snapshot

Manual Web Forge variant switching can change the displayed GLB and placement
without immediately minting a new Quest recall code. A replay record must not
rediscover which offset/scale/rotation belonged to the shown variant from the
current catalog or viewer cache. It should persist the runtime package snapshot
fields:

- `runtime_package.selected_variant_keys`: `{ part: selected_variant_key }`
  derived from `render_placements[part].selected_variant_key`.
- `runtime_package.render_placements`: the active Quest/Web placement map for
  the recalled suit.
- `runtime_package.visual_layers.armor_overlay.variant_render_placements`:
  `{ part: { variant_key: placement } }` table copied from the Forge runtime
  package snapshot when available.
- `runtime_package.selected_variant_render_placements`: `{ part: placement }`
  containing only table records that match the selected variant.
- `runtime_package.variant_placement_snapshot`: compact audit relation for
  replay diff checks.

Each `variant_placement_snapshot.parts[part]` record should include:

- `selected_variant_key`.
- `render_placement_path`, normally `render_placements.<part>`.
- `variant_render_placement_path`, normally
  `visual_layers.armor_overlay.variant_render_placements.<part>.<selected_variant_key>`
  for public runtime packages, or `variant_render_placements.<part>.<selected_variant_key>`
  for private asset-pipeline snapshots.
- `render_asset_ref` and `variant_asset_ref`.
- `matches_current_render_placement`.
- `status`, one of `matched`, `not_variant_selected`,
  `missing_variant_render_placement`, `selected_variant_key_mismatch`, or
  `asset_ref_mismatch`.

Replay alignment QA should treat `status = matched` as the only fully aligned
case for a selected manual variant. If a selected part reports
`missing_variant_render_placement` or a mismatch status, the replay may still be
playable from `render_placements`, but the record must mark it as a Web-vs-Quest
placement audit warning because the Web manual preview cannot be proven to have
used the same variant table entry as Quest recall.

For GLB placement comparisons, use the `runtime-render-placement.v1` fields
directly:

- `target_size_array_m`
- `offset_m`
- `surface_offset_clamped_m`
- `quest_rig_offset_m`
- `quest_surface_offset_clamped_m`
- `rotation_deg`
- `asset_ref`
- `selected_variant_key`

The replay diff should compare Web preview capture telemetry, Quest recall
runtime package, and the snapshot path above. It should not compare against the
mutable current `viewer/assets/armor-parts/variant_catalog.json` as the source
of truth after the record has been written.

### Dedicated Validation Tool

Use `tools/validate_replay_variant_alignment.py` to turn the snapshot relation
into a deterministic JSON report:

```bash
python tools/validate_replay_variant_alignment.py replay-record.json --report-json
python tools/validate_replay_variant_alignment.py runtime-package.json --report-json
```

The tool accepts either:

- a ReplayRecord-like object containing `runtime_package`, or
- a runtime package snapshot directly.

The report contract is `replay-variant-alignment-report.v1`. It returns:

- `ok` / `status`.
- `source_type`: `replay_record`, `container`, or `runtime_package`.
- `selected_variant_count`, `matched_part_count`, `mismatch_part_count`.
- `matched_parts`, `mismatch_parts`, and `not_variant_selected_parts`.
- `parts[part].selected_variant_key`.
- `parts[part].render_asset_ref`.
- `parts[part].variant_asset_ref`.
- `parts[part].snapshot_status`.
- `parts[part].web_quest_replay_identity`.
- `parts[part].checks.selected_key_consistent`.
- `parts[part].checks.asset_ref_consistent`.
- `reasons[]` and `warnings[]`.

A selected variant part passes only when:

- the selected key is consistent across `selected_variant_keys`,
  `render_placements`, `selected_variant_render_placements`, and
  `variant_placement_snapshot`;
- `render_placements[part].asset_ref` matches the selected variant table
  `asset_ref`;
- `variant_placement_snapshot.parts[part].status = matched`;
- `matches_current_render_placement = true`.

This is the offline guard that lets exhibition QA compare Web preview,
Quest recall, and Replay archive identity without opening the viewer.

### Minimal Demo Export CLI

Use `tools/export_replay_demo_record.py` when exhibition QA needs a concrete
ReplayRecord from an already-exported runtime package snapshot:

```bash
python tools/export_replay_demo_record.py runtime-package.json --out replay-record.json --code P7C1 --height-cm 170 --experience-label "Day 1 QA" --report-json
```

The exporter writes a minimal `replay-record.v0.2` object containing:

- `runtime_package`.
- `selected_variants`.
- `placement_snapshot`.
- `wearer.height_cm` and `wearer.source`.
- `experience.label` and source metadata.
- `metadata.created_at`.

Immediately after writing, it runs
`tools/validate_replay_variant_alignment.py` against the generated record and
returns `replay-demo-record-export.v1` with `variant_alignment_report`. A
non-passing alignment report should fail exhibition QA because the saved replay
cannot prove Web preview, Quest recall, and Replay archive identity for the
selected variant placement.

### Web Replay QA Artifact CLI

Use `tools/prepare_replay_qa_artifact.py` after a ReplayRecord exists and the
operator needs a stable file path for Web replay screenshots or manual notes:

```bash
python tools/prepare_replay_qa_artifact.py replay-record.json --code P7C1 --qa-dir qa/replay --out-summary qa/replay/P7C1.summary.json --report-json
```

The tool normalizes/copies the ReplayRecord to a stable QA artifact path, runs
`validate_replay_variant_alignment.py` against the copied file, and writes a
summary JSON. The summary contract is `replay-qa-artifact-summary.v1` and must
include:

- `artifact_path`.
- `alignment_status`.
- `web_replay_check_url_hint`.
- `recommended_operator_check`.

Browser startup is intentionally outside this tool. Exhibition QA should treat
`alignment_status = pass` as the precondition for accepting Web replay visual
screenshots as evidence.

The `web_replay_check_url_hint` must target the static Quest viewer route:
`viewer/quest-iw-demo/index.html`. Its query contract follows the viewer's
current `quest-demo.js` readers:

- `replay`: ReplayRecord or replay script JSON path consumed by `getReplayPath`.
- `code`: four-character Quest recall code consumed by `getRecallCode`.
- `qa`: QA artifact code used for debug/telemetry labeling.

Do not use legacy `replayRecord` or `qaCode` in generated hints unless the
viewer adds explicit readers for those query names.

`tools/validate_replay_public_artifact.py` checks this URL contract when its
input is a `replay-qa-artifact-summary.v1` object. Legacy `replayRecord` or
`qaCode` query names are warnings in `--mode local` so old QA evidence can be
identified without blocking local inspection. They are failures in
`--mode external`; rewrite the summary with
`tools/prepare_replay_qa_artifact.py` before public publication.

The URL preflight also checks that `replay` equals the summary `artifact_path`,
`qa` equals `artifact_code`, and `code` equals the ReplayRecord `recall_code`
when a four-character recall code is present. A summary whose URL points to a
stale artifact or stale recall code should fail before browser review.

### Public Replay Artifact Preflight CLI

Use `tools/validate_replay_public_artifact.py` before a ReplayRecord or QA
summary is promoted to a Web-service-facing public artifact:

```bash
python tools/validate_replay_public_artifact.py replay-record.json --mode external --report-json
python tools/validate_replay_public_artifact.py qa/replay/P7C1.summary.json --mode external --report-json
```

The report contract is `replay-public-artifact-preflight.v1`. It fails closed
when the artifact leaks local filesystem paths, uses `localhost` / `127.0.0.1`
URLs in `external` mode, omits `runtime_package`,
`runtime_package.variant_placement_snapshot`, selected variants, or the
`replay-record.v0.2` schema markers. It also verifies
`public_artifact_policy` so a public ReplayRecord cannot silently allow local
paths or skip external preflight.

Public ReplayRecords must also explicitly state that PlayCanvas write-back is
forbidden, for example
`public_artifact_policy.playcanvas_writeback_allowed = false`. A public replay
artifact is a snapshot consumer; it must not mutate the PlayCanvas source scene
or depend on PlayCanvas as a write-back cache during Web replay.

`tools/export_replay_demo_record.py` writes
`public_artifact_policy.contract_version = replay-public-artifact-policy.v1`
into new minimal ReplayRecords. `tools/prepare_replay_qa_artifact.py` also
normalizes the copied QA artifact with the same policy, so older records become
explicitly read-only before running public preflight. The policy should include:

- `role = snapshot_consumer`.
- `playcanvas_writeback_allowed = false`.
- `local_path_allowed = false`.
- `external_publication_requires_preflight = true`.

PlayCanvas must remain a read-only snapshot consumer. Replay public preflight
rejects PlayCanvas roles such as `source_of_truth` and any non-empty
`mutation_endpoint`, `save_endpoint`, or `write_endpoint` style field because
those fields imply write-back authority. Read-only markers such as
`snapshot_consumer`, `read_only_snapshot_consumer`, `read-only`, `readonly`, or
`disabled` are allowed only as explicit non-write policy values.

## Artifact Rule

The record should store refs, not duplicate every large artifact inline. JSON
artifacts may stay local under `sessions/...` during the demo phase; Cloud/GCS
can later replace `uri` values without changing the contract shape.

Minimum artifact refs:

- `artifacts.replay_script`
- `artifacts.transform_session`
- `artifacts.runtime_package`

Optional refs:

- `body_sim`
- `mocopi_motion`
- `motion_capture`
- `voice_audio`
- `tts_audio`
- `preview_image`
- `video`
- `export_manifest`

Artifact refs must be portable. Do not write `C:\...`, `file://...`, backslash
paths, or root-absolute paths into the record. Use one of:

- Bundle-relative paths, resolved from `portability.bundle_root`.
- `gs://...` object URIs for private GCS storage.
- `https://...` delivery URLs or signed URLs when the export policy allows it.

## External Exhibition PC

The final demo is expected to run on a different exhibition PC. A replay is only
portable when:

- `portability.move_validation.absolute_local_paths_allowed = false`.
- `portability.required_artifact_keys` can be resolved inside the bundle or from
  cloud URIs.
- `validity.valid_when_moved.portable_bundle_required = true` for offline PC
  transfer.
- `validity.valid_when_moved.missing_required_artifact_behavior = invalid`.
- The runtime package snapshot is included, so replay does not depend on the
  authoring PC's current SuitSpec or viewer cache.

Recommended offline bundle layout:

```text
replay-bundles/<bundle_id>/
  replay-record.json
  replay-script.json
  transform-session.json
  runtime-package.json
  media/
    voice-command.webm
    tts.wav
  export-manifest.json
```

## Japanese UI Labels

Stored contract values such as `event_type = DEPOSITION_COMPLETED` and
`playback.view_mode = mirror` remain stable machine-readable codes. Exhibition
UI should not derive Japanese display text from those raw codes. Store display
copy in:

- `presentation.default_locale = ja-JP`
- `presentation.event_labels[]`
- `presentation.view_mode_labels[]`

Every `source_events[].event_type` shown on the exhibition PC should have a
matching `presentation.event_labels[]` entry for `ja-JP`. The display policy
should keep `ui_uses_labels_not_raw_event_types = true` and
`hide_private_ids_on_public_display = true`, so public screens show labels like
`変身開始` or `変身完了` instead of internal event IDs, mocopi session IDs, or raw
operator/device identifiers.

## Mocopi Motion Provenance

Mocopi data is not just a replay frame stream; it is a capture source with its
own session identity and privacy profile. When mocopi contributes motion,
`motion_provenance` should be present with:

- `primary_source = mocopi`.
- `capture_system.provider = mocopi`.
- `session_ref.session_id`: the ReplayRecord-side mocopi session handle.
- `session_ref.source_session_id`: the source mocopi/local adapter session when
  available.
- `frame_rate_hz`: source or normalized capture rate.
- `frame_count`: retained source frame count or normalized replay frame count.
- `timebase`: usually `deposition_elapsed_sec` for replay.
- `coordinate_space`: usually `mocopi_world_y_up` before retargeting.
- `source_artifact_ref`: raw mocopi JSON/stream artifact.
- `derived_artifact_ref`: retargeted replay-motion artifact consumed by the
  runtime.
- `privacy_classification = identifying_motion` unless the data has been
  transformed enough to be non-identifying.

For exhibition use, raw mocopi artifacts should be treated like raw voice audio:
private by default, export-reviewed, and retained only under the consent and
retention policy in the same record.

## Web-Service Operation

`operation` separates local proof files from a service-backed replay archive:

- `mode = local_demo`: local JSON only, useful for current demos.
- `mode = web_service`: API writes record/bundle metadata, artifacts may still
  be local or copied to GCS.
- `mode = cloud_service`: Cloud SQL/GCS is the canonical write path.

For web-serviceized operation, use:

- `operation.storage_backend = cloud_sql_gcs`.
- `operation.write_path = cloud_sql_metadata_gcs_artifacts`.
- `operation.api_surface.replay_record_endpoint` for the future record endpoint.
- `operation.runtime_resolver.artifact_uri_schemes = ["relative", "gs", "https"]`.
- `operation.runtime_resolver.requires_runtime_package_snapshot = true`.
- `operation.external_pc_runtime.preflight_required = true`.

The exhibition PC should run a preflight that validates schema, resolves every
`portability.required_artifact_keys` entry, checks consent/retention flags, and
confirms the runtime package snapshot is present before playback.

## GCP / Cloud Validity

The same record should work after cloud deployment by changing artifact refs,
not by changing the replay semantics:

- SQL owns searchable metadata: `replay_id`, `suit_id`, `recall_code`,
  `manifest_id`, `session_id`, mocopi session ref, consent status, retention
  class.
- GCS owns JSON/media artifacts.
- `validity.valid_in_cloud.uri_schemes` declares accepted ref schemes, normally
  `relative`, `gs`, and `https`.
- `validity.valid_in_cloud.gcp_target = cloud_sql_gcs` means metadata can live in
  Cloud SQL while artifacts live in GCS.
- Signed URLs are acceptable delivery refs only when
  `validity.valid_in_cloud.signed_url_ok = true`.

## Privacy And Retention

Voice audio, transcripts, body motion, `device_id`, and `operator_id` are
potentially identifying. `privacy` records the assumption used when the replay
was written; it is not a substitute for a real exhibition consent flow.

Mocopi raw frames and mocopi session IDs are also potentially identifying. The
contract models that explicitly with `privacy.pii_classes`,
`privacy.motion_storage`, and `privacy.exhibition_pc_policy`.

For internal tests, `operator_consent.status = assumed_for_operator_demo` is
allowed. For public exhibition retention or cloud export, prefer an explicit
`granted` consent record or store only derived/non-identifying metadata.

`media_retention` tells export tooling what can leave the machine:

- `demo_ephemeral`: delete after local verification.
- `exhibition_session`: retain during the event/session.
- `operator_approved_archive`: retain after operator review.
- `cloud_archive`: cloud retention policy applies.

Recommended exhibition-PC constraints:

- `privacy.exhibition_pc_policy.operator_unlock_required = true`.
- `privacy.exhibition_pc_policy.public_display_redaction =
  hide_raw_audio_and_ids` unless a public display has been explicitly approved.
- `privacy.exhibition_pc_policy.raw_media_export_requires_granted_consent =
  true`.
- `media_retention.export_review_required = true` when raw voice or mocopi
  artifacts are present.
- `media_retention.mocopi_raw_retention = delete_after_retarget` when the final
  demo does not require raw mocopi troubleshooting.

## Open Implementation Notes

- `runtime_package_path` does not exist in the current API response yet. The
  first implementation may write the recalled `runtime_package` snapshot beside
  the trial replay script.
- `audio.voice_capture.status = mock` is valid for dry-run demos.
- `playback.view_mode = self` describes the first-person transformation run;
  archive playback should usually record `mirror` or `observer`.
- A replay with missing required bundle artifacts should fail closed rather than
  silently falling back to the current PC's local `sessions/` tree.
- A web-service implementation should keep record metadata queryable even if
  private raw media is later deleted under the retention policy.
