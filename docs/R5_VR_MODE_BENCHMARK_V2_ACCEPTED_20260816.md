# R5 VR-MCCFR mode benchmark v2 — ACCEPTED 2026-08-16

Run `31975899761`: **PASS**.

Artifact `9271052796`, SHA-256 `371737a22e72e2b4e31ea3f4b09ac24ab32b58827346b3bd555137b95e99f980`.

The workflow first passed the corrected algebra/no-leak/integration oracle and then replayed the **unchanged frozen v1 coordinates** after the side-effect bug in the privileged oracle was removed.

## Frozen battery

- 4 existing river control boards;
- 8 combos/player;
- range phases 0.13 / 0.61;
- pot 100;
- bet sizes 25/50/100;
- `ES_CFR_PLUS_LINEAR`;
- 2000 iterations;
- seeds 101, 211, 307, 401, 503;
- 20 runs per mode;
- exact BR evaluation after training.

Hosted timing is engineering evidence only. Physical Ryzen equal-wall-clock remains an R8 gate.

## Global result

| mode | mean exploitability/pot | median | sample stdev | mean train s | relative time vs ZERO |
|---|---:|---:|---:|---:|---:|
| `ZERO` | 0.03427096 | 0.03295081 | 0.00477694 | 0.62274 | 1.00x |
| `INFOSET_EXACT` | 0.03311817 | 0.03399042 | 0.00359434 | 2.93230 | 4.71x |
| `PERFECT_HISTORY` | **0.02969950** | **0.03073631** | 0.00441312 | 0.95958 | 1.54x |

Relative to `ZERO`:

- legal `INFOSET_EXACT` reduces mean exploitability by about **3.36%**, winning 11/20 paired board-seed cells;
- privileged `PERFECT_HISTORY` reduces mean exploitability by about **13.34%**, winning 14/20 paired cells;
- `PERFECT_HISTORY` beats `INFOSET_EXACT` in 15/20 paired cells.

The global standard deviation across adaptive training seeds is not itself an estimator-variance oracle; it includes changed future policies and chance trajectories. The fixed-history tests are the correct proof that `PERFECT_HISTORY` removes opponent-action sampling variance at a node.

## Per-board mean exploitability/pot

| board | ZERO | INFOSET_EXACT | PERFECT_HISTORY |
|---|---:|---:|---:|
| A-high dry | 0.0342064 | 0.0340089 | **0.0303580** |
| four-flush | 0.0358227 | 0.0329670 | **0.0327763** |
| four-straight | 0.0317361 | 0.0308190 | **0.0273323** |
| paired | 0.0353186 | 0.0346777 | **0.0283314** |

`INFOSET_EXACT` helps most clearly on the four-flush cell and only marginally on A-high dry at this horizon.

## Interpretation

This is useful negative/positive evidence rather than a production winner.

1. The corrected `PERFECT_HISTORY` result confirms that meaningful opponent-action sampling variance remains reducible. The v1 anomaly was therefore implementation contamination, not a real strategic result.
2. Exact legal hidden-support integration recovers only part of that opportunity at a very high CPU multiplier on this implementation. `INFOSET_EXACT` is **not** a production candidate in its current exact form.
3. The exact legal oracle remains valuable as a target: a cheap baseline keyed only by the traverser's private information and public history can try to approximate the same conditional values without enumerating the hidden opponent range every visit.
4. Because the control-variate estimator remains unbiased for arbitrary pre-sample baselines, the next candidate is a deterministic tabular running/bootstrapped baseline learned from previous sampled returns. It must update **after** the current estimator is computed, never with the current sample before correction.
5. The privileged mode remains permanently ineligible for production because it conditions on the realized hidden opponent hand.

## Next R5 gate

Implement and validate a cheap no-private-leak tabular baseline with:

- key = traverser private combo + public decision node + action;
- no realized opponent private hand in key or API;
- baseline value fixed before the current sample is used;
- post-estimator running update;
- deterministic seed behavior;
- staged/checkpoint/resume exact future-path equivalence;
- exact unbiasedness regression against the baseline-enhanced estimator;
- equal frozen comparison against `ZERO` and the `INFOSET_EXACT` target.

Only after that should variance reduction be combined with the strongest sampled regret-update candidate.
