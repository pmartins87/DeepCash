# R5 physical Ryzen crossover v1 — precommit 2026-08-19

Status: **FROZEN BEFORE PHYSICAL RESULT**

## Why this gate exists

The fresh hosted R5 held-out passed decisively: `CCS_CFR_PLUS_LINEAR` beat `ES_ZERO` in 36/36 paired cells with zero timing-quality flags. Hosted runners cannot determine the target-machine crossover, and the sampled held-out did not include the strongest accepted exact control, `ALT_DCFR_150_0_2`.

This gate therefore measures all three accepted controls under equal training wall clock on the physical Ryzen target before a traversal crossover is frozen.

## Frozen algorithms

1. `ALT_DCFR_150_0_2` — accepted exact alternating/DCFR control;
2. `CCS_CFR_PLUS_LINEAR` — held-out-passing correlated-chance sampled challenger;
3. `ES_ZERO` — optimized external-sampling control with legal ZERO baseline.

No algorithm may be added or removed after a physical result exists.

## Fresh physical coordinates

The following exact board strings were repository-searched before this freeze and returned no matches:

- `physical_ace_mid`: `Ac 9s 6d 4h 2c`;
- `physical_king_dynamic`: `Kh Jd 8c 5s 2d`;
- `physical_paired_queens`: `Qs Qd 7h 4c 3s`;
- `physical_connected`: `Td 9c 8h 5d 2s`.

Two range/seed phases are frozen:

- `P_A`: P0 phase `0.11`, P1 phase `0.59`, sampled seed `701`;
- `P_B`: P0 phase `0.37`, P1 phase `0.83`, sampled seed `809`.

Shared geometry:

- exact support/player: `8,24,48` combos;
- pot: `100`;
- bet sizes: `25,50,100`;
- training budget: exactly `30.0 s` per physical cell;
- evaluation/BR time is measured separately and excluded from training budget.

Expected workload: `4 boards × 3 supports × 2 phases × 3 algorithms = 72` isolated sequential cells, or at least 36 minutes of nominal training time plus exact evaluation and process overhead.

## Equal-time execution contract

Each cell starts in a fresh child process. Candidate cells run sequentially; no candidate-level parallelism is allowed. Algorithm order rotates deterministically by public cell index to reduce systematic thermal/order bias.

Timing uses `time.perf_counter()` around training only. Chunk size is estimated from cumulative iterations/second and remaining budget, then clipped to algorithm-specific bounds:

- exact DCFR: initial/min/max `1/1/64`;
- CCS: `64/1/4096`;
- ES_ZERO: `64/1/4096`.

A timing-quality flag is raised when overshoot exceeds `max(0.50 s, 5% of the requested budget)`. Flags are retained; they can never be used to discard an unfavorable cell selectively.

The runner must fail closed when:

- the frozen config/schema/status drifts;
- the tracked Git checkout is dirty;
- CPU/memory instrumentation required by the target OS is unavailable;
- a child cell fails;
- any expected cell identity is missing/duplicated;
- a strategic metric is non-finite.

## Physical evidence recorded

The run bundle must include:

- Git HEAD and config SHA-256;
- OS/platform/Python/processor/logical CPU count/process affinity;
- peak working set/RSS for each isolated cell;
- actual training seconds and overshoot;
- iterations and iterations/second;
- terminal visits/second where the algorithm exposes terminal visits;
- policy EV, BR0, BR1 and exploitability/pot;
- per-support aggregate means/worsts;
- exact pairwise win counts at each support;
- machine-readable decision result;
- per-cell logs, CSV, JSON manifest/results, SHA256SUMS and a single `UPLOAD_ME` ZIP.

## Frozen decision rule

There are eight public cells per support and algorithm: four boards × two phases.

For each support independently, an algorithm is a **resolved physical leader** only if both are true:

1. it has the lowest mean exploitability/pot among all three algorithms;
2. it wins strictly at least `5/8` paired public cells against **each** other algorithm.

If no algorithm meets both conditions, that support is `UNRESOLVED`; no post-hoc tie-breaker is allowed. A future longer-budget repetition must be separately frozen before execution.

If the resolved leader differs by support, the accepted result is a **support-dependent crossover architecture**. We do not force one universal solver merely for implementation convenience. If the same algorithm resolves all supports, a uniform physical leader may be recorded.

`ES_ZERO` remains eligible to win the physical comparison; the prior held-out result does not make an unfavorable physical measurement inadmissible.

## Scope

This is a physical river-control crossover. It can establish target-machine R5/R8 traversal evidence and a support/crossover rule, but it does not independently close R3, the R6 posterior-representation failure, full R5 integration, R8 calibration or READY FOR TABLES.

`R5 physical Ryzen crossover v1 = FROZEN BEFORE RESULT`
