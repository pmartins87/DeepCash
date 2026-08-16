# R5 modern algorithm candidate registry — 2026-08-16

This registry prevents DeepCash from prematurely treating one CFR family as the entire production search space. It is a candidate funnel, not a promise that every paper will be implemented.

Production criterion: **strategic error reduction per real Ryzen CPU-hour**, subject to memory, determinism, checkpoint/replay and later R4 representation constraints.

## Already implemented / active controls

- synchronous full-tree CFR / CFR+;
- corrected alternating CFR+;
- OpenSpiel-style post-update discounted CFR control;
- paper-equation DCFR + HS-DCFR generation (running);
- deterministic external sampling;
- deterministic chance sampling;
- correlated chance sampling (accepted, strong paired result);
- alternating external-sampling CFR / LCFR (accepted, mixed result);
- exact BR evaluation on tractable river games.

Important semantics audit: `docs/R5_DCFR_SEMANTICS_AUDIT_20260816.md` records that the accepted historical discounted control and the explicit 2026 paper recurrence use different regret-discount ordering. Both are kept as named algorithms rather than conflated under one `DCFR` label.

## Tier A — highest-priority near-term candidates

### Paper-equation DCFR + Hyperparameter Schedules

Primary source: Zhang, McAleer & Sandholm, *Faster Game Solving via Hyperparameter Schedules*, AAAI 2026 / arXiv:2404.09097v2.

Status:

- exact recurrence and HS schedules frozen in `docs/R5_HS_DCFR_PRECOMMIT_20260816.md`;
- `PAPER_DCFR_150_0_2`, `HS_DCFR_30` and `HS_DCFR_15` implemented;
- exact development workflow running.

Why high priority:

- directly attacks convergence without adding game abstraction or neural approximation;
- schedules change alpha/beta/gamma over the frozen solve horizon;
- especially attractive if it improves the already strong alternating exact controls at negligible per-iteration complexity cost.

### Correlated Chance Sampling (CCS-MCCFR)

Primary source: Li, Chen & Huang, *Correlated Chance Sampling for Monte Carlo Counterfactual Regret Minimization*, arXiv:2607.27035.

Status: **accepted development evidence** — see `docs/R5_CORRELATED_CHANCE_DEV_ACCEPTED_20260816.md`.

DeepCash paired result:

- same exact chance law, regret algebra and action traversal;
- IID vs persistent randomized golden-ratio Weyl allocation only;
- CCS won all 16/16 frozen board-seed cells at every 1k/5k/20k checkpoint;
- about 42% mean exploitability improvement at 20k with no observed runtime penalty in the hosted run.

Next gate:

- larger exact chance supports and later multiple public/chance nodes;
- do not extrapolate one-root river evidence blindly to the full game.

### Variance-Reduced MCCFR with baselines (VR-MCCFR)

Primary source: Schmid et al., *Variance Reduction in Monte Carlo Counterfactual Regret Minimization (VR-MCCFR) for Extensive Form Games using Baselines*, arXiv:1809.03057.

Why high priority:

- directly targets the variance that DeepCash already measured as the main weakness of sampled traversal;
- baseline-enhanced estimates remain unbiased under the paper's construction;
- recursive bootstrapping can propagate variance reduction up sampled trajectories;
- source experiments report very large convergence gains and show CFR+ becoming useful with sampling once variance is reduced.

DeepCash gate:

1. implement an exact small-game oracle baseline first, where expected variance reduction can be measured directly;
2. prove the baseline-enhanced regret estimator remains unbiased against full-tree exact deltas;
3. then add an online learned/tabular baseline;
4. compare IID vs CCS chance allocation inside the same VR estimator only after each component is independently validated.

### Discounted / predictive CFR family

Primary sources:

- Brown & Sandholm, *Solving Imperfect-Information Games via Discounted Regret Minimization*, arXiv:1809.04040;
- Xu et al., *Minimizing Weighted Counterfactual Regret with Optimistic Online Mirror Descent*, arXiv:2404.13891.

Candidates:

- faithful paper-equation DCFR;
- PDCFR+ / predictive discounted variants.

Gate:

- exact predictor semantics and checkpoint determinism first;
- no tuning from validation boards;
- retain instability/failure rather than selecting favorable boards.

## Tier B — structural accelerators

### Regret-based pruning

Primary source: Brown & Sandholm, *Regret-Based Pruning in Extensive-Form Games*, NeurIPS 2015.

Potential value: skip cold negative-regret subtrees while retaining a compatible convergence contract. Relevant because CPU savings may grow with game size.

Gate: add only after the selected regret update has a proved compatible pruning rule.

### Predictive Treeplex Blackwell+ (PTB+)

Primary source: Chakrabarti, Grand-Clément & Kroer, *Extensive-Form Game Solving via Blackwell Approachability on Treeplexes*, NeurIPS 2024.

Potential value: sequence-form/treeplex updates may fit later public-state decomposition better than classic local CFR.

Gate: only after R6/R7 public-state layout exists; benchmark sparse memory traffic on Ryzen.

### Block-coordinate / restart methods

Primary source: Chakrabarti, Diakonikolas & Kroer, *Block-Coordinate Methods and Restarting for Solving Extensive-Form Games*, NeurIPS 2023.

Potential value: sparse recursive updates and restart schedules on very large games.

Gate: medium priority until production-scale tree/data locality exists.

### Smooth / optimistic RM+ variants

Candidate families include SOGRM+, SAPCFR+/APCFR+ and related optimistic regret methods.

Gate: only after discounted/predictive CFR controls justify the added machinery and exact tiny-game implementations reproduce the intended algorithms.

## Tier C — neural / representation-scale candidates

### Deep (Predictive) Discounted CFR

Candidate only after sampled traversal is trustworthy and R4 representation finalists exist. Must beat simpler tabular/sampled and Deep-CFR-style baselines per actual Ryzen CPU-hour.

### Embedding CFR / learned information-state embeddings

Joint R4/R5 candidate. Learned embeddings may enter only after deterministic exact/equity/blocker abstractions provide a strong held-out baseline and mandatory suit/card-order invariances are preserved.

## Explicitly not promoted from theory alone

No algorithm receives a production slot because it has a better theorem, a stronger paper benchmark, or a poker pedigree. DeepCash has a specific constrained objective:

- one Ryzen 9;
- approximately three months maximum production envelope;
- 6-max NLHE with heavy measured action/state abstraction;
- later local resolving and opponent exploitation;
- deterministic auditability/checkpoint recovery.

Candidate funnel:

```text
paper/algorithm
-> faithful tiny-game implementation
-> exact estimator/update oracle
-> deterministic checkpoint/resume
-> development convergence
-> held-out board/range/geometry
-> scaling/memory/wall-clock
-> physical Ryzen equal-compute
-> production candidacy
```

## Current priority order

1. finish paper-equation DCFR / HS-DCFR exact control;
2. finish the running range-support crossover;
3. extend the accepted CCS primitive to larger chance support;
4. implement VR-MCCFR baseline oracles as the next major sampled-variance candidate;
5. evaluate predictive/optimistic discounted methods only after the DCFR semantics hierarchy is stable;
6. defer neural variants until R4 finalists and sampled traversal are stable.

`R5 production solver = NOT SELECTED`
