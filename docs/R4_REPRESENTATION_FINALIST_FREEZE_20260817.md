# R4 deterministic finalist freeze — 2026-08-17

Status: **FROZEN / HELDOUT-V1 PREPARED_NOT_RUN**

This checkpoint freezes the only three deterministic candidates allowed to consume the precommitted R4 held-out-v1 generation. It does not select a production representation and does not authorize physical Ryzen comparison or R9.

## Canonical development evidence

- workflow run: `31976302604` — every step completed successfully;
- artifact: `9274193444`, `r4-representation-dev-v2`;
- ZIP SHA-256: `b1edea689f1d7417f80b2f77d8ec8241042cde81a75eb5f632eea8af38d8fd3e`;
- contents: six JSON files, 504 rows total, 24 development cells;
- frozen selection checkpoint: `1200`, yielding 168 candidate/cell rows;
- method: exact cards/chance/payoffs/action tree with bucket-constrained exact BR and one-sided private-infoset restriction.

The ZIP hash, schema, configuration grids, row counts, candidate coverage, checkpoint coverage and normalization were independently rechecked before this freeze.

## Frozen metrics at checkpoint 1200

| Candidate | Worst upper/pot | Mean upper/pot | P90 upper/pot | Mean compression | Mean action-slot ratio |
|---|---:|---:|---:|---:|---:|
| `equity8` | 0.00547082 | 0.00211593 | 0.00404692 | 0.979167 | 0.979167 |
| `equity4_blocker2` | 0.04552251 | 0.01231955 | 0.04124224 | 0.833333 | 0.833333 |
| `category_equity4` | 0.04552251 | 0.01703230 | 0.04190883 | 0.802083 | 0.802083 |

The mechanical Pareto frontier contained all seven candidates because fidelity and structural cost traded monotonically. The three-candidate cap was therefore applied without inventing a scalar score:

1. `equity8` — high-fidelity finalist; `equity8_blocker2` added structural cost without a resolved strategic gain.
2. `equity4_blocker2` — blocker-sensitive mid-compression finalist.
3. `category_equity4` — structured, more-compressed deterministic alternative.

`category`, `strength4`, `equity4` and `equity8_blocker2` are not permitted into held-out-v1. Their development evidence remains in the audit trail; this freeze is not a claim that they can never appear in a separately precommitted future generation.

## Aggregation correction

The first summary helper treated each JSON payload as one cell even though every development payload contains multiple boards. The raw artifact was valid; the helper failed closed on duplicate candidate rows. This freeze includes a correction that defines a logical cell by board and frozen geometry, plus regression tests for multi-board payloads and duplicate rows.

## Held-out-v1 firewall

The workflow `.github/workflows/river-representation-heldout-v1.yml` has only a manual `workflow_dispatch` trigger. It cannot run from this commit or from a push.

It reads the finalists from `deepcash_core/data/r4_representation_finalists_v1.json` and fixes:

- eight unseen `heldout_v1` boards;
- 8 exact combos per player;
- phase pairs A `(0.19, 0.47)` and B `(0.58, 0.83)`;
- pot 100; SPR 1/2/4 via stacks 100/200/400; minimum bet 20;
- checkpoints 300/1200/3600;
- six matrix cells plus a completeness check and summary artifact.

Dispatch is forbidden until this freeze passes CI and is merged to `main`. A successful workflow will still be unaccepted evidence until every cell and artifact is inspected. No threshold, finalist promotion or production representation is predeclared.

Canonical machine-readable freeze: `deepcash_core/data/r4_representation_finalists_v1.json`.
