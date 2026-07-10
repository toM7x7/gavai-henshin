# Modeler Handoff Summary

Contract: `modeler-handoff-summary.v1`

## Handoff Message

今回のモデラー依頼は2系統です。既存30variantはファイル受領済みですが、三面図再現性が未達のため30件をfidelity_holdの修正対象にします。別枠でP1 limbは24件が未受け入れで、upperarm/forearm/hand/thighの左右3ライン納品が必要です。作業順はP0の三面図修正7グループを先に処理し、続いてP1の4グループを納品/受入に流してください。canonical/base runtime releaseはpackage gateが通れば進められますが、model deliveryはP1不足と30variant fidelity_holdが解消するまでblockedです。どちらもWeb/Questのpublic runtime activationではなく、受け入れ後に別途runtime activation判断を行います。

## P1 Order Status

- Order items: `24`
- Blocked assets: `24`
- Current stop: `delivery`
- Runtime activation allowed: `False`

## Triview Fidelity Status

- Fidelity hold items: `30`
- Per-part fix request groups: `10`
- Separate missing P1 rows referenced by audit: `24`
- Runtime public activation allowed: `False`

## Modeler Action Queue

| Priority | Source | Scope | Count | Action | Acceptance target |
|---|---|---|---:|---|---|
| `P0` | `triview_fidelity_fix` | `back` | 3 | Back must visibly exceed c01 in completion/density. | review_candidate after sidecar provenance and front/side/back/3Q evidence |
| `P0` | `triview_fidelity_fix` | `chest` | 3 | More final-form density without growing into arm/abdomen interference. | review_candidate after sidecar provenance and front/side/back/3Q evidence |
| `P0` | `triview_fidelity_fix` | `helmet` | 3 | Separate from c01 with crown geometry and denser gold/cyan trim; add side-view proof. | review_candidate after sidecar provenance and front/side/back/3Q evidence |
| `P0` | `triview_fidelity_fix` | `left_boot` | 3 | Increase final-form identity while keeping practical boot mass. | review_candidate after sidecar provenance and front/side/back/3Q evidence |
| `P0` | `triview_fidelity_fix` | `left_shin` | 3 | Tie waist/thigh/shin/boot into one flow after P1 thigh arrives. | review_candidate after sidecar provenance and front/side/back/3Q evidence |
| `P0` | `triview_fidelity_fix` | `right_boot` | 3 | Compare left/right gold/cyan trim and sole shape. | review_candidate after sidecar provenance and front/side/back/3Q evidence |
| `P0` | `triview_fidelity_fix` | `right_shin` | 3 | Compare left/right trim continuity into boots. | review_candidate after sidecar provenance and front/side/back/3Q evidence |
| `P1` | `p1_limb_order` | `upperarm/forearm/hand/thigh left-right 3-line variants` | 24 | Deliver 24 missing P1 limb filesets with GLB, sidecar, source blend, preview mesh, and review evidence. | P1 order validator strict pass with catalog gaps=0 and delivery gaps=0 |
| `P1` | `triview_fidelity_fix` | `left_shoulder` | 3 | More final-form trim density while preserving arm lift. | review_candidate after sidecar provenance and front/side/back/3Q evidence |
| `P1` | `triview_fidelity_fix` | `right_shoulder` | 3 | Check right-side trim does not vanish in Quest view. | review_candidate after sidecar provenance and front/side/back/3Q evidence |
| `P1` | `triview_fidelity_fix` | `waist` | 3 | Add visible gold/cyan continuity to legs; keep hip motion clear. | review_candidate after sidecar provenance and front/side/back/3Q evidence |

## Acceptance Gate

| Gate | Owner | Required result |
|---|---|---|
| `triview_fix_delivery` | modeler | 30 delivered variants keep existing keys and include stronger line identity, sidecar provenance, and full tri-view evidence. |
| `p1_limb_order_delivery` | modeler | 24 P1 limb order items are delivered and catalog-registered without runtime activation. |
| `engineering_validation` | engineering | Run order/fix acceptance commands; no missing delivery, catalog, sidecar, tri-view, or fallback blocker remains. |
| `runtime_release` | release reviewer | Public Web/Quest runtime mapping remains blocked until fidelity_pass and separate activation approval. |

## Runtime Release Note

- Public runtime allowed: `False`
- Canonical/base runtime release can proceed: `True`
- Model delivery blocked: `True`
- Reviewer-only allowed: `True`
- Block label: `blocked_by_p1_order_and_triview_fidelity_hold`
- Distinction: Canonical/base runtime release can proceed if package gates pass; modeler P1 delivery and 30variant fidelity acceptance remain blocked.

- P1 limb variants are still stopped at order/delivery/catalog/runtime activation gates.
- 30 delivered variants are file-valid but remain fidelity_hold until visual identity, evidence, and sidecar provenance pass.
- Any public Web/Quest selector mapping requires a separate runtime activation change after acceptance.
