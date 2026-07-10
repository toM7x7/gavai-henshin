# Exhibition PC Transfer Checklist

- contract_version: `exhibition-pc-transfer-checklist.v1`
- status: `pass`
- ready_items: `9`
- missing_items: `0`

## Ready Items
- [x] `readme` - README (`README.md`)
- [x] `demo_env_template` - Demo env template (`.env.demo.example`)
- [x] `local_stack_helper` - Local stack helper (`tools/start_exhibition_local_stack.ps1`)
- [x] `adb_reverse_helper` - Quest ADB reverse helper (`tools/start_quest_adb_reverse.ps1`)
- [x] `runbook` - Exhibition PC runbook (`docs/exhibition-pc-runbook-2026-05-04.md`)
- [x] `service_contract_tool` - Service deployment contract tool (`tools/validate_service_deployment_contract.py`)
- [x] `release_package_validator` - Release package validator (`tools/validate_exhibition_release_package.py`)
- [x] `qa_release_manifest` - Release package QA manifest (`qa/exhibition_release_package_latest.json`)
- [x] `replay_qa_artifact` - Replay QA artifact (`qa/replay/*.replay-record.json, qa/replay/*.summary.json, qa/replay-record-*.demo.json`)

## Missing Items
- None

## Manual Steps
1. Copy or unzip the package to C:\henshin-demo\gavai-henshin on the exhibition PC.
2. Run npm install and python -m pip install -e ".[dev]" on the exhibition PC.
3. Copy .env.demo.example to .env only on the exhibition PC, then fill venue-local placeholders if needed.
4. Run the release package validator and keep its JSON under qa/ before doors open.
5. Start the local stack helper with a fresh Web Forge code for the public visitor path.
6. Record local-pass/local-fail before evaluating service, PlayCanvas, or mocopi optional lanes.

## URLs
- `web_forge`: `http://127.0.0.1:8010/viewer/armor-forge/`
- `api_health`: `http://127.0.0.1:8010/api/health`
- `quest_usb_template`: `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>`
- `quest_manual_entry_usb_adb`: `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1`
- `quest_lan_fallback_template`: `http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>`

## USB Quest Steps
1. Connect the Quest to the exhibition PC with a USB-C data cable.
2. Put on the headset and accept the USB debugging prompt.
3. Run adb devices -l and confirm the state is device, not unauthorized or offline.
4. Run .\tools\start_quest_adb_reverse.ps1 -RecallCode <CODE> -CacheBust -LaunchBrowser.
5. Confirm adb reverse --list includes tcp:5173 tcp:5173 and tcp:8010 tcp:8010.
6. Open the Quest USB URL with the same fresh code that Web Forge generated.

## Do Not Copy
- .env files containing real provider secrets or venue-only credentials.
- node_modules/, .venv/, venv/, __pycache__/, or .pytest_cache/ dependency caches.
- Machine-local absolute paths such as C:\dev\codex\gavai-henshin.
- Old Quest Browser tabs, browser cache, or stale recall codes as QA evidence.
- Downloaded cloud credential files or service account keys.

## Recommended Commands
- `python tools/export_exhibition_pc_transfer_checklist.py --report-json`
- `python tools/validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_external_pc.json`
- `.\tools\start_exhibition_local_stack.ps1 -RecallCode <CODE> -LaunchQuest -RequireAdbReverseSmoke`
