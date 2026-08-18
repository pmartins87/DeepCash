# R4 / R5 / R6 physical compatibility precommit — 2026-08-18

Status: **FROZEN BEFORE PHYSICAL RESULT**

This gate is intentionally finite. It follows the accepted R4 hosted held-out-v2 evidence, the first physical 20-second equal-wall-clock run, and the successful Windows memory/affinity repair. It is not a new candidate generation.

## Question

Can the leading R4 representation, `matchup_cluster8`, retain its large fidelity advantage over the `equity8` anchor when it is combined with the leading exact R5 alternating discounted update semantics and reached through the first R6 turn-to-river public-state chance-transfer boundary, without creating a material equal-wall-clock or memory disadvantage on the target Ryzen 9?

## Frozen solver semantics

Use exactly `ALT_DCFR_150_0_2`, the historical/OpenSpiel-style post-update discounted control already retained by R5:

1. compute instantaneous regret under alternating player-local timing;
2. add instantaneous regret to cumulative regret;
3. discount the updated cumulative regret with alpha 1.5 for non-negative regret and beta 0 for negative regret;
4. use quadratic output/average weighting.

This gate must not silently substitute the separately audited paper-equation old-discount-then-add recurrence.

## Frozen R4 candidates

Exactly:

- `matchup_cluster8` — physical/held-out fidelity leader;
- `equity8` — deterministic accuracy/compute anchor.

`matchup_cluster4` is omitted from this compatibility gate because the already-consumed held-out and physical evidence establishes it only as an aggressive compression endpoint with much larger restriction loss. No new R4 candidate may be added after this precommit.

## First R6 boundary

This is the first **public turn state -> exact public river chance -> river subgame** contract. It is deliberately smaller than a full turn betting/resolving solver.

For each turn public state:

- the four public board cards remain exact;
- both private ranges remain weighted exact-combo supports;
- each possible river card removes every private combo containing that card;
- incompatible private deals remain excluded exactly;
- the marginal public chance mass of a river card is the total remaining compatible private-deal weight after card removal;
- river-card probabilities are those masses normalized over legal river cards;
- the Generation-2 physical action grid materializes separately at SPR 1/2/4.

The selected R4 representation is constructed only after the river public card and card-removal conditioning are known. No realized opponent private card is available to the representation.

## Frozen turn battery

Turn boards:

- `ace_high_dry_turn`: `Ah Kd 9c 4s`;
- `paired_turn`: `Qs Qd 8h 3c`;
- `connected_turn`: `Jh Td 8c 7s`;
- `three_flush_turn`: `Kh 9h 5h 2c`.

Range phases:

- A: p0 `0.19`, p1 `0.47`;
- B: p0 `0.58`, p1 `0.83`.

Geometry:

- pot 100;
- SPR1 stack 100 -> `[25,50,100]`;
- SPR2 stack 200 -> `[25,50,100,200]`;
- SPR4 stack 400 -> `[25,50,100,200,400]`;
- 8 exact range combos per player;
- minimum bet 20.

For every turn board × phase × SPR coordinate, enumerate the exact river public chance distribution and select exactly two river children by highest chance mass, ties by encoded river-card id. This selection depends only on the frozen public/range state, never on candidate results.

Total intended physical child cells: `4 × 2 × 3 × 2 = 48`. Total candidate runs: `48 × 2 = 96`.

## Equal-compute protocol

Reference per selected river child:

- exact-combo `ALT_DCFR_150_0_2`;
- 600 fixed iterations;
- reference construction/evaluation excluded from candidate budgets.

Each candidate receives exactly 3.0 seconds target training wall-clock per selected river child. In a fresh subprocess it trains:

- p0-restricted representation state;
- p1-restricted representation state;
- joint representation state;

in equal-iteration round-robin chunks of 5 iterations until the candidate budget is reached. Evaluation and checkpoint I/O occur after the budget and are separately recorded.

Candidate order rotates deterministically by physical child cell. Candidate workers are sequential (`parallel_candidate_workers = 1`).

## Required outputs

Retain for every child/candidate:

- turn board, selected river card and exact public chance probability;
- physical SPR/action geometry;
- exact reference BR interval;
- candidate p0/p1 restriction-loss bounds;
- joint representation exploitability within the representation-restricted game;
- iterations completed and iterations/second;
- action slots and infosets;
- peak working set/RSS and affinity;
- checkpoint bytes/hash/read-write throughput;
- stdout/stderr and deterministic configuration/hash metadata.

## Decision rule

Do not invent a scalar score.

The compatibility gate supports an R4 production freeze only if `matchup_cluster8` preserves its strategic advantage over `equity8` across the turn-to-river bridge while remaining physically competitive in throughput and memory. Tiny adverse differences inside the exact-reference/solver resolution interval are not treated as resolved reversals.

A concrete compatibility failure may reopen R4 engineering. Absent such a failure, do not create Generation-3.

Even on PASS, this gate does **not**:

- select the final sampled production traversal for R5;
- prove multi-public-node CCS/VR-MCCFR behavior;
- implement turn betting/local resolving;
- mark R6 PASS;
- authorize R9 production training.

Its purpose is to resolve the specific R4 production-representation compatibility debt before the roadmap proceeds deeper into R5/R6.
