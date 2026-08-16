# R5 exact tabular solver development v1 — accepted 2026-08-16

R5 is now **IN PROGRESS**. This document accepts the first precommitted exact small-game solver comparison as development evidence. It does **not** select the production solver.

## Correctness gate

The implementation was frozen before numerical inspection in `docs/R5_TABULAR_SOLVER_PRECOMMIT_20260816.md`.

General CI run `31964902028` on commit `ad802d6008a667b0eb058a3a2715fddc69d606ac`: **PASS**.

The tests prove:

- `CFR_PLUS_LINEAR` reproduces the legacy DeepCash `solve_river_cfr_plus` result exactly on the frozen fixture;
- staged training equals monolithic training for all four variants;
- JSON checkpoint roundtrip preserves the exact future path for all four variants;
- a checkpoint cannot be resumed under another solver variant;
- non-finite checkpoint corruption fails closed.

## Benchmark gate

Workflow run `31964902076` on the same commit: **PASS**.

Artifact:

- ID `9268225276`;
- SHA-256 `53fca369a4856faafbd1a7427335a1bda0399e21c8d4835c99cb4a36598110e0`.

Frozen battery:

- four R3 development control boards;
- exact HU river chance/card removal/payoffs;
- fixed 25% / 50% / 100% bet family for every solver;
- 6 exact combos/player;
- range phases 0.00 / 0.27;
- pot 100, stack 400, SPR 4;
- checkpoints 100 / 400 / 1200;
- exact best-response evaluation at every checkpoint.

Variants:

- `CFR_UNIFORM` — ordinary cumulative regrets + uniform average;
- `CFR_LINEAR` — ordinary cumulative regrets + linear average;
- `CFR_PLUS_UNIFORM` — non-negative regret clipping + uniform average;
- `CFR_PLUS_LINEAR` — non-negative regret clipping + linear average.

## Aggregate exploitability per pot

| checkpoint | CFR uniform mean/worst | CFR linear mean/worst | CFR+ uniform mean/worst | CFR+ linear mean/worst |
|---:|---:|---:|---:|---:|
| 100 | 0.013971 / 0.016431 | 0.023752 / 0.030792 | 0.011732 / 0.014202 | **0.006888 / 0.008535** |
| 400 | 0.005402 / 0.006208 | 0.012471 / 0.017137 | 0.003894 / 0.005189 | **0.001552 / 0.002378** |
| 1200 | 0.002648 / 0.003149 | 0.006388 / 0.009714 | 0.001430 / 0.001809 | **0.000398 / 0.000455** |

At checkpoint 1200, mean exploitability of `CFR_PLUS_LINEAR` is approximately:

- 6.65x lower than ordinary CFR + uniform averaging;
- 16.04x lower than ordinary CFR + linear averaging;
- 3.59x lower than CFR+ + uniform averaging.

No meaningful hosted-run training-cost penalty accompanied the advantage. Mean cumulative training time across the four boards at 1200 iterations was approximately:

- CFR uniform: 2.958 s;
- CFR linear: 2.956 s;
- CFR+ uniform: 2.986 s;
- CFR+ linear: 2.974 s.

These hosted-CI times are only gross engineering evidence; they are not the target-Ryzen equal-compute gate.

## Important negative result

`CFR_LINEAR` is not merely weaker in this small battery; its average-strategy convergence is visibly unstable/non-monotonic on some cells. On A-high dry, exploitability/pot moved from about 0.006617 at 400 iterations back up to 0.009714 at 1200. The result is preserved rather than hidden.

The important lesson is not that linear averaging is intrinsically bad. In this experiment, **linear averaging without CFR+ regret clipping is a poor combination**, while CFR+ plus linear averaging is clearly the strongest of the four exact tabular controls.

## Accepted interpretation

`CFR_PLUS_LINEAR` becomes the **leading exact tabular control** for subsequent R5 comparisons.

This does not authorize a production choice because the scalable 6-max problem cannot use synchronous full-tree traversal. R5 must next determine how much convergence is lost and how much wall-clock is gained by sampled traversal methods, then compare neural approximators only after sampled exact controls are trustworthy.

Immediate R5 sequence:

1. deterministic external-sampling MCCFR with exact-game evaluation;
2. deterministic checkpoint/resume including RNG state;
3. equal-visit/equal-wall-clock comparison against this exact CFR+ control on tractable games;
4. outcome-sampling only if it offers a plausible compute/memory advantage;
5. Deep CFR / neural regret-value candidates after sampling correctness is established;
6. physical Ryzen comparison before production freeze.

`R5 = IN PROGRESS`

`R5 production solver = NOT SELECTED`

`READY FOR TABLES = NO`
