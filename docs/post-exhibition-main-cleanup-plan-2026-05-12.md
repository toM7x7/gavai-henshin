# Post-Exhibition Main Cleanup Plan - 2026-05-12

Purpose: create a small, reviewable cleanup path from `main` after the
exhibition rush, without reverting or overwriting the current mixed worktree.

Scope:

- This is a docs-only planning artifact.
- Do not commit the current dirty tree as one unit.
- Do not revert edits made by other agents.
- Build the cleanup branch from current `main`, then stage only reviewed paths.
- Treat raw evidence, generated files, and unfinished feature/asset work as
  deferred unless a release owner explicitly promotes them.

## Current Dirty State

Observed from `git status --short --branch` on 2026-05-12:

```text
current branch: codex/new-route-canonical-identity-lock
upstream: origin/codex/new-route-canonical-identity-lock
```

The worktree is a mixed exhibition worktree, not a main-ready changeset.

High-signal groups:

| Area | Current signal | Cleanup decision |
|---|---:|---|
| `README.md`, `PROJECT_STRUCTURE.md`, `.gitignore`, env templates | Modified / untracked root policy files | Candidate for main cleanup after review. |
| `docs/**` | Many untracked docs plus 2 modified docs | Candidate only after indexing and de-duplicating active docs. |
| `src/henshin/**`, `schemas/**`, `examples/*.json` | Runtime/API and schema/sample changes | Candidate only with matching tests and release package validation. |
| `viewer/armor-forge/**`, `viewer/quest-iw-demo/**`, `viewer/shared/**`, `vite.quest.config.js` | Web/Quest runtime changes | Candidate only after Web/Quest parity and Quest port `5173` checks. |
| `tools/**`, `tests/**` | Many validation/export tools and tests | Candidate only when paired with the behavior they validate. |
| `viewer/assets/armor-parts/**` | Large GLB/Blend/sidecar/catalog and variant work | Split: promote only validated runtime assets; defer creative variants and toppings. |
| `.playwright-cli/**`, `tests/.tmp/**`, `output/**`, root `.tmp-*` | Deleted/generated local outputs | Keep out of main cleanup unless a tiny named report is curated. |
| `qa/**`, `docs/_smoke_renders/**`, `docs/assets/**` | Evidence and render artifacts | Defer by default; promote only reviewed, human-readable summaries. |
| old screenshots/videos/PDFs under `examples/` | Deleted non-machine-readable evidence | Keep deleted from repo; do not reintroduce into `examples/`. |

Compact status count before this doc was added:

```text
modified: .env.example, .gitignore, README.md, package.json, pyproject.toml
modified: docs(2), examples(1), src(9), tests(8), tools(6), viewer(84), vite.quest.config.js
deleted: .playwright-cli(57), output(6), tests/.tmp(95), examples media(7), root temp logs(2)
untracked: PROJECT_STRUCTURE.md, .env.demo.example, docs, examples, qa, schemas, src, tests, tools, viewer
```

## Main-Based Cleanup Branch

Create the branch from `main`, not from the current mixed branch:

```powershell
cd C:\dev\codex\gavai-henshin
git fetch origin
git switch main
git pull --ff-only
git switch -c codex/post-exhibition-main-cleanup-2026-05-12
```

Recommended commit lanes:

1. Repo structure and policy
   - `README.md`
   - `PROJECT_STRUCTURE.md`
   - `.gitignore`
   - `.env.example`
   - `.env.demo.example`
   - Goal: make the root layout, examples policy, generated-output policy, and
     validation entry points current.

2. Active docs index and runbooks
   - Active `docs/*contract*.md`, `docs/*readiness*.md`, `docs/exhibition-*.md`,
     and current Web/Quest checklists.
   - Goal: keep one readable post-exhibition path; summarize or archive stale
     handoffs instead of leaving every dated note in the main reading path.

3. Runtime/API contract
   - `src/henshin/**`
   - `schemas/**`
   - machine-readable `examples/*.sample.json` and `examples/*.fixture.json`
   - matching `tests/test_*.py`
   - Goal: preserve the Forge -> Quest recall contract and replay/schema shape.

4. Web/Quest runtime
   - `viewer/armor-forge/**`
   - `viewer/quest-iw-demo/**`
   - `viewer/shared/**`
   - `vite.quest.config.js`
   - matching browser/runtime tests.
   - Goal: preserve the local exhibition route on `8010` and fixed Quest
     runtime port `5173`.

5. Validation and release tooling
   - `tools/audit_*`
   - `tools/validate_*`
   - `tools/export_*`
   - matching tests.
   - Goal: make the cleanup mechanically auditable before any push.

6. Curated runtime assets
   - `viewer/assets/armor-parts/variant_catalog.json`
   - only GLB, `.modeler.json`, preview mesh, and master files that pass the
     catalog, GLB, and whole-suit gates.
   - Goal: promote the smallest asset set needed by the public runtime.

Stage with path-level review:

```powershell
git add -p <path>
git diff --cached --stat
git diff --cached --check
git diff --cached --name-only
```

## Deferred Feature And Asset Work

Keep these out of the main cleanup branch unless they receive a separate owner,
acceptance gate, and validation run:

- MOCOPI, PlayCanvas, hosted service, and GCP work that is not required for the
  local post-exhibition baseline.
- Wave 2 creative variants, toppings, texture prompts, and unaccepted modeler
  deliveries.
- Modeler work still marked `fidelity_hold`, `metadata_hold`, or equivalent.
- Raw Quest/Web screenshots, videos, Playwright captures, smoke render images,
  `qa/logs`, and generated `tests/.tmp` outputs.
- Broad documentation history that is not an active contract, runbook, index, or
  decision record.
- Any large asset folder that does not have a catalog reference and passing
  validation evidence.

If a deferred item becomes release-critical, promote it through a dedicated
feature branch first, then merge the reviewed result into the main cleanup lane.

## Validation Commands

Run inventory before staging:

```powershell
cd C:\dev\codex\gavai-henshin
git status --short --branch
git diff --name-only
git ls-files --others --exclude-standard
python tools\audit_project_structure_cleanup.py --repo-root . --fail-on-findings
python tools\list_release_stage_candidates.py --repo-root . --summary-json --no-ignored
python tools\audit_repo_readiness.py --repo-root . --no-ignored --fail-on-blocked
```

Run core local validation before opening a PR:

```powershell
cd C:\dev\codex\gavai-henshin
$env:PYTHONPATH = "$PWD\src"
python -m pip install -e ".[dev]"
npm ci
node --check viewer\quest-iw-demo\quest-demo.js
node --check viewer\armor-forge\forge.js
python -m pytest tests\test_new_route_api.py tests\test_runtime_package.py tests\test_quest_recall_render_contract.py tests\test_dashboard_server.py -q
python -m pytest tests\test_exhibition_smoke_check.py tests\test_validate_exhibition_release_package.py tests\test_smoke_web_glb_load.py tests\test_quest_armor_whole_suit_audit.py -q
python -m pytest -q
npm test
npx vite build --config vite.quest.config.js --outDir tests\.tmp\quest-vite-build-post-exhibition --emptyOutDir
```

Run release package and asset gates:

```powershell
cd C:\dev\codex\gavai-henshin
New-Item -ItemType Directory -Force qa | Out-Null
python tools\validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_post_exhibition.json
python tools\smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_post_exhibition.json
python tools\audit_quest_armor_whole_suit.py --output qa\quest_armor_whole_suit_post_exhibition.json --fail-on fail
python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --include-delivered-assets
```

For a true main-ready claim, repeat the key checks from a clean clone or detached
cleanup-branch commit:

```powershell
$releaseCommit = "<cleanup-branch-commit-sha>"
$checkRoot = "C:\henshin-release-check\$releaseCommit"
New-Item -ItemType Directory -Force $checkRoot | Out-Null
cd $checkRoot
git clone <repo-url> gavai-henshin
cd $checkRoot\gavai-henshin
git fetch --all --tags --prune
git switch --detach $releaseCommit
git rev-parse HEAD
git status --short --branch
$env:PYTHONPATH = "$PWD\src"
python -m pip install -e ".[dev]"
npm ci
node --check viewer\quest-iw-demo\quest-demo.js
node --check viewer\armor-forge\forge.js
python -m pytest tests\test_new_route_api.py tests\test_runtime_package.py tests\test_quest_recall_render_contract.py tests\test_dashboard_server.py tests\test_quest_armor_whole_suit_audit.py -q
New-Item -ItemType Directory -Force qa | Out-Null
python tools\validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_clean_clone.json
python tools\smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_clean_clone.json
python tools\audit_quest_armor_whole_suit.py --output qa\quest_armor_whole_suit_clean_clone.json --fail-on fail
```

Expected release gates:

- `git status --short --branch` has no surprise runtime, tool, test, or asset
  paths.
- Structure audit has no blocked generated-output or misplaced evidence
  findings.
- Release package validation reports no missing required runtime files.
- GLB smoke has no load failures.
- Whole-suit audit reports `status=pass`.
- Quest remains on fixed port `5173`; do not silently move the Quest runtime to
  another port to avoid a local conflict.
- Generated `qa/*.json` and `tests/.tmp/**` outputs are not staged unless a
  specific reviewed report is intentionally promoted.
