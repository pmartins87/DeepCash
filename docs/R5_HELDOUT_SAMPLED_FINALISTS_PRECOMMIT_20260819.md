# R5 sampled-finalist held-out v1 — precommit 2026-08-19

Status: **FROZEN BEFORE FIRST NUMERICAL RUN**

The hosted scaling-development gate has already been consumed. This document freezes a fresh R5-specific held-out test before either finalist is evaluated on these coordinates.

## Purpose

Test whether the development advantage of `CCS_CFR_PLUS_LINEAR` over the optimized `ES_ZERO` external-sampling control generalizes to previously unused public boards, new range quantile phases and new RNG seeds at equal hosted training wall clock.

This is the last hosted sampled-finalist gate before physical Ryzen reproduction. It cannot by itself select the production R5 traversal.

## Frozen finalists

1. `CCS_CFR_PLUS_LINEAR` — leading sampled finalist from the accepted hosted scaling gate.
2. `ES_ZERO` — optimized `ES_CFR_PLUS_LINEAR` identity-control baseline.

`ES_TABULAR_RUNNING` and `ES_INFOSET_EXACT` are deliberately not reintroduced after their accepted negative production evidence. No new candidate may be added after this freeze.

## Fresh held-out boards

These exact board strings were repository-searched before this precommit and returned no matches:

- `ace_low_mixed_r5ho`: `As 7c 5d 3h 2s`;
- `king_broadway_mixed_r5ho`: `Kc Qs Td 6h 2c`;
- `paired_jacks_r5ho`: `Jh Jc 8s 5d 3c`;
- `three_diamond_connected_r5ho`: `9d 8d 6c 4s 2d`.

They must not be changed after numerical execution starts.

## Frozen range/game coordinates

- exact combos/player: `8,24,48`;
- P0 quantile phase: `0.27`;
- P1 quantile phase: `0.73`;
- pot: `100`;
- river bet sizes: `25,50,100`;
- seeds: `401,503,607`;
- training budget: exactly `15.0 s` cumulative per board × support × seed × finalist;
- policy evaluation and exact BR are outside the training-time budget.

The expected artifact contains `4 boards × 3 supports × 3 seeds × 2 finalists = 72` rows.

## Time-budget contract

Use the same bounded deterministic chunk policy as the accepted scaling gate:

- `time.perf_counter()` around training only;
- initial chunk `64` iterations;
- next chunk estimated from cumulative iterations/second and remaining time;
- chunk clipped to `[1,4096]`;
- checkpoint is the first completed chunk at or beyond 15 seconds;
- record actual training seconds, overshoot, iterations, terminal visits and exact strategic metrics;
- timing-quality flag if overshoot exceeds `max(0.10 s, 5% of requested budget)`.

Timing-quality flags are retained and reviewed; they are never used to discard an unfavorable cell selectively.

## Frozen acceptance rule

No post-hoc absolute exploitability target is permitted.

`CCS_CFR_PLUS_LINEAR` passes this held-out generalization gate only if all of the following are true:

1. the artifact is complete and contains exactly 72 unique cell identities;
2. structural prerequisite tests pass before numerical execution;
3. at each support separately (`8`, `24`, `48`), CCS mean exploitability/pot is no greater than ES_ZERO mean exploitability/pot;
4. at each support separately, CCS wins strictly more than half of the 12 paired board × seed cells, therefore at least `7/12`;
5. across all supports, CCS wins at least `27/36` paired cells (75%);
6. any timing-quality flag is explicitly audited before acceptance.

If any strategic criterion fails, the held-out set must not be tuned against. The result is negative evidence and the R5 finalist decision must return to the previously frozen development evidence/design assumptions.

## Consequence of PASS

A PASS advances both:

- `CCS_CFR_PLUS_LINEAR` as sampled challenger;
- `ES_ZERO` as physical control;

to a physical Ryzen protocol that also includes the exact `ALT_DCFR_150_0_2` control for crossover/scaling measurement.

A hosted PASS still does not mark R5 PASS, R8 PASS or authorize R9.
