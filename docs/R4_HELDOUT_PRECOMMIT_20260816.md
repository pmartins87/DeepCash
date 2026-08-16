# R4 representation held-out v1 precommit — 2026-08-16

This file is frozen **before any R4 numerical benchmark result is accepted**.

Purpose: prevent private-state abstraction candidates from being tuned to the same boards/ranges used for final validation, and keep R4 completely separate from the still-active R3 held-out evidence.

## Candidate generation entering this validation

The first deterministic generation is fixed to:

- `category`
- `strength4`
- `equity4`
- `equity8`
- `category_equity4`
- `equity4_blocker2`
- `equity8_blocker2`

No learned representation enters held-out v1. If development evidence motivates a new feature, different bucket count, counterfactual-value clustering or learned encoder **after this file**, that new generation does not get to reuse held-out v1 as unseen evidence; a new held-out generation must be frozen first.

## Exact common reference

Every candidate is evaluated on the same exact river game:

- exact physical cards and card removal;
- exact showdown evaluator;
- exact range compatibility;
- fixed rich one-bet action reference from `ONE_BET_REFERENCE_FRACTIONS`;
- exact-combo private infosets as the reference;
- candidate compression applied to one player at a time;
- candidate policy expanded back to exact combo keys before best-response evaluation.

Joint candidate-vs-candidate solves are diagnostics only. Selection is based on one-sided restriction evidence, compression and compute cost.

## Frozen held-out boards

Registry: `deepcash_core/river_representation_fixtures.py::R4_REPRESENTATION_HELDOUT_V1_BOARDS`

1. `king_wheel_dry_r4` — `Kd 7c 4h 3s 2d`
2. `ace_paired_r4` — `Ac Ad 9h 6s 2c`
3. `three_club_connected_r4` — `Jc 9c 7c 5d 2h`
4. `broadway_four_straight_r4` — `Ad Kc Qs Jd 3h`
5. `low_double_paired_r4` — `6s 6d 3c 3h Kh`
6. `quads_board_r4` — `8c 8d 8h 8s Ac`
7. `mid_connected_rainbow_r4` — `Td 9c 7h 6s 4d`
8. `four_spade_r4` — `Ks Js 8s 5s 2d`

These names/cards are distinct from R3 control, held-out-v1 and held-out-v2 registries.

## Frozen range geometry

Held-out v1 uses two deterministic range phase pairs:

- phase pair A: P0 `0.19`, P1 `0.47`
- phase pair B: P0 `0.58`, P1 `0.83`

Range size: **8 exact combos per player**.

The `quantile_range` function remains the deterministic range constructor. Private card compatibility is still resolved exactly at chance traversal time.

## Frozen SPR/action geometry

Pot: `100` chips.

SPR cells:

- SPR 1: stack `100`
- SPR 2: stack `200`
- SPR 4: stack `400`

Minimum bet: `20` chips.

The laboratory action set is the rich one-bet reference, materialized independently in each SPR cell with normal stack clipping. R4 held-out v1 therefore measures representation generalization across several action geometries without depending on the eventual R3 production-size freeze.

## Frozen convergence checkpoints

- 300 CFR+ iterations
- 1,200 CFR+ iterations
- 3,600 CFR+ iterations

A candidate is not accepted from an unconverged cell merely because its apparent loss is small. Difficult cells may be rerun at larger budgets, but the original result remains part of the audit trail.

## Decision discipline

Held-out v1 does **not** automatically select the smallest representation or the lowest raw loss.

The eventual R4 decision must consider, at minimum:

1. worst conservative restriction-loss upper bound across held-out cells;
2. mean restriction loss;
3. exact-combo compression ratio;
4. action-slot / infoset reduction;
5. equal-wall-clock performance on the physical Ryzen 9;
6. invariance tests, including global suit permutation;
7. stability across range phases and board families.

The final representation may be a later counterfactual-value or learned candidate, but such a candidate requires a new unseen validation generation if held-out v1 has already informed its design.

Current state: **PRECOMMITTED / NOT RUN**.

`R4 = PENDING / ENGINEERING STARTED`

`READY FOR TABLES = NO`
