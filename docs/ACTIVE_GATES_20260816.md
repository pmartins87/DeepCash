# DeepCash active gates — 2026-08-16

Transient audit ledger. A workflow is never promoted merely because it exists or because a partial matrix is green. Accepted evidence is recorded only after completion and inspection.

## R1 — generic exact-engine oracle — ACCEPTED; target-site debt remains

Legal-action oracle v3 run `31963863819`: **PASS** — 120 deterministic 2-to-6 handed hands, 592 live decision states and exactly one structurally documented pinned-PokerKit blind-epoch reopen divergence. DeepCash intentionally keeps cumulative-full-raise semantics rather than copying that upstream behavior.

R1 remains IN PROGRESS only because target-site reopen, odd-chip, rake and optional forced-bet semantics are not yet frozen from evidence.

## R3 — opening-size lattice seen selection — ACCEPTED; unseen-v2 RUNNING

Seen engineering workflow run `31962334355` evaluated all 14 non-empty proper subsets of `{25,50,75,100}%` across the four precommitted seen cells and selected, before unseen-v2 consumption:

| complexity | frozen champion | worst upper/pot | mean upper/pot |
|---:|---|---:|---:|
| 1 | `L1_100` | 0.00881885 | 0.00269107 |
| 2 | `L2_50_100` | 0.00342888 | 0.00153998 |
| 3 | `L3_25_50_100` | 0.00316745 | 0.00132747 |

Selector artifact `9268277521`, SHA-256 `f17838f1196564e4e30a9b622d85bd0157ce1d17b92af1cff349bb2f1427897a`.

The original `25/50/100` three-size hypothesis survived the complete proper-subset search. This is not a complexity freeze because 2-size vs 3-size differences remain close to exact-BR resolution.

Unseen-v2 uses only those three frozen champions on six new boards, 8 combos/player, phases 0.31/0.79 and SPR 1/2/4. Latest inspection:

- SPR 1: PASS numerical cell;
- SPR 4: PASS numerical cell;
- SPR 2: still running;
- final summary: blocked until all three cells finish.

No unseen-v2 result may retroactively change the candidates forwarded by the selector.

Full seen-selection evidence: `docs/R3_OPENING_LATTICE_SELECTION_ACCEPTED_20260816.md`.

## R3 — independent raise-size held-out — ACCEPTED AS ENGINEERING EVIDENCE

Across SPR 1/2/4, the unseen raise-size battery established `Q2_50_100` as the leading engineering candidate. At deeper geometries, removing 50% produces material resolved loss; adding 150% on top of 50%+100% has not shown a resolved gain worth its extra cost.

Fail-closed postprocessor run `31964700344`: PASS. Full evidence: `docs/R3_RAISE_SIZE_HELDOUT_ACCEPTED_20260816.md`.

R3 still requires opening unseen-v2 completion, any necessary exact-BR tightening and physical Ryzen equal-compute evidence before action-family freeze.

## R4 — deterministic representation development — RUNNING / UNACCEPTED

Workflow run `31964142661` remains active. Frozen development candidates:

`category`, `strength4`, `equity4`, `equity8`, `category_equity4`, `equity4_blocker2`, `equity8_blocker2`.

Battery: four seen control boards, phase pairs 0.00/0.27 and 0.11/0.54, 6 exact combos/player, SPR 1/2/4, checkpoints 100/400/1200. Latest inspection remains phase A SPR1 PASS, phase A SPR2 running.

The deterministic selector was frozen before numerical inspection. R4 held-out-v1 remains firewalled and NOT RUN.

## R5 — exact solver controls

### Synchronous full-tree controls — ACCEPTED

Run `31964902076`: PASS. Among the first synchronous controls, `CFR_PLUS_LINEAR` led at checkpoint 1200 with mean/worst exploitability per pot `0.000398 / 0.000455` at ~2.97 hosted seconds.

This remains a valid synchronous baseline but is no longer the strongest exact control.

### Corrected alternating CFR+ / DCFR v2 — ACCEPTED

A literature/source audit invalidated v1 **before any result consumption** because v1 averaged both players only after both regret half-updates. v2 corrects this to player-local alternating semantics: P0 average/regret/update, profile refresh, then P1 average/regret/update.

Corrected CI run `31966030259`: PASS.

Corrected benchmark run `31966030278`: PASS. Artifact `9268529202`, SHA-256 `5c000f61a9d14722f927851942e6b44b8311f5d7f2d575c5fd1e5b761a97643b`.

Checkpoint-1200 mean/worst exploitability per pot:

| algorithm | mean | worst | mean hosted train s |
|---|---:|---:|---:|
| synchronous CFR+ linear | 0.00039815 | 0.00045542 | 2.845 |
| alternating CFR+ linear | 0.00000946 | 0.00002445 | 5.762 |
| alternating CFR+ quadratic | 0.00001077 | 0.00002870 | 5.774 |
| **DCFR 1.5/0/2** | **0.00000587** | **0.00000767** | 5.784 |
| DCFR 1.5/0.5/2 | 0.00001071 | 0.00002722 | 5.769 |

`ALT_DCFR_150_0_2` is now the leading exact tabular development control. At checkpoint 400 it is already about 28.6x more converged than synchronous CFR+ at checkpoint 1200 while using less hosted wall-clock in this exact microgame.

Full evidence: `docs/R5_ALTERNATING_DCFR_DEV_V2_ACCEPTED_20260816.md`.

## R5 — sampled traversal decomposition

### External sampling — ACCEPTED negative tiny-tree result

Run `31965167770`: PASS. At 20k, `ES_CFR_PLUS_LINEAR` mean/worst exploitability per pot is ~`0.009886 / 0.012771`. It is far worse than exact traversal on the 6x6 chance support, so sampling is not automatically beneficial at small scale.

Full evidence: `docs/R5_EXTERNAL_SAMPLING_DEV_ACCEPTED_20260816.md`.

### IID chance sampling — ACCEPTED

Run `31965523599`: PASS. At 20k, `CS_CFR_PLUS_LINEAR` mean/worst is ~`0.005879 / 0.008443`, materially better than external sampling at modestly higher per-iteration cost. This isolates opponent-action sampling as an important additional variance source in this river control.

An analytical unit oracle also proves the one-step chance-sampled regret estimator is unbiased relative to the exact full-chance regret update on the frozen fixture.

Full evidence: `docs/R5_CHANCE_SAMPLING_DEV_ACCEPTED_20260816.md`.

### Range-support crossover — RUNNING / UNACCEPTED

Run `31965398733` is still running. It compares full-tree CFR+ against external-sampling CFR+ as exact private range support expands through 6/12/24/48 combos per player on two boards. Interpretation must use wall-clock/deal support rather than pretending iteration counts are equal work.

### Correlated chance sampling — RUNNING / UNACCEPTED

Recent CCS-MCCFR work motivated a new paired control in which only the temporal allocation of chance outcomes changes: IID private-deal sampling versus a persistent randomized golden-ratio Weyl stream. The precommit explicitly assumes no gain until DeepCash evidence proves one.

Correctness implementation/tests are in `deepcash_core/river_correlated_chance_sampling.py` and `tests/test_river_correlated_chance_sampling.py`.

Numerical run `31966357494` is running on the same four boards, four frozen seeds and 1k/5k/20k checkpoints.

## R5 — modern algorithm funnel

`docs/R5_MODERN_ALGORITHM_CANDIDATE_REGISTRY_20260816.md` now prevents the project from stopping at vanilla CFR/CFR+/Deep CFR. The research funnel includes DCFR, predictive/discounted variants, hyperparameter schedules, pruning/treeplex/block-coordinate methods and later neural discounted/embedding candidates. Every candidate must pass tiny-game correctness, held-out evidence, scaling and target-Ryzen equal-compute before production candidacy.

The next advanced sampled-control question is whether discounted/variance-reduced sampling can inherit some of the enormous exact-DCFR convergence gain without paying full-tree cost.

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
