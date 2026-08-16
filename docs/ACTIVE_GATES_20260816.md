# DeepCash active gates — 2026-08-16

Transient audit ledger. A workflow is never promoted merely because it exists or because a partial matrix is green. Accepted evidence is recorded only after completion and inspection.

## R1 — bidirectional legal-action oracle v3 — ACCEPTED

Accepted generic-rules evidence:

- workflow `r1-legal-actions-oracle-v3.yml`;
- run `31963863819` on commit `5e6c46349980b9a6e861b69736a3d7c49bb7f686`;
- 120 deterministic 2-to-6 handed hands;
- 592 live decision states checked bidirectionally;
- exactly one structurally documented pinned-PokerKit blind-epoch reopen divergence;
- every other actor/call/fold/check/raise/boundary mismatch remains fatal;
- exact completed-hand stack parity retained.

DeepCash intentionally keeps cumulative-full-raise semantics instead of copying the upstream PokerKit blind-epoch behavior. Target-site reopen evidence is still unresolved, so `R1 = IN PROGRESS`.

## R3 — opening-size lattice engineering selection — ACCEPTED; unseen v2 RUNNING

Workflow run `31962334355`, source commit `723096d01cea3a2bd39869734329f81ecd480aad`.

Every one-, two- and three-size proper subset of `{25,50,75,100}%` was evaluated on the four precommitted seen engineering cells. All four lattice jobs passed. The frozen selector then completed successfully and forwarded exactly one champion per cardinality:

| complexity | champion | worst upper/pot | mean upper/pot | worst interval/pot |
|---:|---|---:|---:|---:|
| 1 | `L1_100` | 0.00881885 | 0.00269107 | 0.00273509 |
| 2 | `L2_50_100` | 0.00342888 | 0.00153998 | 0.00285407 |
| 3 | `L3_25_50_100` | 0.00316745 | 0.00132747 | 0.00273929 |

Selector artifact `9268277521`, SHA-256 `f17838f1196564e4e30a9b622d85bd0157ce1d17b92af1cff349bb2f1427897a`.

The old `O3_25_50_100` hypothesis therefore survived the complete four-size proper-subset search as the winning three-size engineering subset. This is not a complexity freeze: 2-size vs 3-size differences remain close to exact-BR resolution on seen evidence.

Only after selection did the precommitted unseen-v2 generation launch. Current held-out-v2 jobs are running at SPR 1/2/4, using only `L1_100,L2_50_100,L3_25_50_100`, six new boards, 8 combos/player, phases 0.31/0.79 and checkpoints 300/1200/3600.

Full seen-data selection evidence: `docs/R3_OPENING_LATTICE_SELECTION_ACCEPTED_20260816.md`.

## R3 — independent raise-size held-out — ACCEPTED AS ENGINEERING EVIDENCE

Source run `31962687271` completed all three numerical cells successfully. A historical missing summarizer caused only the final postprocessing job to fail; the expensive cells were not rerun. Fail-closed postprocessor run `31964700344` downloaded the immutable artifacts and passed. General CI `31964700348` also passed.

Accepted cross-SPR descriptive results at checkpoint 3600:

| Candidate | mean upper | worst upper | max resolved worst excess | cumulative CI seconds | descriptive Pareto |
|---|---:|---:|---:|---:|---|
| Q1_100 | 0.00187922 | 0.01109559 | 0.00799696 | 1505.48 | yes |
| Q2_50_100 | 0.00081742 | 0.00240061 | 0.00001414 | 1599.41 | yes |
| Q2_100_150 | 0.00189127 | 0.01123168 | 0.00763065 | 1568.38 | no |
| Q3_50_100_150 | 0.00082204 | 0.00254006 | 0.00000000 | 1662.45 | no |

At SPR 2/4, omitting the 50% raise produces material resolved loss. `Q2_50_100` remains essentially resolution-limited while cheaper than the full Q3 family, so it is the leading raise-size engineering candidate, not a production freeze.

Full evidence: `docs/R3_RAISE_SIZE_HELDOUT_ACCEPTED_20260816.md`.

## R4 — deterministic representation development — RUNNING / UNACCEPTED

Workflow run `31964142661` is active.

Frozen battery:

- four already-seen development control boards;
- candidates `category`, `strength4`, `equity4`, `equity8`, `category_equity4`, `equity4_blocker2`, `equity8_blocker2`;
- phase pairs 0.00/0.27 and 0.11/0.54;
- 6 exact combos/player;
- SPR 1/2/4;
- checkpoints 100/400/1200;
- single sequential job.

Latest inspection:

- phase A / SPR 1: PASS;
- phase A / SPR 2: running;
- remaining cells pending.

The development selection rule was frozen before numerical inspection and may carry at most three deterministic finalists. The independent R4 heldout-v1 generation remains firewalled and NOT RUN.

R4 correctness machinery already has passing regressions for exact-control equivalence, one-sided candidate-vs-exact restriction, deterministic checkpoint/resume, hole-card-order invariance and all 24 global suit permutations.

## R5 — exact tabular control — ACCEPTED; external sampling RUNNING

R5 is now **IN PROGRESS**.

### Exact synchronous control

Precommit: `docs/R5_TABULAR_SOLVER_PRECOMMIT_20260816.md`.

Correctness CI run `31964902028`: **PASS**.

Benchmark run `31964902076`: **PASS**. Artifact `9268225276`, SHA-256 `53fca369a4856faafbd1a7427335a1bda0399e21c8d4835c99cb4a36598110e0`.

At checkpoint 1200 across four exact river control boards:

| variant | mean exploitability/pot | worst exploitability/pot | mean cumulative CI training s |
|---|---:|---:|---:|
| CFR uniform | 0.002648 | 0.003149 | 2.958 |
| CFR linear | 0.006388 | 0.009714 | 2.956 |
| CFR+ uniform | 0.001430 | 0.001809 | 2.986 |
| CFR+ linear | **0.000398** | **0.000455** | 2.974 |

`CFR_PLUS_LINEAR` is accepted as the leading exact tabular control. It is not the production solver because synchronous full-tree traversal does not scale to 6-max.

Full evidence: `docs/R5_TABULAR_SOLVER_DEV_ACCEPTED_20260816.md`.

### Deterministic external-sampling MCCFR

Precommit: `docs/R5_EXTERNAL_SAMPLING_PRECOMMIT_20260816.md`.

Implemented/gated:

- `ES_CFR_LINEAR` and `ES_CFR_PLUS_LINEAR`;
- chance and non-traverser action sampling;
- traverser action enumeration;
- common pre-update strategy snapshot for both traversers;
- exact own-reach average strategy in this first small-game control;
- deterministic PRNG state in checkpoints;
- same-seed identity, staged-vs-monolithic identity, JSON future-path identity, wrong-variant and non-finite fail-closed tests.

General CI run `31965167839`: **PASS**.

Numerical workflow run `31965167770` is **IN PROGRESS** on the four control boards, two variants, four frozen seeds and checkpoints 1000/5000/20000. Results remain unaccepted until completion and inspection.

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
