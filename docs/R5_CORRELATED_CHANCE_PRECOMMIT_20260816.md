# R5 correlated chance sampling control — precommit 2026-08-16

This generation is frozen before any correlated-chance numerical result is consumed.

Primary source: Li, Chen & Huang, *Correlated Chance Sampling for Monte Carlo Counterfactual Regret Minimization*, arXiv:2607.27035 (July 2026).

The paper changes the **temporal allocation of chance outcomes**, not the game chance law or regret estimator. Each concrete chance node receives a persistent randomized Weyl stream

`u_n = (phi + n * g) mod 1`, where `g = (sqrt(5)-1)/2` and `phi ~ Uniform[0,1)` is sampled once, then `u_n` is mapped through the chance distribution's quantile function.

DeepCash will test this idea first in the already-audited root private-deal chance sampler. Our river control has one repeatedly visited concrete chance node whose outcomes are the compatible weighted private-card deals, so the intervention can be isolated cleanly.

## Frozen candidates

1. `IID_CS_CFR_PLUS_LINEAR`
   - existing accepted chance-sampling CFR+ control;
   - independent PRNG chance draw each iteration;
   - full action tree enumerated after the sampled private deal;
   - exact own-reach linear average strategy.

2. `CCS_CFR_PLUS_LINEAR`
   - identical regret update, averaging, exact action traversal and BR evaluation;
   - only the private-deal draw changes to a persistent randomized golden-ratio Weyl stream;
   - one initial phase per seed;
   - persistent visit index stored in the checkpoint.

No other algorithmic difference is permitted in this generation.

## Correctness / determinism gates

- fixed `(phase, visit_index)` must map exactly to the documented Weyl formula;
- weighted discrete quantile mapping must reproduce chance support boundaries exactly;
- same seed -> bit-identical phase, stream, checkpoint and policy path;
- staged training == monolithic training;
- JSON roundtrip preserves phase/index and exact future path;
- wrong game/variant and non-finite corruption fail closed;
- `CCS` and IID controls must have identical terminal visits per iteration;
- only chance allocation may differ: action/regret algebra is shared with the accepted chance-sampling control.

## Frozen numerical battery

Same development game as the accepted chance-sampling generation:

- four R3 control boards;
- 6 exact combos/player;
- pot 100;
- stack 400 / SPR 4;
- 25% / 50% / 100% bet family;
- phases 0.00 / 0.27;
- seeds `11,29,101,20260816`;
- checkpoints `1000,5000,20000`;
- exact best-response evaluation.

The original IID chance-sampling numbers are included through a same-run comparator so hosted-run noise does not create a false improvement.

## Acceptance discipline

The source paper reports strong gains in several tabular poker settings but also near-vanilla endpoints in some Hold'em endgames. Therefore DeepCash assumes **no benefit** until its own paired evidence says otherwise.

Measure paired per-seed/per-board exploitability deltas, aggregate mean/median/worst/stdev, and wall-clock overhead. Do not discard unfavorable boards or seeds.

Even if CCS wins this small control, it is only a sampling primitive candidate; the production solver still requires larger-support scaling and physical Ryzen evidence.

`R5 correlated chance sampling = PRECOMMITTED`

`R5 production solver = NOT SELECTED`
