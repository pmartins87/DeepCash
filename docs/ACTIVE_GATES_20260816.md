# DeepCash active gates — 2026-08-16

Transient audit ledger. A workflow is never promoted because it merely exists or because only part of a matrix is green. `STATUS.json` and the accepted-evidence documents remain canonical.

## R1 — exact generic engine

**Generic evidence: ACCEPTED. R1 overall: IN PROGRESS.**

Latest hard generic gate: legal-action oracle v3 run `31963863819` — PASS, 120 deterministic 2-to-6 handed hands, 592 live decision states and exactly one isolated pinned-PokerKit blind-epoch divergence. DeepCash keeps its explicit cumulative-full-raise contract rather than copying that upstream corner behavior.

Target-site reopen, odd-chip, rake and optional forced-bet semantics remain unresolved release debt.

**Reference model decision — 2026-08-17:** GGPoker is the initial cash-game rules/economy reference. The engine and strategy architecture remain site-agnostic; per-site rake/caps/rounding, reopen/min-raise, odd chips, forced bets, currency/table metadata and scraper/tablemap differences belong in explicit adapters/configuration. Small differences are not permission to assume identity; they must be measured before a site is homologated.

### Universal site-rule contract — ENGINEERING_PASS

Branch: `agent/r1-site-rule-contract`.

Structural validation: CI run `31985349633` passed on `c592f144d1d11e2041626e4367a4b949423cafd3`.

The GGPoker 6-max published rake grid, preflop rake eligibility and optional
straddle feature are encoded behind a typed site adapter. Production configuration
fails closed while short-all-in reopen, odd-chip order and rake rounding/timing
remain unresolved. This checkpoint does not change R1 from IN_PROGRESS.

Evidence: `docs/R1_GGPOKER_SITE_RULE_CONTRACT_20260817.md`.

### Deterministic site-rule evidence harness — ENGINEERING_PASS

Branch: `agent/r1-evidence-fixtures`. CI run `31986987358` passed all 278 tests at `9ff89f4f192148179dab8916d433680298ab5e19`.

A strict schema and validation CLI now admit only anonymized, source-hashed and
mathematically discriminating fixtures for cumulative short-all-in reopen,
odd-chip splits and rake main/side-pot settlement. This tooling does not itself
resolve a site rule and does not change R1 from IN_PROGRESS.

Evidence: `docs/R1_GGPOKER_EVIDENCE_CAPTURE_20260817.md`.

## R3 — action abstraction

### Opening-size complete lattice — ACCEPTED

Seen engineering run `31962334355` evaluated every one-, two- and three-size proper subset of `{25,50,75,100}%`. Frozen cardinality champions from the seen set: `L1_100`, `L2_50_100`, `L3_25_50_100`.

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

R3 remains IN PROGRESS until difficult exact-BR intervals are tightened where they affect the L2/L3 decision, finalists receive physical Ryzen equal-wall-clock comparison, and river evidence is converted into a street/SPR-dependent action contract rather than copied blindly to flop/turn/preflop.

**Physical Ryzen status:** `PENDING_NOT_STARTED`. No R3 workload is currently running on the Ryzen and no physical R3 evidence has been accepted. Hosted-CI results remain engineering evidence only.

Current river finalists: openings 25/50/100 vs compute-efficient 50/100; raises 50/100.

## R4 — representation abstraction

### Development infrastructure — ACCEPTED; original selection intervals SUPERSEDED

Run `31964142661` remains accepted for deterministic bucket construction, training paths, compression, timing and invariance infrastructure. Its unrestricted-BR selection intervals remain invalidated by `docs/R4_BUCKET_BR_METHODOLOGY_CORRECTION_20260816.md`.

### Corrected bucket-constrained-BR development replay — AUDITED

Canonical v2 run `31976302604` completed successfully, including the structural oracle, all six phase/SPR replay steps and artifact upload. Artifact `9274193444` (`r4-representation-dev-v2`) has ZIP SHA-256 `b1edea689f1d7417f80b2f77d8ec8241042cde81a75eb5f632eea8af38d8fd3e`.

The archive contains six JSON files and 504 rows covering every frozen phase, SPR, board, candidate and checkpoint coordinate. The checkpoint-1200 selector consumes 24 logical board/geometry cells.

Legacy v1 run `31976111855` remains **SUPERSEDED / INELIGIBLE FOR PROMOTION**. Its successful completion does not change this boundary.

### Deterministic finalist freeze — FROZEN, ENGINEERING CI PASS

Only these candidates may enter held-out-v1:

- `equity8`;
- `equity4_blocker2`;
- `category_equity4`.

Machine-readable freeze: `deepcash_core/data/r4_representation_finalists_v1.json`. Audit: `docs/R4_REPRESENTATION_FINALIST_FREEZE_20260817.md`. Branch CI `32001037641` passed at `7b8358aa276370b330fe83d336b56d1d64e49d62`.

### Held-out firewall

`river-representation-heldout-v1.yml` is prepared with a manual `workflow_dispatch` trigger only. Status: **PREPARED_NOT_RUN**. Do not dispatch it until the freeze branch passes CI and is merged to `main`. After execution, a green workflow alone is insufficient: all six matrix cells and the combined artifact must be inspected before any promotion.

## R5 — solver / traversal research

### Exact/discounted controls — ACCEPTED

The exact small-game funnel includes synchronous CFR/CFR+, corrected alternating discounted controls and paper-equation DCFR/HS-DCFR controls. The historical post-update `ALT_DCFR_150_0_2` remains the strongest tested exact microgame control; paper-equation DCFR/HS schedules were preserved as negative evidence rather than tuned until they won.

### Chance/external sampling — ACCEPTED ENGINEERING EVIDENCE

Persistent randomized golden-ratio Weyl chance allocation beat paired IID chance sampling in all 16 frozen board-seed cells at each 1k/5k/20k checkpoint in run `31966357494`.

Sampling crossover v1 timing was invalidated after discovering that every sampled deal rebuilt the full compatible-deal support. Corrected sampling crossover v2 run `31967392548` is PASS, artifact `9269091911`, SHA-256 `a81c3675b9cd9768a30d8ff01b34cb281fc21800765c8fabef61a2d07cb6c577`. The optimized CDF sampler preserves the exact legacy sample sequence.

At 48 combos/player, the first observed hosted-CI scaling crossover appears: external sampling 80k reached about `0.00454` mean exploitability/pot in about `47.5 s`, while full-tree CFR+ 100 was about `0.00848` in about `52 s`. This is evidence that a crossover exists, not a universal threshold and not physical-Ryzen timing.

### Variance-reduced MCCFR structural gates — ACCEPTED

The baseline-enhanced estimator passed exact unbiasedness checks including off-policy controls. The legal-information exact conditional baseline v2 passed run `31975167850`; its boundary receives traverser private combo + public history/current policy and no realized opponent private hand. `INFOSET_EXACT` integration passed run `31975535179`.

VR benchmark v1 run `31975686749` was **invalidated** after inspection: privileged `PERFECT_HISTORY` evaluated counterfactual opponent branches through the stateful training traversal, contaminating regret deltas. The cause and invalidation are recorded in `docs/R5_VR_MODE_BENCHMARK_V1_INVALIDATED_20260816.md`.

The oracle was corrected so only the sampled opponent branch may mutate training state; counterfactual privileged baselines are evaluated with a pure fixed-deal policy evaluator. The regression explicitly starts from a non-terminal opponent node and proves unsampled branches cannot change regret deltas/counters.

### Corrected VR mode benchmark v2 — ACCEPTED

Run `31975899761`: PASS. Artifact `9271052796`, SHA-256 `371737a22e72e2b4e31ea3f4b09ac24ab32b58827346b3bd555137b95e99f980`.

Global 2000-iteration result over 4 boards × 5 seeds:

| mode | mean exploitability/pot | sample stdev | mean train s | time vs ZERO |
|---|---:|---:|---:|---:|
| ZERO | 0.03427096 | 0.00477694 | 0.62274 | 1.00x |
| INFOSET_EXACT | 0.03311817 | 0.00359434 | 2.93230 | 4.71x |
| PERFECT_HISTORY | **0.02969950** | 0.00441312 | 0.95958 | 1.54x |

Legal `INFOSET_EXACT` improves mean exploitability by about 3.36% but at ~4.71x hosted-CI training time. Privileged `PERFECT_HISTORY` improves it by about 13.34% and remains permanently production-ineligible. This shows meaningful reducible opponent-action variance exists, but exact hidden-support integration is too expensive for its observed gain. Full interpretation: `docs/R5_VR_MODE_BENCHMARK_V2_ACCEPTED_20260816.md`.

### Cheap no-leak tabular baseline — STRUCTURAL AND NUMERIC EVIDENCE ACCEPTED

`deepcash_core/river_vr_tabular.py` implements `TABULAR_RUNNING`: running action-value baselines keyed only by traverser private combo + public opponent node + action. The baseline is frozen before the current sample is corrected and updated only afterward.

Dedicated oracle run `31976450221`: **PASS**. It proves first-iteration identity with ZERO, same-seed determinism, staged=monolithic training, JSON checkpoint exact future-path equivalence, and no realized-opponent-hand component in baseline identity.

The comparison was frozen before execution in `docs/R5_TABULAR_VR_BENCHMARK_PLAN_20260816.md`. Numerical run `31976572985`: **PASS**. Artifact `9271293501`, ZIP SHA-256 `83e04bf241f59d645d7be68c9f781042f4dfe85a970b4f5d17ab5c6b7c6d67d6`. The archive, schema/configuration, 180 raw rows and reported aggregates were independently re-audited on 2026-08-17.

At 10k iterations over four boards × five seeds:

| mode | mean exploitability/pot | sample stdev | mean train s | time vs ZERO |
|---|---:|---:|---:|---:|
| ZERO | 0.01619797 | 0.00188020 | 3.41965 | 1.000x |
| TABULAR_RUNNING | **0.01577459** | **0.00098999** | 3.84933 | 1.126x |
| INFOSET_EXACT | 0.01500396 | 0.00101858 | 14.25467 | 4.168x |

`TABULAR_RUNNING` lowers mean exploitability by about 2.61% versus ZERO and wins 11/20 paired cells; its cross-seed dispersion is about 47% lower at low overhead. It is accepted as the leading cheap legal external-sampling VR primitive currently tested, **not** as a production solver winner.

Full interpretation: `docs/R5_TABULAR_VR_BENCHMARK_V1_ACCEPTED_20260816.md`.

### Equal-wall-clock/scaling comparison — PRECOMMIT PREPARED, NOT RUN

The next gate is frozen in `docs/R5_EQUAL_WALLCLOCK_SCALING_PRECOMMIT_20260817.md`. It compares only already-accepted implementations as separate, semantically honest comparators: optimized external CFR+ with ZERO, optimized external CFR+ with TABULAR_RUNNING, correlated chance CFR+ and INFOSET_EXACT as an expensive legal reference.

No hybrid CCS+external/tabular algorithm is claimed: correlated chance samples only the private-deal chance node while traversing the complete action tree; TABULAR_RUNNING corrects sampled opponent actions inside external sampling. Integration would require its own structural/unbiasedness gate before numerical consumption.

Execution remains **NOT RUN** while the two R4 development workflows consume hosted CI. Hosted timing will remain engineering evidence; physical Ryzen equal-wall-clock comparison remains mandatory.

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
