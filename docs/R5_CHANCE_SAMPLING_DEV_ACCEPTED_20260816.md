# R5 chance-sampling development v1 — accepted 2026-08-16

This document accepts the first precommitted chance-sampled CFR control. It isolates chance variance from the additional opponent-action variance present in external sampling.

## Correctness evidence

Precommit: `docs/R5_CHANCE_SAMPLING_PRECOMMIT_20260816.md`.

Original implementation CI run `31965523585`: **PASS**.

A later analytical oracle was added without changing the algorithm. It enumerates every compatible private deal and proves, action by action and infoset by infoset, that the expected one-step sampled regret estimator (`chance=1` on a deal sampled from the true chance distribution) equals the exact full-chance regret delta. This directly protects against missing/double importance weighting. The current broad CI at commit `5d03e14a44a8de28b0233654bb277893e205bc72` completed pytest successfully in run `31965827811`.

Other deterministic gates cover:

- same seed -> bit-identical state/result;
- staged == monolithic training;
- JSON checkpoint -> identical future PRNG/training path;
- wrong variant/game -> fail closed;
- non-finite state -> fail closed;
- exact terminal-leaf accounting for each sampled private deal.

## Numerical battery

Workflow run `31965523599` on source commit `4c630d59e0e80d83c3b0f90de6453e002069ce06`: **PASS**.

Artifact:

- ID `9268412226`;
- SHA-256 `afcecf04db047d8ecb37648d1052da6f6ad31723d0a44fe67588b64a254dfdd9`.

Frozen battery:

- four existing exact river control boards;
- 6 exact combos/player;
- pot 100, stack 400, SPR 4;
- 25% / 50% / 100% action family;
- phases 0.00 / 0.27;
- seeds `11,29,101,20260816`;
- checkpoints `1000,5000,20000`;
- exact best-response evaluation.

## Aggregate result

| iterations | CS CFR linear mean / median / worst | CS CFR+ linear mean / median / worst | mean train s CS / CS+ |
|---:|---:|---:|---:|
| 1,000 | 0.037485 / 0.036166 / 0.065696 | **0.025649 / 0.025132 / 0.034430** | 0.252 / 0.266 |
| 5,000 | 0.015415 / 0.013546 / 0.028009 | **0.010889 / 0.010537 / 0.015201** | 1.250 / 1.330 |
| 20,000 | 0.008116 / 0.007807 / 0.016560 | **0.005879 / 0.005426 / 0.008443** | 4.990 / 5.309 |

At 20k, `CS_CFR_PLUS_LINEAR` also has much lower seed/board dispersion than ordinary chance-sampled CFR:

- CS CFR linear stdev ~`0.003434` pot;
- CS CFR+ linear stdev ~`0.001120` pot.

## Chance sampling vs external sampling

At the same 20,000 sampled iterations:

| sampled control | mean exploitability/pot | worst | stdev | mean hosted train s |
|---|---:|---:|---:|---:|
| `ES_CFR_PLUS_LINEAR` | 0.009886 | 0.012771 | 0.001353 | 4.449 |
| `CS_CFR_PLUS_LINEAR` | **0.005879** | **0.008443** | **0.001120** | 5.309 |

Chance sampling is therefore substantially more accurate on this tiny control at a modest extra per-iteration wall-clock cost. Relative to external sampling at 20k it reduces mean exploitability by roughly 40.5% and worst-cell exploitability by roughly 33.9%, while taking roughly 19.3% more hosted training time.

This isolates a real source of variance: sampling the opponent's actions in addition to chance is materially costly in strategic convergence on the current small river tree.

## Full tree still dominates the tiny control

The accepted exact `CFR_PLUS_LINEAR` control reached approximately:

- mean exploitability/pot `0.000398`;
- worst `0.000455`;
- mean hosted training time ~`2.974 s`

at only 1200 full-tree iterations.

Thus chance sampling, although clearly better than external sampling here, still loses decisively to exact full-tree traversal on the 6x6 microgame. This is expected to be a scale-dependent result rather than a reason to discard sampling globally.

## Accepted interpretation

- regret clipping remains strongly useful under chance sampling;
- `CS_CFR_PLUS_LINEAR` is the leading **chance-sampled control**;
- opponent-action sampling is responsible for a meaningful additional portion of external-sampling variance in this river game;
- exact full-tree CFR+ remains the strongest solver while the exact chance support is tiny;
- R5 should prefer the least stochastic traversal that fits the compute/memory envelope, rather than assuming maximal sampling is automatically efficient;
- the running range-size crossover experiment is now especially important because it will show when exact traversal becomes expensive enough for this tradeoff to change.

`R5 = IN PROGRESS`

`R5 production solver = NOT SELECTED`

`READY FOR TABLES = NO`
