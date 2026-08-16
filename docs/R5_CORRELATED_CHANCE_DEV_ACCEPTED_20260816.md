# R5 correlated chance sampling development v1 — accepted 2026-08-16

This document accepts the first precommitted paired IID-vs-correlated chance experiment. Only the temporal allocation of private chance outcomes differs between the two controls.

## Source / implementation gate

Method source: Li, Chen & Huang, *Correlated Chance Sampling for Monte Carlo Counterfactual Regret Minimization*, arXiv:2607.27035.

DeepCash implementation:

- persistent seed-derived random phase `phi`;
- golden-ratio Weyl stream `(phi + n*g) mod 1`, `g=(sqrt(5)-1)/2`;
- exact weighted quantile mapping onto compatible private-card deals;
- same CFR+ regret algebra, action traversal, exact own-reach average strategy and exact BR evaluation as the IID chance-sampling control.

Correctness CI passed before numerical acceptance. Tests cover the exact Weyl formula, discrete quantile boundaries, same-seed identity, staged-vs-monolithic identity, JSON stream/checkpoint future-path identity, exact visit accounting and fail-closed corruption.

## Numerical gate

Workflow run `31966357494`: **PASS**.

Artifact:

- ID `9268623901`;
- SHA-256 `ee2bb35f28eae23fe7f9639bd6ddc9fb47949ea78dc90450a1535f7b5f4a84d4`.

Frozen battery:

- four exact river control boards;
- 6 exact combos/player;
- phases 0.00 / 0.27;
- pot 100, stack 400 / SPR 4;
- 25% / 50% / 100% action family;
- seeds `11,29,101,20260816`;
- checkpoints 1000 / 5000 / 20000;
- paired same-run IID and CCS for every board/seed.

## Aggregate result

| iterations | IID mean / median / worst | CCS mean / median / worst | IID stdev | CCS stdev | mean train s IID / CCS |
|---:|---:|---:|---:|---:|---:|
| 1,000 | 0.025649 / 0.025132 / 0.034430 | **0.013259 / 0.012971 / 0.016565** | 0.004404 | **0.001869** | 0.266 / **0.253** |
| 5,000 | 0.010889 / 0.010537 / 0.015201 | **0.006465 / 0.006129 / 0.008681** | 0.001666 | **0.001189** | 1.324 / **1.263** |
| 20,000 | 0.005879 / 0.005426 / 0.008443 | **0.003340 / 0.003212 / 0.004196** | 0.001120 | **0.000438** | 5.286 / **5.039** |

The paired result is unusually clean:

- CCS is better in **16/16 board-seed cells** at 1k;
- better in **16/16** at 5k;
- better in **16/16** at 20k;
- no ties and no IID wins at any checkpoint.

Mean paired relative exploitability improvement from CCS:

- ~47.2% at 1k;
- ~40.4% at 5k;
- ~42.4% at 20k.

At 20k, CCS also cuts worst-cell exploitability by roughly half (`0.008443 -> 0.004196`) and reduces dispersion substantially, without measurable hosted-run overhead; its mean runtime was slightly lower in this run.

## Accepted interpretation

The recent correlated-chance idea survives a strict DeepCash paired test and becomes the **leading chance-sampling primitive** in the current river laboratory.

The evidence supports a specific conclusion rather than a broad claim:

- low-discrepancy temporal allocation of the same exact chance distribution materially reduces sampled-regret noise here;
- the improvement is consistent across every frozen board/seed cell;
- it does not change the game distribution or payoff tree;
- it does not yet prove that correlated chance beats exact traversal, nor that the same gain persists in multi-street public/chance trees.

Exact full-tree discounted controls still dominate this tiny chance support. CCS matters because its advantage can become important once exact chance enumeration stops fitting the Ryzen budget.

Next use of CCS should be in larger-support crossover tests and, later, multi-node public/chance sampling. It should not be extrapolated blindly from one root chance node.

`R5 correlated chance sampling = ACCEPTED DEVELOPMENT EVIDENCE`

`R5 production solver = NOT SELECTED`

`READY FOR TABLES = NO`
