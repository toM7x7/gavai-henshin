# Project Structure

This file is the source of truth for keeping `gavai-henshin` as a single,
reviewable project after the exhibition phase.

## Canonical Root

Keep these directories at the repository root:

```text
src/        Python package and local API/runtime logic
viewer/     Web Forge, Quest runtime, shared browser code, and runtime assets
tools/      Operator, validation, export, and maintenance scripts
tests/      Python and browser contract tests
schemas/    JSON schemas and public data contracts
examples/   Small JSON samples and fixtures only
docs/       Active contracts, runbooks, and reviewed design notes
config/     Non-secret local configuration templates and certificates
infra/      Deployment and service infrastructure notes/config
qa/         Curated QA manifests only; raw logs/media stay out of GitHub
```

Root files should stay limited to project metadata and entry points:

```text
README.md
PROJECT_STRUCTURE.md
package.json
package-lock.json
pyproject.toml
vite.quest.config.js
.gitignore
.env.example
.env.demo.example
Dockerfile
.dockerignore
CONTRIBUTING.md
LICENSE
Lore Bible.md
blueprint.md
```

## Do Not Move Without a Contract Change

These paths are used directly by code, tests, or operator scripts:

```text
examples/suitspec.sample.json
examples/partcatalog.seed.json
examples/suitmanifest.sample.json
examples/mocopi_sequence.sample.json
viewer/assets/armor-parts/variant_catalog.json
viewer/assets/armor-parts/<part>/**
viewer/assets/meshes/**
viewer/assets/vrm/default.vrm
viewer/assets/vrm/baselines.json
viewer/armor-forge/**
viewer/quest-iw-demo/**
viewer/shared/**
schemas/**
src/henshin/**
tools/**
tests/**
```

If any of these paths must move, update the runtime code, tests, docs, and
release classification tools in the same change.

## Generated and Local-Only Areas

These paths are local outputs or workspaces. They are not part of the normal
GitHub release:

```text
sessions/
qa/logs/
tests/.tmp/
output/
dist/
build/
node_modules/
.pytest_cache/
.playwright-cli/
.playwright-mcp/
.claude/
blender/
*.log
.tmp-*
armor-forge-japanese-ui-*.png
```

The exhibition evidence that had been mixed into `examples/` and the repo root
was moved out of the project tree to:

```text
D:\personal_dev\gavai-henshin\gavai-henshin-local-archive\evidence-2026-05
```

The same archive root also holds `post-exhibition-cleanup-2026-05-12\`, which
preserves the worktree snapshot containing the 30 fidelity-hold line-variant
armor filesets (see `docs/model-readiness-2026-07.md`).

That archive is for local historical reference only. Do not copy it back into
the repository unless a small named artifact is explicitly promoted.

## Examples Policy

`examples/` should stay small and machine-readable. It is for sample JSON and
fixtures used by tests, tools, and local demos.

Allowed examples:

```text
*.sample.json
*.fixture.json
partcatalog.seed.json
```

Not allowed in `examples/`:

```text
screenshots
Quest photos
recording videos
zip bundles
ad-hoc user messages
embedded PoC applications
node_modules
```

## Docs Policy

Docs should be split by role:

```text
Active contracts: docs/*contract*.md and docs/*readiness*.md
Operator runbooks: docs/exhibition-*.md and current Quest/Web checklists
Modeler records: docs/modeler-*.md while they are still current
Historical evidence: external local archive, or a reviewed docs archive package
```

When a dated document stops being the active source of truth, either summarize
it in a current doc or move it to an explicit archive package. Do not leave old
handoffs in the main reading path without a current index.

## Cleanup Audits

Use these read-only commands before staging or moving large groups of files:

```powershell
python tools/audit_project_structure_cleanup.py --repo-root . --fail-on-findings
python tools/list_release_stage_candidates.py --repo-root . --summary-json --no-ignored
python tools/audit_repo_readiness.py --repo-root . --no-ignored --fail-on-blocked
```

The first command checks the filesystem structure. The second and third commands
classify dirty Git paths so generated evidence, local workspaces, and raw QA
artifacts do not enter a GitHub push by accident.

## Next Phase Lanes

After this cleanup, keep future work in these lanes:

```text
Web service: split static hosting, artifact storage, API runtime, and provider workers.
Quest runtime: improve body tracking, mocopi fallback behavior, and VR interaction.
Asset pipeline: promote only catalog-referenced armor assets into viewer/assets.
Replay: keep records portable and validate public replay artifacts.
GitHub readiness: stage release-critical code, docs, and armor assets separately.
```

