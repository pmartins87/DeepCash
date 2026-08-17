# DeepCash — Work handoff — 2026-08-16

This document is an operational continuation point for a new ChatGPT Work thread. It is not a replacement for `STATUS.json`, `docs/ROADMAP.md`, or accepted-evidence documents.

## Mission

Continue DeepCash toward a robust 6-max NLHE cash-game AI under the canonical R0-R15 roadmap. Do not skip gates and do not start production training while R9 is BLOCKED.

Target hardware for final physical calibration: single Ryzen 9. Long production training is approximately three months only after R1-R8 PASS.

## Canonical status

- R0 PASS
- R1 IN_PROGRESS
- R2 PASS
- R3 IN_PROGRESS
- R4 IN_PROGRESS
- R5 IN_PROGRESS
- R6-R8 PENDING
- R9 BLOCKED
- R10-R15 PENDING
- READY FOR TABLES = NO

`BLOCKED` means execution is deliberately forbidden by unmet hard prerequisites. `PENDING` means a later gate has not yet become active. See `docs/STATUS_SEMANTICS.md`.

## Immediate active work

### R4 corrected representation replay

Workflow run `31976302604`.

At the latest check:

- bucket-constrained BR structural gate: PASS;
- phase A / SPR1: PASS;
- phase A / SPR2: PASS;
- phase A / SPR4: running;
- remaining phase B cells pending.

Do not open R4 held-out v1 until the corrected development replay is complete, inspected, and at most three deterministic finalists are frozen.

Methodology correction: `docs/R4_BUCKET_BR_METHODOLOGY_CORRECTION_20260816.md`.

### R5 cheap legal tabular variance reduction

Structural oracle run `31976450221`: PASS.

Numerical benchmark run `31976572985`: PASS.

Artifact `9271293501`, SHA-256 `83e04bf241f59d645d7be68c9f781042f4dfe85a970b4f5d17ab5c6b7c6d67d6`.

Accepted evidence: `docs/R5_TABULAR_VR_BENCHMARK_V1_ACCEPTED_20260816.md`.

At 10k iterations over the frozen 4-board x 5-seed development battery:

- ZERO mean exploitability/pot: `0.01619797`, mean train `3.41965s`, stdev `0.00188020`;
- TABULAR_RUNNING: `0.01577459`, `3.84933s`, stdev `0.00098999`;
- INFOSET_EXACT: `0.01500396`, `14.25467s`, stdev `0.00101858`.

TABULAR_RUNNING therefore gave about 2.61% lower mean exploitability than ZERO at only about 1.126x hosted-CI time, and approximately halved cross-seed dispersion. It is the leading cheap legal VR primitive currently tested, not a production winner.

Next justified R5 experiment: precommit an equal-wall-clock/scaling comparison that combines only already-gated compatible primitives. Do not tune the same development battery until the candidate wins.

## Methodological invariants

1. Exact game/traversal state; lossy compression only at representation boundary.
2. No opponent private-card leakage into decision representation or legal variance-reduction APIs.
3. Common-reference one-sided restriction is the primary action-abstraction metric.
4. Own-tree exploitability is convergence evidence only.
5. Propagate exact-BR uncertainty; never choose a winner from unconverged policies.
6. Never invent post-hoc thresholds.
7. Hosted-CI fixed-iteration timing is engineering evidence only.
8. Final R3/R4/R5 selection requires equal-wall-clock evidence on the physical Ryzen 9.
9. Failed/invalidated experiments remain in the audit trail.
10. R9 production training remains BLOCKED until R1-R8 PASS.

## First actions for the next Work thread

1. Read `STATUS.json`, `docs/ROADMAP.md`, `docs/ACTIVE_GATES_20260816.md`, and this handoff.
2. Query GitHub Actions run `31976302604`; if complete, inspect the full R4 corrected artifact before changing any finalist or touching held-out v1.
3. Confirm general CI after the latest R5 tabular commits.
4. Promote the accepted R5 tabular benchmark into canonical status/active-gate ledgers if not already reflected there.
5. Precommit the next R5 equal-wall-clock/scaling experiment before launching it.
6. Keep R1 target-site rules debt and R3 physical-Ryzen calibration visible; do not let active R4/R5 research hide those hard prerequisites.

## Suggested first instruction in ChatGPT Work

`Continue the DeepCash project from docs/WORK_HANDOFF_20260816.md. Use the GitHub connector proactively. Read STATUS.json and the active-gate ledger first, inspect all currently running/unaccepted workflows before claiming evidence, and continue the R0-R15 roadmap without skipping gates. Do not start R9 until R1-R8 are PASS.`
