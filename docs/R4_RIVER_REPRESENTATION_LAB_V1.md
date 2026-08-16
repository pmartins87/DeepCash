# R4 river private/public representation laboratory v1

Status: **engineering scaffold only — UNACCEPTED**.

This document starts R4 engineering without promoting the roadmap gate to PASS and without consuming any still-unseen R3 validation board.

## Purpose

R4 asks a different question from R3:

- R3: which strategic actions should exist?
- R4: how much private/public information can be compressed without materially damaging strategy?

The game engine remains exact. Cards, card removal, showdown values, pot and the action tree are never bucketed by this laboratory. Only the private information-set identity presented to CFR is aliased.

## New implementation

- `deepcash_core/river_representation_lab.py`
- `tools/benchmark_river_representation_reference.py`
- `tests/test_river_representation_lab.py`

The exact-combo mapping is a mandatory control. With one bucket per exact combo, the new representation solver must reproduce the original `solve_river_cfr_plus` result bit-for-bit on the frozen unit fixture. Any failure there is an implementation bug, not representation evidence.

## Candidate deterministic baselines

The first generation intentionally contains simple, interpretable candidates before any learned embedding:

- `category`: final five-card hand category only;
- `strength4`: four weighted quantiles of exact river hand strength;
- `equity4`: four weighted quantiles of exact showdown equity against the supplied opponent range with exact card removal;
- `equity8`: eight equity quantiles;
- `category_equity4`: category crossed with four equity quantiles;
- `equity4_blocker2`: four equity quantiles crossed with two quantiles of opponent-range mass blocked by the private combo;
- `equity8_blocker2`: eight equity quantiles crossed with two blocker quantiles.

These are baselines, not a production shortlist. Counterfactual-value features/clustering and learned embeddings remain later R4 work after the deterministic benchmark is trusted.

## Common-reference restriction method

For each board/range/action tree:

1. solve `exact vs exact`;
2. solve `candidate P0 vs exact P1`;
3. solve `exact P0 vs candidate P1`;
4. expand every candidate policy back to exact combo keys;
5. compute exact best responses in the uncompressed river game;
6. propagate the same conservative one-sided restriction-loss bounds already used in R3.

This prevents a candidate from looking good merely because both players were forced into the same lossy representation.

A joint `candidate vs candidate` solve is also recorded for infoset/action-slot compression, training time and exploitability diagnostics, but it is not the sole selection criterion.

## Invariance discipline

Feature ties are never split using physical card enumeration order. Unit tests reverse both hole cards while preserving the strategic state and require every non-exact representation candidate to return the same bucket map.

Future R4 gates must additionally test global suit permutation and broader canonical-state metamorphisms before any representation can be frozen.

## Board/data separation

Until the current R3 action-abstraction validation closes:

- the R4 benchmark tool exposes only the existing R3 **development control** board registry;
- it must not inspect `HELDOUT2_RIVER_BOARDS` or any other board that is still unseen for an active R3 gate;
- R4 will receive its own precommitted held-out generation before any R4 candidate result is used for selection.

This prevents cross-gate leakage.

## Current acceptance state

No numerical R4 result has been accepted yet. The repository now contains the machinery needed to begin deterministic state-abstraction measurements while R1/R3 evidence-bearing workflows finish.

`R4 = PENDING / ENGINEERING STARTED`

`READY FOR TABLES = NO`
