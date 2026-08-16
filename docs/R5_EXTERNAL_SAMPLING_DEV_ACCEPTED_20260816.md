# R5 external-sampling MCCFR development v1 — accepted 2026-08-16

This document accepts the first precommitted deterministic external-sampling control, including its **negative small-game efficiency result**. It does not reject sampling for the large 6-max problem; it establishes that sampling is not automatically beneficial when the exact tree is already tiny.

## Correctness

Precommit: `docs/R5_EXTERNAL_SAMPLING_PRECOMMIT_20260816.md`.

General CI run `31965167839` on commit `466a6aac1ff075e99b1afb5a5299cdb6b6a4ec3a`: **PASS**.

The accepted tests cover:

- same seed -> bit-identical state/result;
- staged training -> bit-identical monolithic training;
- JSON checkpoint roundtrip -> bit-identical future PRNG/training path;
- wrong solver variant -> fail closed;
- non-finite checkpoint corruption -> fail closed;
- exact-BR interval sanity after sampled training.

## Numerical battery

Workflow run `31965167770`: **PASS**.

Artifact:

- ID `9268312419`;
- SHA-256 `40f52a73cc60126c1d31d3261e3dab47962a5d14cf9a6377c18ed114723df552`.

Frozen battery:

- four existing exact river control boards;
- 6 exact combos/player;
- pot 100, stack 400, SPR 4;
- fixed 25% / 50% / 100% action family;
- range phases 0.00 / 0.27;
- seeds `11,29,101,20260816`;
- checkpoints `1000,5000,20000`;
- 16 board/seed cells per variant at each checkpoint;
- exact best response for evaluation.

Variants:

- `ES_CFR_LINEAR`;
- `ES_CFR_PLUS_LINEAR`.

## Aggregate result

| iterations | ES CFR linear mean / median / worst | ES CFR+ linear mean / median / worst | mean train s ES / ES+ |
|---:|---:|---:|---:|
| 1,000 | 0.042763 / 0.042501 / 0.061350 | 0.045171 / 0.044348 / 0.063162 | 0.210 / 0.221 |
| 5,000 | 0.019407 / 0.019887 / 0.027569 | 0.020952 / 0.021423 / 0.027233 | 1.036 / 1.116 |
| 20,000 | 0.010590 / 0.010443 / 0.019640 | **0.009886 / 0.010023 / 0.012771** | 4.108 / 4.449 |

At 20k, `ES_CFR_PLUS_LINEAR` has slightly lower mean exploitability and materially lower dispersion/worst cell than ordinary external-sampling CFR:

- ES CFR linear stdev: ~0.004751 pot;
- ES CFR+ linear stdev: ~0.001353 pot.

Therefore clipping looks useful as the sampled run matures, even though ordinary ES CFR is slightly ahead in mean at the earlier 1k/5k checkpoints.

## Negative efficiency result on the tiny tree

The accepted exact full-tree control achieved at only 1200 iterations:

- mean exploitability/pot ~`0.000398`;
- worst ~`0.000455`;
- mean hosted training time ~`2.974 s`.

The external-sampling CFR+ run at 20,000 iterations achieved:

- mean ~`0.009886`;
- worst ~`0.012771`;
- mean hosted training time ~`4.449 s`.

So on the current **6-combo-per-player microgame**, exact full-tree CFR+ is both faster and dramatically more converged. This is not an implementation result to hide; it is an important architecture boundary.

The reason to keep external sampling in R5 is scaling: exact full-tree iteration cost grows with the full compatible chance/opponent expansion, whereas external sampling pays for sampled chance/opponent paths plus traverser branches. A 6x6 chance support is too small for that asymptotic advantage to matter.

## Accepted interpretation

- `CFR_PLUS_LINEAR` remains the dominant exact small-game oracle/control.
- `ES_CFR_PLUS_LINEAR` becomes the leading **external-sampling engineering candidate** from this first sampled generation because its late-checkpoint mean/worst/variance are better than ordinary ES CFR.
- external sampling is **not competitive on the tiny 6x6 range game**;
- the next experiment must measure the crossover as exact range/chance support expands rather than extrapolating from this tiny control.

A production solver is still not selected. The next R5 gate should compare exact CFR+ and ES CFR+ across increasing exact range sizes, then proceed to larger sampled/public-state games and neural approximation only after the crossover is understood.

`R5 = IN PROGRESS`

`R5 production solver = NOT SELECTED`

`READY FOR TABLES = NO`
