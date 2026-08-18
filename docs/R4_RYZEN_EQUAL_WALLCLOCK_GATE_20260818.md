# R4 physical Ryzen equal-wall-clock gate — 2026-08-18

Status: **PREPARED / NOT YET RUN**

This is the next admissible R4 evidence gate after Generation-2 held-out-v2 run `32101218388`.

## Candidates

Run exactly these three frozen representations; do not add or tune a new candidate after seeing physical timing/results:

1. `matchup_cluster8` — hosted held-out fidelity leader;
2. `equity8` — deterministic anchor;
3. `matchup_cluster4` — aggressive compression control.

## Required comparison principle

The physical test must be **equal wall clock on the target Ryzen 9**, not equal iterations. Each candidate receives the same measured CPU-time budget per paired cell. Warm-up, process affinity, worker count, Python/build version, checkpoint I/O, and machine load must be held constant or recorded.

Hosted-GitHub seconds are excluded from the production decision.

## Geometry

At minimum preserve the validated distinct river geometries:

- SPR1: pot 100 / stack 100 / physical sizes 25, 50, 100;
- SPR2: pot 100 / stack 200 / physical sizes 25, 50, 100, 200;
- SPR4: pot 100 / stack 400 / physical sizes 25, 50, 100, 200, 400.

The physical package should then extend the representation comparison into the first street/stack-compatible architecture used by the production solver so the selected representation is not justified by river-only compute behavior.

## Measurements to retain

For every paired candidate/cell retain:

- exact machine/CPU/RAM metadata;
- worker count and affinity policy;
- elapsed wall time and CPU time;
- peak RSS / memory footprint;
- iterations or traversals completed inside the fixed budget;
- infoset count and action-slot count;
- checkpoint size and write/read throughput where applicable;
- final exploitability / conservative fidelity bound supported by that architecture;
- deterministic seed/config hash;
- stdout/stderr and raw JSON/CSV result artifact.

## Decision rule

Production representation freeze requires evidence that the candidate preserves the hosted strategic advantage while remaining competitive in real compute/memory scaling.

Default interpretation of current evidence before physical execution:

- prefer `matchup_cluster8` if its physical throughput/memory cost does not erase its very large held-out fidelity advantage over `equity8`;
- retain `equity8` if the clustering overhead creates a material equal-wall-clock disadvantage at realistic street support;
- select `matchup_cluster4` only if the approximately 50% representation footprint enables a real throughput/memory gain large enough to compensate for its much larger held-out restriction loss.

Do not invent a post-hoc scalar score. Report the Pareto evidence and freeze the production representation only when the tradeoff is resolved for the target three-month Ryzen envelope.

## R4 exit

After a valid physical result is audited:

1. record immutable raw artifacts and hashes;
2. freeze one production representation plus any explicitly justified fallback;
3. update `STATUS.json` / `docs/ROADMAP.md`;
4. mark R4 PASS only if the selected representation is compatible with the intended R5 solver/traversal and R6 street architecture.

Until then R4 remains **IN_PROGRESS**.
