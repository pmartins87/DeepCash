# R5 modern algorithm candidate registry — research freeze 2026-08-16

This registry prevents DeepCash from prematurely treating `CFR+` / external-sampling / Deep CFR as the entire algorithmic search space. It is a **candidate registry**, not a promise that every paper will be implemented.

The production criterion remains DeepCash-specific: strategic error reduction per real Ryzen CPU-hour under our action/state representation, memory and reproducibility constraints.

## Already implemented controls

- synchronous full-tree CFR / CFR+ variants;
- deterministic external-sampling CFR / CFR+;
- deterministic chance-sampling CFR / CFR+;
- exact BR evaluation on tractable river games.

These establish local correctness and scaling baselines before newer methods are trusted.

## Tier A — high-priority exact/tabular candidates

### Discounted CFR (DCFR)

Primary source: Brown & Sandholm, *Solving Imperfect-Information Games via Discounted Regret Minimization*, arXiv:1809.04040.

Why it belongs in R5:

- explicitly discounts old positive/negative regrets and reweights output strategy;
- reported to outperform CFR+ across the paper's tested games;
- some variants retain compatibility with sampling/pruning, which is relevant to the Ryzen budget.

DeepCash gate:

- implement only after exact formula/parameters are pinned from the paper/code;
- first require exact checkpoint/resume and small-game convergence parity tests;
- then compare against our `CFR_PLUS_LINEAR` exact control and sampled controls.

### Hyperparameter Schedules on DCFR / PCFR+

Primary source: Zhang, McAleer & Sandholm, *Faster Game Solving via Hyperparameter Schedules*, arXiv:2404.09097.

Why it belongs:

- dynamically changes discounting hyperparameters instead of using one fixed weighting schedule;
- authors report large empirical speedups over prior DCFR/PCFR+ baselines without game-specific tuning.

DeepCash gate:

- only after a faithful DCFR/PCFR+ implementation exists;
- schedule must be frozen before held-out tests;
- no hand-tuning schedules from DeepCash validation boards.

### Predictive / discounted predictive CFR+ family (PDCFR+)

Primary source: Xu et al., *Minimizing Weighted Counterfactual Regret with Optimistic Online Mirror Descent*, arXiv:2404.13891.

Why it belongs:

- combines predictive CFR+ ideas with discounted weighting;
- directly targets faster equilibrium convergence under weighted counterfactual regret.

DeepCash gate:

- compare on exact river/turn controls only after predictor semantics are independently validated;
- preserve any instability rather than tuning it away on the development boards.

### SAPCFR+ / APCFR+

Primary source: Meng et al., *Asynchronous Predictive Counterfactual Regret Minimization+ Algorithm in Solving Extensive-Form Games*, arXiv:2503.12770.

Why it belongs:

- targets PCFR+ instability when predictions are inaccurate;
- the simplified SAPCFR+ is described as a small modification with competitive empirical behavior.

DeepCash gate:

- candidate only if PCFR+/PDCFR+ proves promising enough to justify predictive machinery;
- rank robustness across different board/range families, not best single-board speed.

### Smooth Optimistic Gradient-Based RM+ (SOGRM+)

Primary source: Meng et al., *Last-Iterate Convergence of Smooth Regret Matching+ Variants in Learning Nash Equilibria*, NeurIPS 2025.

Why it belongs:

- modern RM+ variant with last-iterate / finite-time best-iterate theory under weak MVI conditions;
- paper reports strong experimental performance against other RM+ variants.

DeepCash gate:

- lower priority than DCFR/PDCFR+ until implementation complexity and sequence-form/tree integration cost are measured.

## Tier B — structural solver candidates / accelerators

### Predictive Treeplex Blackwell+ (PTB+)

Primary source: Chakrabarti, Grand-Clément & Kroer, *Extensive-Form Game Solving via Blackwell Approachability on Treeplexes*, NeurIPS 2024.

Why it belongs:

- sequence-form/treeplex approach rather than classic local CFR only;
- stabilized predictive variant has strong theoretical convergence guarantees.

DeepCash gate:

- only worth implementing if our later public-state / street-decomposition representation maps efficiently to treeplex operations;
- compare memory traffic and sparse-update behavior on the physical Ryzen, not theory alone.

### Regret-based pruning

Primary source: Brown & Sandholm, *Regret-Based Pruning in Extensive-Form Games*, NeurIPS 2015.

Why it belongs:

- removes cold negative-regret subtrees while retaining convergence guarantees;
- potential CPU savings grow with game size and are directly relevant to a CPU-only budget.

DeepCash gate:

- pruning is an accelerator, not a strategy algorithm selection by itself;
- add only after the selected regret update has a proven compatible pruning contract.

### Block-coordinate / restart methods

Primary source: Chakrabarti, Diakonikolas & Kroer, *Block-Coordinate Methods and Restarting for Solving Extensive-Form Games*, NeurIPS 2023.

Why it belongs:

- sparse recursive updates may reduce work on large sequential games;
- restarting can substantially change practical convergence.

DeepCash gate:

- medium priority; benchmark only after our production-scale public-state layout exists, because its benefit depends heavily on tree/data locality.

## Tier C — neural / representation-scale candidates

### Deep (Predictive) Discounted CFR

Primary source: Xu et al., *Deep (Predictive) Discounted Counterfactual Regret Minimization*, arXiv:2511.08174.

Why it belongs:

- explicitly attempts to carry advanced discounted/predictive CFR behavior into function approximation instead of approximating only vanilla CFR;
- highly relevant if DeepCash ultimately requires neural regret/value approximation.

DeepCash gate:

- do **not** implement before sampled tabular traversal is trusted and R4 representation finalists exist;
- must beat simpler Deep CFR-like baselines per CPU-hour on the actual Ryzen.

### Embedding CFR

Primary source: Fu et al., *No-Regret Strategy Solving in Imperfect-Information Games via Pre-Trained Embedding*, arXiv:2511.12083.

Why it belongs:

- directly addresses information-set compression with a continuous embedding instead of only hard clustering;
- overlaps R4 representation and R5 solver design.

DeepCash gate:

- treat as a joint R4/R5 candidate only after deterministic exact/equity/blocker abstractions provide a strong held-out baseline;
- embeddings must preserve mandatory suit/card-order invariances by construction or verified metamorphic tests.

## Explicitly not promoted from theory alone

No paper receives a production slot because it has a better asymptotic bound or claims state of the art on other benchmark games. DeepCash has a constrained and unusual objective:

- one Ryzen 9;
- three-month maximum production envelope;
- 6-max NLHE with heavy representation/action abstraction;
- later local resolving and opponent exploitation;
- strong requirements for deterministic replay and auditability.

Therefore the candidate funnel is:

```text
paper/algorithm candidate
-> faithful tiny-game implementation
-> exact oracle + checkpoint determinism
-> development convergence
-> held-out board/range/geometry
-> memory + wall-clock scaling
-> target Ryzen equal-compute
-> only then production candidacy
```

## Current priority order

1. finish chance-vs-external-vs-full-tree sampling decomposition;
2. locate the range-size crossover where sampling becomes useful;
3. implement faithful DCFR as the next advanced tabular regret-update control;
4. then evaluate PDCFR+/hyperparameter schedules if DCFR/predictive machinery justifies them;
5. defer neural variants until R4 finalists and sampled traversal are stable.

`R5 production solver = NOT SELECTED`
