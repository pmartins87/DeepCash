# DeepCash active gates — 2026-08-16

Transient audit ledger. A workflow is never promoted because it merely exists or because only part of a matrix is green. `STATUS.json` and the accepted-evidence documents remain canonical.

## R1 — exact generic engine

**Generic evidence: ACCEPTED. R1 overall: IN PROGRESS.**

Latest hard generic gate: legal-action oracle v3 run `31963863819` — PASS, 120 deterministic 2-to-6 handed hands, 592 live decision states and exactly one isolated pinned-PokerKit blind-epoch divergence. DeepCash keeps its explicit cumulative-full-raise contract rather than copying that upstream corner behavior.

Target-site reopen, odd-chip, rake and optional forced-bet semantics remain unresolved release debt.

## R3 — action abstraction

### Opening-size complete lattice — ACCEPTED

Seen engineering run `31962334355` evaluated every one-, two- and three-size proper subset of `{25,50,75,100}%`. Frozen cardinality champions from the seen set:

- `L1_100`;
- `L2_50_100`;
- `L3_25_50_100`.

Selector artifact `9268277521`, SHA-256 `f17838f1196564e4e30a9b622d85bd0157ce1d17b92af1cff349bb2f1427897a`.

### Opening-size unseen-v2 — ACCEPTED

The independently precommitted six-board / 8-combo / SPR 1-2-4 unseen generation completed fully. Summary artifact `9268566954`, SHA-256 `158eef1f2d9d9adfff1254af14d694464a0e8ff85a6716cd3ea27c75291de641`.

Cross-SPR checkpoint-3600 mean/worst upper loss per pot:

| candidate | mean | worst |
|---|---:|---:|
| L1_100 | 0.00589680 | 0.01368868 |
| L2_50_100 | 0.00114458 | 0.00267837 |
| **L3_25_50_100** | **0.00097338** | **0.00168981** |

At SPR 2, L3's extra 25% branch has a resolved advantage over L2. L3 is the leading strategic river-opening finalist; L2 remains the lower-compute finalist. Full evidence: `docs/R3_OPENING_HELDOUT_V2_ACCEPTED_20260816.md`.

### Raise-size unseen evidence — ACCEPTED

`Q2_50_100` is the leading engineering river-raise family. Omitting 50% causes material deeper-SPR loss; adding 150% has not shown a resolved incremental gain worth its cost. Full evidence: `docs/R3_RAISE_SIZE_HELDOUT_ACCEPTED_20260816.md`.

### R3 remaining gate

R3 remains IN PROGRESS until:

- difficult exact-BR intervals are tightened where they affect the L2/L3 decision;
- finalists receive physical Ryzen equal-wall-clock comparison;
- river evidence is converted into a street/SPR-dependent action contract rather than copied blindly to flop/turn/preflop.

Current river finalists: openings 25/50/100 vs compute-efficient 50/100; raises 50/100.

## R4 — representation abstraction

### Deterministic development battery — ACCEPTED

Run `31964142661`: PASS. Artifact `9270794930`, SHA-256 `2fcf9bac459126f6d2638421c5b06da5441ae14682ef0d999e80dba15473eb70`.

All six frozen development cells completed: two range-phase pairs × nominal SPR 1/2/4 over the four seen control boards, 6 exact combos/player and checkpoints 100/400/1200.

At checkpoint 1200, aggregate strategic-loss upper bounds show a strong separation between eight-equity-bucket controls and the compressed four-bucket/category controls, but the latter still have wide exact-BR intervals. Key aggregate values are recorded in `docs/R4_DEV_RESULTS_20260816.md`.

The all-24 global suit-permutation metamorphic test for every current deterministic representation is in the green general suite. Latest broad CI after the no-leak integration changes: run `31975686755`, PASS.

No deterministic finalist has been frozen yet because solver uncertainty is concentrated in a few difficult development cells.

### Targeted convergence extension — RUNNING / UNACCEPTED

Plan frozen before execution in `docs/R4_TARGETED_CONVERGENCE_PLAN_20260816.md`. Run `31975623597` extends only the difficult seen cells from 1200 to 3600 iterations at one representative un-clipped geometry. It does not touch R4 held-out v1.

R4 held-out v1 remains unopened. It may start only after targeted convergence is inspected and at most three development finalists are explicitly recorded.

## R5 — solver / traversal research

### Exact/discounted controls — ACCEPTED

The exact small-game funnel includes synchronous CFR/CFR+, corrected alternating discounted controls and paper-equation DCFR/HS-DCFR controls. The historical post-update `ALT_DCFR_150_0_2` remains the strongest tested exact microgame control; paper-equation DCFR/HS schedules were preserved as negative evidence rather than tuned until they won.

### Chance/external sampling — ACCEPTED ENGINEERING EVIDENCE

IID chance sampling is unbiased but noisy on small support. Persistent randomized golden-ratio Weyl chance allocation beat paired IID chance sampling in all 16 frozen board-seed cells at each 1k/5k/20k checkpoint in run `31966357494`.

Sampling crossover v1 timing was invalidated after discovering that every sampled deal rebuilt the full compatible-deal support.

Sampling crossover v2 run `31967392548`: PASS, artifact `9269091911`, SHA-256 `a81c3675b9cd9768a30d8ff01b34cb281fc21800765c8fabef61a2d07cb6c577`. A 10,000-draw regression proves the optimized precomputed-CDF sampler preserves the exact legacy sampled-deal sequence and final PRNG state. Strategic outputs match v1 while timing improves sharply.

At 48 combos/player, the first observed scaling crossover appears: external sampling 80k reached about `0.00454` mean exploitability/pot in about `47.5 s`, while full-tree CFR+ 100 was about `0.00848` in about `52 s` on hosted CI. This is evidence that a crossover exists, **not** a universal 48-combo threshold and not Ryzen timing evidence.

### Variance-reduced MCCFR algebra/oracles — ACCEPTED

The baseline-enhanced estimator passed exact unbiasedness checks, including off-policy controls. `PERFECT_HISTORY` is deliberately privileged and exists only as a zero/low-variance lower-bound oracle; it is never production eligible.

The legal-information exact conditional baseline v2 passed dedicated oracle run `31975167850`. Its API receives only the traverser's private combo, public node/history and current policy; no realized opponent private hand is accepted.

`INFOSET_EXACT` was then integrated into external sampling alongside `ZERO` and `PERFECT_HISTORY`. Two first-pass tests incorrectly assumed RNG-state/terminal-visit equality **across different adaptive solver modes**; those assumptions were removed, not the solver checks. The corrected dedicated integration run `31975535179` is PASS. It proves:

- `ZERO` remains the ordinary external-sampling identity control;
- `INFOSET_EXACT` is deterministic under same seed and checkpoint partitioning;
- it is a real control variate rather than a ZERO alias;
- its baseline boundary has no realized-opponent-hand input.

General CI containing the corrected integration is also green (`31975686755`).

### Legal VR mode performance battery — RUNNING / UNACCEPTED

The numerical plan was frozen in `docs/R5_VR_MODE_BENCHMARK_PLAN_20260816.md` before execution. Run `31975686749` compares `ZERO`, legal `INFOSET_EXACT`, and privileged `PERFECT_HISTORY` over four development boards × five seeds at 2000 iterations. The goal is to quantify variance reduction versus CPU cost and determine whether a cheap learned/tabular legal baseline is worth building.

No result from this workflow is accepted until the run completes and its artifact is inspected.

### Modern candidate funnel

`docs/R5_MODERN_ALGORITHM_CANDIDATE_REGISTRY_20260816.md` includes discounted/predictive methods, correlated chance sampling, variance-reduced MCCFR, pruning, treeplex/block-coordinate methods and later neural discounted/embedding variants. No literature result receives production status without DeepCash exact-oracle, held-out, scaling and physical-Ryzen evidence.

## Current project state

`R0 = PASS`

`R1 = IN PROGRESS`

`R2 = PASS`

`R3 = IN PROGRESS`

`R4 = IN PROGRESS`

`R5 = IN PROGRESS`

`R6-R8 = PENDING`

`R9 = BLOCKED`

`R10-R15 = PENDING`

`READY FOR TABLES = NO`
