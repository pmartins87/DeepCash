# R5 equal-wall-clock/scaling comparison — precommit 2026-08-17

Status: **PRECOMMITTED_NOT_RUN**

## Purpose

Measure how the accepted R5 traversal/variance primitives trade strategic error for real hosted-CPU time as private-range support grows. This is a development scaling gate only. It does not select a production solver and cannot replace the physical Ryzen 9 comparison required before R5/R8 exit.

The run must not start while the currently active R4 v1/v2 development workflows are consuming hosted CI.

## Frozen comparators

1. `ES_ZERO` — optimized `ES_CFR_PLUS_LINEAR` with the legal ZERO baseline.
2. `ES_TABULAR_RUNNING` — the same optimized external-sampling regret/average update with the accepted no-private-leak running tabular baseline.
3. `CCS_CFR_PLUS_LINEAR` — accepted persistent randomized Weyl allocation at the private-deal chance node with full action-tree CFR+ traversal.
4. `ES_INFOSET_EXACT` — optimized external sampling with the accepted exact legal-information conditional baseline, retained only as an expensive reference.

These are separate comparators. This run does **not** claim or construct a hybrid CCS+external/tabular solver:

- CCS samples the private-deal chance node and traverses the complete action tree;
- TABULAR_RUNNING corrects sampled opponent actions inside external sampling.

Any future integration of Weyl chance allocation into external/VR traversal requires a distinct structural, unbiasedness, determinism and checkpoint gate before its numerical results may be consumed.

## Frozen development coordinates

Boards:

- `A_high_dry`;
- `four_straight`.

Range support:

- exact combos/player: `8,24,48`;
- P0 quantile phase: `0.13`;
- P1 quantile phase: `0.61`.

Game geometry:

- pot: `100`;
- river bet sizes: `25,50,100`;
- no post-hoc change to boards, phases, ranges or action family.

Seeds:

- `101,211,307`.

Cumulative hosted training-time budgets per board × range × seed × comparator:

- `1.0 s`;
- `5.0 s`;
- `15.0 s`.

Evaluation time is measured separately and excluded from the training budget.

## Time-budget execution contract

Each comparator starts from a clean state for its board/range/seed cell and advances cumulatively in bounded chunks until it reaches each time budget.

- Timing uses `time.perf_counter()` around training only.
- Chunk size starts at 64 iterations.
- After each chunk, the next chunk is deterministically bounded to `[1, 4096]` iterations from the observed iterations/second and remaining budget.
- A checkpoint is the first completed chunk at or beyond the target budget.
- The artifact records requested budget, actual cumulative training seconds, overshoot, iterations and terminal visits.
- Policy evaluation and exact BR run only after the checkpoint is frozen.
- No result may be normalized by iteration count alone; interpretation uses actual time, range/deal support and exact strategic metrics.
- Wall-clock iteration counts are intentionally machine-dependent. Given a recorded checkpoint state, policy/BR evaluation remains deterministic.

A checkpoint with time overshoot greater than `max(0.10 s, 5% of its requested budget)` is flagged for timing-quality review. This is not a strategic PASS/FAIL threshold and must not be used to discard an unfavorable candidate selectively.

## Required pre-run structural gate

Before any numerical cell:

- external-sampling optimized-deal sequence/regression tests;
- ZERO VR integration identity;
- TABULAR_RUNNING first-iteration identity, same-seed determinism, staged equivalence, JSON future-path equivalence and no-realized-opponent-hand key/API tests;
- INFOSET_EXACT no-private-leak boundary tests;
- CCS phase/sequence, checkpoint and deterministic replay tests.

A failure blocks the entire numerical artifact. Partial cells are never promotable.

## Artifact schema and rows

Schema: `DEEPCASH_R5_EQUAL_WALLCLOCK_SCALING_V1`.

Every row records:

- board, range combos/player, compatible deal count and seed;
- comparator and requested time budget;
- actual cumulative training seconds and overshoot;
- iterations, iterations/second and terminal visits/second;
- policy EV, BR0, BR1 and exploitability/pot;
- evaluation seconds;
- for TABULAR_RUNNING: baseline slots, visited slots, update count and coverage.

The artifact also reports per range × budget × comparator:

- cell count;
- mean/median/worst exploitability per pot;
- sample standard deviation;
- mean actual training seconds and timing overshoot;
- mean throughput;
- paired wins and mean/median exploitability delta versus `ES_ZERO`.

At 15 seconds it additionally reports Pareto dominance by range support and the gap from TABULAR_RUNNING to INFOSET_EXACT.

## Acceptance discipline

No post-hoc absolute exploitability threshold is permitted.

- `ES_TABULAR_RUNNING` remains a serious candidate only if its strategic/time tradeoff stays useful as range support grows; domination by ES_ZERO is accepted negative evidence.
- `CCS_CFR_PLUS_LINEAR` is compared fairly by actual time, while its different traversal semantics remain explicit.
- `ES_INFOSET_EXACT` is an oracle-quality legal reference, not a production favorite.
- A winner on one board, seed, range or budget is not a production winner.
- Hosted-CI timing is engineering evidence only.
- The final R5 choice still requires compatible R3/R4 freezes, held-out validation and equal-wall-clock reproduction on the physical Ryzen 9.
- Failed, partial or timing-quality-flagged runs remain in the audit trail and are never silently overwritten.

`R5 equal-wall-clock/scaling v1 = PRECOMMITTED_NOT_RUN`
