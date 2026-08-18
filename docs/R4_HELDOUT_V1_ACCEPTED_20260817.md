# R4 representation held-out-v1 — accepted engineering evidence — 2026-08-17

Status: **ACCEPTED ENGINEERING EVIDENCE / R4 REMAINS IN_PROGRESS**

This document records the post-run inspection of the precommitted deterministic R4 held-out-v1 generation. It accepts the experiment as engineering evidence. It does **not** select a production private-state representation, does **not** close R4, and does **not** authorize R9.

## Canonical run and artifact

- workflow: `DeepCash R4 representation held-out v1`;
- run: `32085317554`;
- event: manual `workflow_dispatch`;
- source branch: `main`;
- source commit: `2c1bf1ac1e04a834caaebc2d000bc05a9fdf0c17`;
- run conclusion: `success`;
- combined artifact: `9308636169`, `r4-representation-heldout-v1`;
- artifact digest: `sha256:6860be515a79532110c4c42ee901513db93f74b9d94b96deedfac626c5fd13f2`;
- archive contents: six cell JSON files plus `r4_heldout_v1_summary.json`;
- frozen finalists: `equity8`, `equity4_blocker2`, `category_equity4`.

All six matrix jobs and the final summarize job completed successfully. The completeness gate required exactly six JSON cell payloads before emitting the combined summary.

## Coverage audit

Each cell contains eight precommitted held-out boards, three candidates and checkpoints `300`, `1200`, `3600`, for 72 rows per payload and 432 raw rows total.

The nominal matrix is:

- phase A: `(p0=0.19, p1=0.47)` at labeled SPR 1/2/4;
- phase B: `(p0=0.58, p1=0.83)` at labeled SPR 1/2/4;
- eight boards per phase/geometry;
- 8 exact range combos per player.

Every candidate/board path has all three checkpoints. No row, candidate, board or checkpoint is missing.

## Checkpoint-3600 combined metrics

| Candidate | Mean upper loss / pot | P90 upper / pot | Worst upper / pot | Mean interval width / pot | Mean compression | Mean train s |
|---|---:|---:|---:|---:|---:|---:|
| `equity8` | **0.00193346** | **0.00715726** | **0.01005899** | **0.00054445** | 0.816406 | 28.4708 |
| `equity4_blocker2` | 0.00388414 | 0.00968563 | 0.01655804 | 0.00060850 | 0.660156 | 28.2678 |
| `category_equity4` | 0.00663440 | 0.01350116 | 0.01784304 | 0.00074873 | **0.558594** | 28.1469 |

`equity8` is the clear **fidelity leader** on this generation: it has the lowest mean, P90 and worst conservative restriction-loss upper bound. `category_equity4` remains the most compressed finalist, with `equity4_blocker2` between them. The mechanical Pareto frontier therefore still contains all three; no post-hoc scalar score is introduced to force a production winner.

At checkpoint 3600, the lowest upper-bound candidate by board/phase/geometry is approximately:

- `equity8`: 31.5 of 48 nominal board cells after splitting exact ties;
- `equity4_blocker2`: 14.5 of 48;
- `category_equity4`: 2 of 48.

This paired count is descriptive only; the canonical selection metrics remain the conservative loss bounds and compute/compression costs.

## Convergence audit

All 144 candidate × board × nominal-geometry trajectories decreased monotonically in `worst_loss_upper_per_pot` from `300 -> 1200 -> 3600`.

Combined means by checkpoint:

| Candidate | 300 | 1200 | 3600 |
|---|---:|---:|---:|
| `equity8` | 0.00767965 | 0.00308303 | **0.00193346** |
| `equity4_blocker2` | 0.00957642 | 0.00486098 | **0.00388414** |
| `category_equity4` | 0.01246148 | 0.00756451 | **0.00663440** |

Mean value-interval width also contracts strongly through the checkpoints. No candidate is promoted from an unresolved early-checkpoint advantage.

## Important geometry limitation found during audit

The six nominal SPR jobs are **not six distinct action geometries**.

The benchmark materializes the frozen one-bet reference fractions `{25%, 33%, 50%, 75%, 100%, 150%, 200%}` and clips them by stack. Therefore:

- labeled SPR1 / stack100 uses `[25, 33, 50, 75, 100]`;
- labeled SPR2 / stack200 uses `[25, 33, 50, 75, 100, 150, 200]`;
- labeled SPR4 / stack400 also uses `[25, 33, 50, 75, 100, 150, 200]`.

Consequently the SPR2 and SPR4 strategic rows are exact duplicates for a given phase/board/candidate/checkpoint apart from wall-clock noise. The 48 nominal checkpoint-3600 rows per candidate correspond to **32 distinct strategic coordinates**: 2 phases × 2 materialized action geometries × 8 boards.

This does not invalidate the precommitted experiment: it correctly measures the frozen river one-bet laboratory that was actually specified. It does limit the claim. Held-out-v1 cannot be cited as evidence that the abstraction generalized separately to true SPR2 and true SPR4 stack-dependent trees. Production R4 still requires street/SPR-compatible architecture and physical equal-compute evidence on a tree where deeper stack changes available actions and/or continuation structure.

## Accepted interpretation

1. The held-out firewall worked: only the three frozen deterministic finalists consumed held-out-v1.
2. The run is complete, reproducible and internally consistent.
3. `equity8` is the current deterministic **accuracy leader**.
4. `equity4_blocker2` and `category_equity4` remain legitimate lower-compression Pareto alternatives.
5. No production representation is selected from this experiment alone.
6. The SPR2/SPR4 geometry duplication is now an explicit audit constraint and must not be hidden by the nominal matrix labels.
7. Any counterfactual-value or clustering family must be introduced as a **separate frozen generation** and must not reuse held-out-v1 as unseen evidence.
8. Learned embeddings remain downstream of deterministic/clustering baselines and must justify their real-compute cost.
9. Physical Ryzen equal-wall-clock comparison remains mandatory before the production representation freeze.

## Next R4 work

- record this run in `STATUS.json`, `docs/ROADMAP.md` and the active-gate ledger;
- freeze a separate Generation-2 clustering/counterfactual candidate protocol before numerical consumption;
- reserve a new held-out generation for Generation-2; held-out-v1 is permanently consumed;
- keep `equity8` as the deterministic accuracy anchor in future comparisons;
- only after candidate generations are complete, run a physical Ryzen equal-wall-clock comparison on a stack/street geometry that actually distinguishes the intended SPRs;
- freeze one production representation only after strategic fidelity, memory/infoset reduction and real compute are jointly audited.
