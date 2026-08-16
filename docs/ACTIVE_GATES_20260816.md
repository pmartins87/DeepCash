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

## R3 — opening-size subset lattice -> unseen v2 — RUNNING / UNACCEPTED

Run `31962334355`.

The engineering lattice evaluates every one-, two- and three-size proper subset of the fixed `{25,50,75,100}%` opening reference. A frozen selector may forward exactly one champion at each cardinality, using worst conservative restriction-loss upper bound, then mean upper bound, training time and lexical tie-break.

Latest inspection:

- control SPR 1: PASS;
- control SPR 4: PASS;
- seen heldout-v1 SPR 1: numerical analysis completed and artifact upload in progress/completing;
- seen heldout-v1 SPR 4: still running.

The true unseen-v2 generation was precommitted before lattice results are accepted: six new boards, 8 combos/player, phases 0.31/0.79, SPR 1/2/4, checkpoints 300/1200/3600. Only the three preselected cardinality champions may enter it.

No opening family is accepted until the complete lattice -> selector -> unseen-v2 chain finishes and is inspected.

## R3 — independent raise-size held-out — ACCEPTED AS ENGINEERING EVIDENCE

Source run `31962687271` completed all three numerical cells successfully:

- SPR 1 artifact `9267994573`;
- SPR 2 artifact `9268089087`;
- SPR 4 artifact `9268068340`.

The source workflow's final summary job failed only because `tools/summarize_raise_size_heldout.py` did not exist at that historical commit. The numerical cells were not rerun. A fail-closed summarizer and tests were added, and dedicated postprocessor run `31964700344` downloaded the immutable source artifacts and passed. Summary artifact: `9268162754`, SHA-256 `a77790aefe7e255f0d4ec7a76cbdb2c8d7331432ab664583036888695734f9b5`. General CI `31964700348` also passed.

Accepted cross-SPR descriptive results at checkpoint 3600:

| Candidate | mean upper | worst upper | max resolved worst excess | cumulative CI seconds | descriptive Pareto |
|---|---:|---:|---:|---:|---|
| Q1_100 | 0.00187922 | 0.01109559 | 0.00799696 | 1505.48 | yes |
| Q2_50_100 | 0.00081742 | 0.00240061 | 0.00001414 | 1599.41 | yes |
| Q2_100_150 | 0.00189127 | 0.01123168 | 0.00763065 | 1568.38 | no |
| Q3_50_100_150 | 0.00082204 | 0.00254006 | 0.00000000 | 1662.45 | no |

Interpretation:

- SPR 1 clips all four nominal candidates to the same physical action tree;
- at SPR 2/4, omitting the 50% raise produces material resolved loss;
- 50%+100% remains essentially resolution-limited while being cheaper than 50%+100%+150%;
- `Q2_50_100` is therefore the leading **raise-size engineering candidate**, not a production freeze.

Full inspected evidence: `docs/R3_RAISE_SIZE_HELDOUT_ACCEPTED_20260816.md`.

R3 still requires opening unseen-v2, any necessary exact-BR tightening and physical Ryzen equal-compute evidence.

## R4 — deterministic representation development — RUNNING / UNACCEPTED

Workflow run `31964142661` is active.

Frozen development battery:

- boards: four already-seen control boards only;
- candidates: `category`, `strength4`, `equity4`, `equity8`, `category_equity4`, `equity4_blocker2`, `equity8_blocker2`;
- phase pairs: 0.00/0.27 and 0.11/0.54;
- 6 exact combos/player;
- SPR 1/2/4;
- checkpoints 100/400/1200;
- single sequential job.

Latest inspection:

- phase A / SPR 1: PASS;
- phase A / SPR 2: running;
- remaining four cells: pending.

The development selector was frozen before numerical inspection in `docs/R4_DEV_SELECTION_PRECOMMIT_20260816.md`. It uses conservative strategic-loss plus compression/cost Pareto logic and may carry at most three deterministic finalists.

R4 machinery already has passing regressions for exact-control equivalence, one-sided candidate-vs-exact restriction, deterministic checkpoint/resume, hole-card-order invariance and all 24 global suit permutations for every current candidate.

The independent R4 heldout-v1 set remains firewalled and **NOT RUN**. Its eight boards, two alternate range-phase pairs, 8 combos/player, SPR 1/2/4 and 300/1200/3600 checkpoints were frozen before any R4 numerical result.

## Current project state

`R0 = PASS`

`R1 = IN PROGRESS`

`R2 = PASS`

`R3 = IN PROGRESS`

`R4 = IN PROGRESS`

`R5-R8 = PENDING`

`R9 = BLOCKED`

`READY FOR TABLES = NO`
