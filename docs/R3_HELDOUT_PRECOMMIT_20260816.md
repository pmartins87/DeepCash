# R3 held-out opening-size precommit — 2026-08-16

This file records the held-out evaluation design **before accepting any held-out result**. It is deliberately separate from the four development/control boards already used to build and debug the R3 common-reference machinery.

## Purpose

The current control evidence favors `O3_25_50_100` over smaller opening-size families once stacks are deep enough for the omitted actions to remain distinct. That evidence cannot by itself justify production selection because the same control boards and range phases have already influenced engineering decisions.

The held-out gate tests whether the ordering generalizes without changing the candidate definitions after results are observed.

## Frozen held-out board families

The first held-out registry contains exactly six deterministic river boards:

1. `K_high_dry_heldout` — `Kc 8d 5s 3h 2c`;
2. `double_paired_heldout` — `Js Jd 6c 6h 2s`;
3. `three_flush_heldout` — `Kh Qh 8h 5c 2d`;
4. `broadway_connected_heldout` — `Ks Qd Jh 5c 2s`;
5. `low_connected_heldout` — `7h 6d 5c 3s 2h`;
6. `trips_board_heldout` — `9s 9h 9d 4c 2h`.

These names/cards are stored separately from the historical control registry. Existing `--boards all` control workflows continue to mean only the original four control boards unless `--board-set heldout` is explicitly requested.

## Frozen range sampling

- exact range combos/player: **6**;
- P0 quantile phase: **0.13**;
- P1 quantile phase: **0.61**.

The control battery used phases `0.00 / 0.27`; the held-out phases are intentionally different so the evaluation is not merely a new board with the same deterministic private-card sample positions.

## Frozen geometry/checkpoints

- pot: 100;
- SPRs: **1 and 4** (stacks 100 and 400);
- checkpoints: **250, 1000, 3000**;
- candidates: `O1_50`, `O2_25_75`, `O3_25_50_100`;
- reference openings: 25%, 50%, 75%, 100% pot, clipped exactly by stack;
- raise-response geometry: held rich/fixed while only opening sizes are restricted;
- all-in openings: exact fold/call/no-raise semantics through empty raise-target sets.

## Interpretation discipline

The workflow is an **evidence gate, not an automatic production selector**. Results must be reported with:

- conservative restriction-loss upper bounds;
- exact-BR interval widths;
- mean and worst held-out board values;
- SPR-specific behavior;
- any candidate collapse caused by geometric clipping.

No candidate may be frozen from this GitHub-hosted result alone. Final action-family selection still requires target-Ryzen cost evidence and must account for raise-size abstraction separately.

Workflow: `.github/workflows/river-raise-opening-heldout-v1.yml`

Launch commit: `df2145abdda4ad2e841a01b8bc58907b533adc16`

`R3 = IN PROGRESS`

`READY FOR TABLES = NO`
