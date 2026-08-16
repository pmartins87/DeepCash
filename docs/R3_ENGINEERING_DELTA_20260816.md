# R3 engineering delta — 2026-08-16

This note records engineering added after the last canonical `R3_VALIDATION_STATUS.md` update. It does **not** promote any new item to PASS by itself; canonical promotion still requires the corresponding CI evidence and later Ryzen evidence where required.

## 1. Reference-convergence diagnostics

Added `tools/analyze_river_reference_convergence.py`.

It reports, without inventing a post-hoc strategic threshold:

- first/last exact-BR value-interval width;
- first/last conservative restriction-loss upper bound;
- whether interval width tightened monotonically;
- latest-checkpoint mean/worst restriction upper bounds;
- latest-checkpoint mean/worst exact-BR interval widths;
- cumulative training cost diagnostics.

Regression tests deliberately allow non-monotonic intermediate noise to remain visible instead of relaxing or rewriting evidence.

## 2. R1 adversarial fixtures

Added `tests/test_r1_adversarial.py` and a dedicated workflow.

The new fixtures target:

- cumulative short raises just below the full-raise threshold;
- cumulative short raises exactly reaching the reopen threshold;
- material difference between `ANY_INCREASE` and `NEVER` reopen policies;
- four-way nested preflop side pots with three distinct eligibility layers;
- explicit odd-chip ordering rather than accidental physical-seat ordering.

These tests improve generic-engine coverage but do not replace target-site evidence for the actual short-all-in/reopen and odd-chip rules.

## 3. One-raise common-reference game

Added `deepcash_core.river_raise_reference_lab`.

It extends the exact river control to independent P0/P1 opening bet sets while preserving one raise depth. This makes it possible to solve:

- `R vs R`;
- `C vs R`;
- `R vs C`;

inside a tree where raises exist, instead of measuring opening-size restriction only in the no-raise control.

The first restriction experiment intentionally isolates **opening-size loss**: rich raise responses remain available while only one player's opening sizes are restricted.

## 4. Dynamic exact best response

Added two dynamic-programming exact-BR oracles:

- `deepcash_core.river_reference_dp` for the asymmetric one-bet reference game;
- `deepcash_core.river_raise_reference_dp` for the asymmetric one-raise reference game.

Both retain the older pure-plan enumerators as independent correctness controls. Tests compare DP and enumeration on tractable policies before DP is allowed to accelerate richer reference games.

This is important because pure-plan enumeration grows exponentially with action width, while the dynamic oracle exploits the tree structure and can keep exact-BR evaluation affordable as the reference set grows.

## 5. Resumable one-raise reference training

Added `deepcash_core.river_raise_reference_training`:

- deterministic CFR+ state;
- exact game/action signature;
- cumulative global iteration accounting;
- staged resume;
- JSON checkpoint schema;
- result evaluation through dynamic exact BR.

Regression tests compare staged training with the monolithic one-raise solver and require checkpoint roundtrip to preserve the exact future training path.

## 6. Multi-SPR common-reference battery

Added a common-reference geometry battery over representative river SPR controls:

- SPR 0.5;
- SPR 1;
- SPR 2;
- SPR 4.

Candidate and reference sizings are re-materialized under each pot/stack geometry, so clipping/all-in effects are part of the measured action space rather than ignored.

A dedicated analyzer aggregates mean/worst conservative restriction bounds across `geometry × board` cells.

## 7. Package-safe benchmark fixtures

Shared river benchmark fixtures were moved into the installed `deepcash_core.river_benchmark_fixtures` module for new v2 workflows. This avoids depending on one executable script importing another executable script through environment-specific Python path behavior.

The v2 workflows are the intended package-safe engineering path for DP reference convergence and multi-SPR smoke batteries.

## Promotion rule

None of these additions selects S1/S2/S3/S4 or any one-raise action family.

R3 still requires all of the following before action-family freeze:

1. exact-BR intervals tight enough that common-reference restriction bounds are informative;
2. held-out board/range expansion;
3. multi-SPR evidence;
4. one-raise common-reference evidence;
5. physical Ryzen equal-wall-clock evidence;
6. precommitted selection/tie-break criteria.

`R3 = IN PROGRESS`

`READY FOR TABLES = NO`
