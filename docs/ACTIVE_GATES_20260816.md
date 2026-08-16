# DeepCash active gates — 2026-08-16

Transient audit ledger. A workflow is never promoted because it merely exists or because only part of a matrix is green. `STATUS.json` and the accepted-evidence documents remain canonical.

## R1 — exact generic engine

**Generic evidence: ACCEPTED. R1 overall: IN PROGRESS.**

Latest hard gate: legal-action oracle v3 run `31963863819` — PASS, 120 deterministic 2-to-6 handed hands, 592 live decision states and exactly one isolated pinned-PokerKit blind-epoch divergence. Target-site reopen, odd-chip, rake and optional forced-bet semantics remain unresolved release debt.

## R3 — action abstraction

### Opening-size complete lattice — ACCEPTED

Seen engineering run `31962334355` evaluated every one-, two- and three-size proper subset of `{25,50,75,100}%`. Frozen cardinality champions:

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

At SPR 2, L3's extra 25% branch has a resolved advantage over L2. L3 is therefore the leading strategic opening finalist; L2 remains the compute-efficient finalist. Full evidence: `docs/R3_OPENING_HELDOUT_V2_ACCEPTED_20260816.md`.

### Raise-size unseen evidence — ACCEPTED

`Q2_50_100` is the leading engineering raise family. Omitting 50% causes material loss at deeper SPR; adding 150% has not shown a resolved incremental gain worth its cost. Full evidence: `docs/R3_RAISE_SIZE_HELDOUT_ACCEPTED_20260816.md`.

### R3 remaining gate

R3 remains IN PROGRESS until:

- difficult exact-BR intervals are tightened where they affect the L2/L3 decision;
- the finalists receive physical Ryzen equal-wall-clock comparison;
- river evidence is converted into a street/SPR-dependent action contract rather than blindly copied to flop/turn/preflop.

Current finalists: river openings 25/50/100 vs compute-efficient 50/100; river raises 50/100.

## R4 — representation abstraction

**RUNNING / UNACCEPTED.**

Development workflow run `31964142661` remains active. Frozen candidates:

`category`, `strength4`, `equity4`, `equity8`, `category_equity4`, `equity4_blocker2`, `equity8_blocker2`.

Battery: four seen control boards, two phase pairs, 6 exact combos/player, SPR 1/2/4 and checkpoints 100/400/1200. Latest inspection: phase-A SPR1 PASS; phase-A SPR2 still running.

The deterministic selector was frozen before results and may forward at most three finalists. Independent R4 heldout-v1 remains firewalled and NOT RUN.

## R5 — solver / traversal research

### Exact synchronous baseline — ACCEPTED

`CFR_PLUS_LINEAR` led the first synchronous battery at checkpoint 1200 with mean/worst exploitability per pot about `0.000398 / 0.000455`.

### Corrected alternating exact discounted controls — ACCEPTED

Corrected player-local alternating run `31966030278` established the historical OpenSpiel-style post-update discounted `ALT_DCFR_150_0_2` as the strongest tested exact control: checkpoint-1200 mean/worst about `0.00000587 / 0.00000767`.

A semantics audit then separated that concrete algorithm from the old-regret-discount-then-add recurrence written in the 2026 Hyperparameter Schedules paper.

### Paper-equation DCFR / HS schedules — ACCEPTED NEGATIVE EVIDENCE

Run `31966914580`, artifact `9268760347`, SHA-256 `a05440224844d6515944b89428aeccae0fe64fb0c63958c737a316be03887976`.

The paper-equation DCFR and HS-DCFR(30/15) controls remained around `~0.002–0.004` exploitability/pot and were dramatically weaker on this microgame than both alternating CFR+ and the historical post-update discounted control. The negative result is preserved; no tuning was performed to force the literature-preferred method to win.

### IID chance sampling — ACCEPTED

At 20k, `CS_CFR_PLUS_LINEAR` mean/worst ~`0.005879 / 0.008443`, materially better than external sampling but still far behind exact traversal on the tiny chance support. An analytical test proves the one-step chance-sampled regret estimator is unbiased against the exact full-chance delta.

### Correlated chance sampling — ACCEPTED STRONG RESULT

Run `31966357494`, artifact `9268623901`, SHA-256 `ee2bb35f28eae23fe7f9639bd6ddc9fb47949ea78dc90450a1535f7b5f4a84d4`.

Persistent randomized golden-ratio Weyl chance allocation beat paired IID chance sampling in **16/16 frozen board-seed cells at every 1k/5k/20k checkpoint**. At 20k, mean exploitability improved from ~`0.005879` to ~`0.003340` with no observed hosted-run cost penalty. CCS is the current leading chance-sampling primitive, not a production solver.

### Alternating external LCFR — ACCEPTED MIXED RESULT

Run `31966542606`. LCFR was only marginally ahead of uniform alternating external CFR at 20k, while linear output averaging alone was clearly worse. No decisive promotion.

### Sampling crossover v1 — INVALIDATED FOR TIMING

Run `31965398733` exposed a hot-loop implementation problem before acceptance: each sampled chance draw rebuilt the full compatible-deal support. That preserved the strategic sample sequence but invalidated scaling/wall-clock conclusions.

The sampler now precomputes the exact weighted deal CDF once per `advance` batch and uses binary search. A deterministic 10,000-draw regression proves identical sampled-deal sequence and final PRNG state against the legacy selector.

### Sampling crossover v2 — RUNNING / UNACCEPTED

Run `31967392548` replays the exact v1 coordinates with only the optimized sampler hot path. Latest inspection: sampler-equivalence tests passed and the corrected scaling battery is running. Strategic outputs must match the old sequence before any new timing conclusion is accepted.

### Modern candidate funnel

`docs/R5_MODERN_ALGORITHM_CANDIDATE_REGISTRY_20260816.md` includes discounted/predictive methods, CCS, variance-reduced MCCFR baselines, pruning, treeplex/block-coordinate methods and later neural discounted/embedding variants. No paper receives production status without DeepCash exact-oracle, held-out, scaling and physical-Ryzen evidence.

## Current project state

`R0 = PASS`

`R1 = IN PROGRESS`

`R2 = PASS`

`R3 = IN PROGRESS`

`R4 = IN PROGRESS`

`R5 = IN PROGRESS`

`R6-R8 = PENDING`

`R9 = BLOCKED`

`READY FOR TABLES = NO`
