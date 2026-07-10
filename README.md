# gavai-henshin

`gavai-henshin` is the local prototype for the route:

```text
Web: Suit Forge -> Quest: Henshin Trial -> Replay: Archive
```

The repo is now organized as one project again. Start with
[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) before moving files or preparing a
GitHub push.

## Quickstart

Install dependencies:

```powershell
cd C:\path\to\gavai-henshin
npm install
python -m pip install -e ".[dev]"
```

Run the dashboard/API:

```powershell
npm run dev
```

Run the Quest viewer:

```powershell
npm run dev:quest -- --host 0.0.0.0 --port 5173
```

Main local URLs:

```text
Web Forge:  http://localhost:8010/viewer/armor-forge/
Dashboard:  http://localhost:8010/viewer/suit-dashboard/
Quest:      http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1
```

Quest runtime port `5173` is fixed for the local Quest path and ADB reverse.
Stop the conflicting process if the port is already occupied.

## Validation

Core contract tests:

```powershell
python -m pytest tests/test_new_route_api.py tests/test_runtime_package.py tests/test_quest_recall_render_contract.py -q
npm test
```

Structure and release cleanup checks:

```powershell
python tools/audit_project_structure_cleanup.py --repo-root .
python tools/list_release_stage_candidates.py --repo-root . --summary-json --no-ignored
python tools/audit_repo_readiness.py --repo-root . --no-ignored
```

Exhibition smoke check:

```powershell
python tools/exhibition_smoke_check.py --forge
```

## Active Docs

- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md): canonical repo layout and cleanup rules.
- [docs/armor-blueprint-generator.md](docs/armor-blueprint-generator.md): intent -> blueprint -> procedural armor GLB generator.
- [docs/armor-body-fit-rules-2026-07.md](docs/armor-body-fit-rules-2026-07.md): measured VRM body-fit rules (armor-body-fit.v1) for wearable assembly.
- [docs/henshin-experience-roadmap-2026-07.md](docs/henshin-experience-roadmap-2026-07.md): product roadmap (公示→適合→蒸着→封印→記録院).
- [docs/cloud-architecture-2026-07.md](docs/cloud-architecture-2026-07.md): cloud lane source of truth (Cloud Run lift-and-shift plan + gates).
- [docs/model-readiness-2026-07.md](docs/model-readiness-2026-07.md): 3D asset inventory, the recovered 30 line variants, and remaining model work.
- [docs/refactor-backlog-2026-07.md](docs/refactor-backlog-2026-07.md): audited refactor items (applied + pending).
- [docs/exhibition-pc-runbook-2026-05-04.md](docs/exhibition-pc-runbook-2026-05-04.md): local exhibition PC runbook.
- [docs/exhibition-pc-local-fallback-migration-manual-2026-05-05.md](docs/exhibition-pc-local-fallback-migration-manual-2026-05-05.md): transfer and fallback manual.
- [docs/web-service-readiness-2026-05-02.md](docs/web-service-readiness-2026-05-02.md): web service and GCP readiness.
- [docs/replay-record-contract.md](docs/replay-record-contract.md): replay record contract.
