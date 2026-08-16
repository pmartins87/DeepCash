# DeepCash active gates — 2026-08-16

This is a transient audit ledger for gates that have been launched but **must not be promoted to PASS merely because the implementation/workflow exists**. Canonical `STATUS.json`, validation-status documents and `docs/ROADMAP.md` remain authoritative for accepted evidence.

## R1 — bidirectional legal-action oracle v3 — ACCEPTED

Workflow:

- `.github/workflows/r1-legal-actions-oracle-v3.yml`

Tool:

- `tools/crosscheck_pokerkit_legal_actions_v3.py`

The v2 gate correctly failed on one preflop blind-epoch reopening disagreement with pinned PokerKit. Root-cause analysis showed that PokerKit begins its internal completion/raise amount at zero, so a first voluntary short all-in above a live BB can reset its acted-player state even when a prior caller is facing less than a full raise. DeepCash keeps generic cumulative-full-raise semantics and now has a direct regression for that exact case.

v3 preserves the complete v2 bidirectional action/boundary comparison and permits only the structurally identified upstream blind-epoch divergence. Every other mismatch remains fatal.

Accepted evidence:

- run `31963863819`;
- commit `5e6c46349980b9a6e861b69736a3d7c49bb7f686`;
- **120 deterministic hands**, 24 per player count from 2 through 6;
- **592 live decision states** checked;
- exactly **1** expected pinned-PokerKit blind-epoch divergence;
- exact completed-hand stack parity retained.

This closes the generic bidirectional-oracle gap. It does **not** close target-site short-all-in/reopen evidence, so R1 remains IN PROGRESS.

## R3 — exhaustive opening-size subset lattice -> unseen held-out v2

Workflow:

- `.github/workflows/river-opening-subset-lattice-v1.yml`

Run:

- `31962334355` — **IN PROGRESS** at latest inspection.

Engineering candidate universe:

- every one-, two- and three-size proper subset of the fixed 25/50/75/100% opening reference;
- 14 candidates total;
- no new arbitrary opening size may be introduced from the lattice result without starting a new validation generation.

Seen engineering cells:

1. control boards, SPR 1, 4 combos/player, phases 0.00/0.27;
2. control boards, SPR 4, 4 combos/player, phases 0.00/0.27;
3. held-out-v1 boards, now explicitly seen, SPR 1, 6 combos/player, phases 0.13/0.61;
4. held-out-v1 boards, now explicitly seen, SPR 4, 6 combos/player, phases 0.13/0.61.

At latest inspection, both control lattice jobs had completed successfully while the two larger held-out-v1/seen engineering jobs were still running. This partial state is **not** accepted as a lattice result.

Precommitted selector:

- `tools/select_opening_lattice_champions.py`;
- exactly one champion forwarded per cardinality 1/2/3;
- minimize worst conservative restriction-loss upper bound across all seen engineering boards/cells;
- tie within 1e-12 -> mean upper bound -> cumulative training seconds -> lexical name.

Unseen v2 validation:

- frozen in `docs/R3_HELDOUT_V2_PRECOMMIT_20260816.md` before lattice-result acceptance;
- six new boards;
- 8 combos/player;
- phases 0.31/0.79;
- SPR 1/2/4;
- checkpoints 300/1200/3600;
- only the three preselected cardinality champions may enter;
- selector has no access to held-out-v2 artifacts.

Acceptance discipline:

- held-out-v2 is a generalization gate, not an automatic production selector;
- if v2 exposes a material reversal/failure, preserve it as seen evidence, return to engineering and create a new unseen validation generation after any retuning;
- no action-family freeze without physical Ryzen equal-compute evidence.

Current canonical status until completed and inspected: **UNACCEPTED**.

## R3 — independent raise-size unseen validation

Workflow:

- `.github/workflows/river-raise-size-heldout-v1.yml`

Run:

- `31962687271` — **IN PROGRESS** at latest inspection.

Precommit:

- `docs/R3_RAISE_SIZE_HELDOUT_PRECOMMIT_20260816.md`

Purpose:

- validate the raise-size conclusion on boards not used by opening held-out-v2;
- fixed candidates `Q1_100`, `Q2_50_100`, `Q2_100_150`, `Q3_50_100_150`;
- six separate unseen boards;
- 6 combos/player;
- phases 0.22/0.68;
- SPR 1/2/4;
- checkpoints 300/1200/3600.

Partial evidence at latest inspection:

- SPR 1 job completed successfully and uploaded artifact `9267994573`;
- its exact materialized raise maps collapse **all four nominal candidates to the same action set** at stack=pot=100: for openings 25/50/75 every candidate can only raise all-in to 100, and an opening of 100 has no raise branch;
- consequently all four candidates have identical restriction-loss/interval curves at SPR 1;
- at checkpoint 3600 the six-board mean/worst upper bound is approximately `0.000963 / 0.001841` pot and equals the remaining exact-BR interval resolution;
- SPR 2 and SPR 4 jobs remain running, so this is geometry evidence only and **not** a final raise-size conclusion.

Acceptance discipline:

- `upper <= exact-BR interval width` is reported only as a measurement-resolution diagnostic, never as a permanent production threshold;
- any held-out evidence for material Q1 loss returns the project to raise-size engineering;
- physical Ryzen cost remains mandatory before freeze.

Current canonical status until all SPR cells complete and are inspected: **UNACCEPTED**.

## R4 — deterministic representation development battery

Workflow:

- `.github/workflows/river-representation-dev-v1.yml`

Run:

- `31964142661` — **IN PROGRESS** at latest inspection.

Selection precommit:

- `docs/R4_DEV_SELECTION_PRECOMMIT_20260816.md` was frozen before the first numerical R4 development result;
- development ranking uses conservative one-sided restriction loss plus compression/action-slot cost and a Pareto rule, not a post-hoc scalar score;
- carry at most three deterministic finalists into the next stage.

Frozen first development battery:

- only the four already-seen development control boards;
- candidates `category`, `strength4`, `equity4`, `equity8`, `category_equity4`, `equity4_blocker2`, `equity8_blocker2`;
- two phase pairs `0.00/0.27` and `0.11/0.54`;
- 6 exact combos/player;
- SPR 1/2/4;
- checkpoints 100/400/1200;
- single sequential workflow job to avoid starving R3 evidence jobs.

The underlying R4 machinery has already passed general CI, including:

- exact-combo representation reproduces the original river CFR+ control;
- one-sided candidate-vs-exact restriction methodology;
- staged-vs-monolithic CFR+ equivalence;
- JSON checkpoint future-path equivalence;
- hole-card-order invariance;
- all **24 global suit permutations** for every current deterministic representation candidate;
- frozen Pareto aggregation logic and fail-closed candidate-set/checkpoint validation.

Latest broad CI for those tests: run `31964282905` — **PASS**.

R4 held-out v1 remains firewalled and **NOT RUN**. Its independent eight-board/two-phase/SPR 1-2-4 generation was frozen in `docs/R4_HELDOUT_PRECOMMIT_20260816.md` before any R4 numerical result.

Current status: **R4 IN PROGRESS; development numerical gate UNACCEPTED**.

`R1 = IN PROGRESS`

`R3 = IN PROGRESS`

`R4 = IN PROGRESS`

`READY FOR TABLES = NO`
