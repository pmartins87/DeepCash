# R6 action-conditioned posterior river representation bridge v1 — precommit 2026-08-19

Status: **FROZEN BEFORE FIRST NUMERICAL RESULT**

## Purpose

R4 froze `matchup_cluster8` as the production private-state representation primitive after exact public-card/card-removal conditioning. R6 now has an exact turn+river control and an exact two-street best-response oracle. Before any local-resolving feedback architecture is built, this gate asks a narrower question:

> Does the frozen R4 representation remain faithful when the river ranges are not static fixture ranges, but exact action-conditioned posterior ranges produced by a real turn betting policy?

This gate deliberately avoids inserting a dynamic bucket map into the monolithic two-street CFR tree. Doing so would make river bucket identity depend on a posterior range that itself changes with the evolving turn policy, creating a circular and unstable information-state definition. Instead, the turn policy is frozen first, posterior river subgames are then materialized exactly, and R4 representation fidelity is measured on those fixed posterior subgames.

## Frozen R4 identities

The runner must load `deepcash_core/data/r4_production_representation_v1.json` and fail unless:

- schema = `DEEPCASH_R4_PRODUCTION_REPRESENTATION_FREEZE_V1`;
- status = `FROZEN`;
- production representation = `matchup_cluster8`;
- accuracy anchor = `equity8`.

No other representation candidate may be introduced by this gate.

## Frozen exact turn source states

Two exact turn states are used only to generate action-conditioned posterior ranges:

1. `posterior_ahigh`: `Ah Kd 9c 4s`;
2. `posterior_connected`: `9h 8d 7c 3s`.

For both:

- exact combos/player = `12`;
- P0 quantile phase = `0.19`;
- P1 quantile phase = `0.67`;
- turn pot = `100`;
- effective stack = `200`;
- minimum bet = `20`;
- turn bet fractions = `1/2, 1` of pot, materializing `50,100`;
- river candidate fractions use frozen `GEN2_REFERENCE_FRACTIONS` and are clipped to the exact post-turn stack;
- exact source solver variant = `ALT_DCFR_150_0_2`;
- exact source solver iterations = `12`.

The source solve is a deterministic posterior-state generator. This gate makes **no claim** that 12 iterations are a production-quality turn strategy or that its source exploitability is sufficiently small.

## Frozen public turn histories

Exactly three observed turn continuations are sampled from each source policy:

- `CHECK_CHECK`;
- `P0_BET_50_CALL`;
- `P1_BET_50_CALL`.

The 100-chip turn bet is retained in the source game so the policy is solved in the frozen two-size turn action geometry, but the bridge evaluates the three histories above only. History selection is fixed before the source solve and cannot depend on posterior quality.

## Frozen public river cards

For `posterior_ahigh`:

- `2h`;
- `Tc`.

For `posterior_connected`:

- `2d`;
- `Qh`.

Therefore the gate contains exactly:

`2 turn boards × 3 public histories × 2 river cards = 12 posterior river subgames`.

For every subgame, `conditioned_river_ranges(...)` must:

- multiply each P0 combo only by P0's own realization probability along the observed turn history;
- multiply each P1 combo only by P1's own realization probability along that history;
- remove the public river card exactly;
- never inspect the realized opponent private hand when computing an individual combo's posterior weight.

## Frozen river fidelity protocol

For each of the 12 posterior river subgames:

1. materialize the exact five-card river board;
2. use exact action-conditioned posterior P0/P1 ranges and their weights;
3. carry the exact post-turn `(pot, stack)` geometry into river action materialization;
4. solve an exact-combo reference with `ALT_DCFR_150_0_2` for `400` iterations;
5. for each candidate (`matchup_cluster8`, `equity8`), build deterministic Generation-2 bucket maps from that exact posterior river spec;
6. solve a P0-only restricted game and a P1-only restricted game, each for `400` iterations with the same alternating variant;
7. compute conservative one-sided restriction-loss bounds via the already audited `restriction_loss_bounds(...)` construction;
8. record the joint bucket counts/action-slot compression as architecture diagnostics, but do not use bucket-constrained joint exploitability as the fidelity metric.

The principal fidelity metric is `worst_loss_upper_per_pot` from the one-sided restriction bound.

## Frozen resolution rule

For each candidate/cell define its numerical resolution interval as:

`max(reference BR interval, P0-restricted BR interval, P1-restricted BR interval) / river pot`.

For a paired cell define:

`adverse = matchup_cluster8 loss_upper - equity8 loss_upper`.

- `adverse <= 0`: nominal win/tie for the production representation;
- `adverse > 0` but `adverse <= max(matchup_resolution, equity_resolution)`: unresolved adverse difference;
- `adverse > max(matchup_resolution, equity_resolution)`: resolved loss for `matchup_cluster8`.

This freezes the interpretation before results are known and follows the same principle used by the R4 production freeze: numerical differences inside the solver/reference resolution envelope are not treated as resolved reversals.

## Acceptance rule

`matchup_cluster8` passes this R6 posterior bridge only if all are true:

1. exactly 12 posterior cells and 24 candidate rows are present with unique identities;
2. every posterior river spec has non-empty compatible exact private-deal support;
3. every candidate map covers every surviving exact combo and materializes no more than eight buckets/player;
4. mean `worst_loss_upper_per_pot` for `matchup_cluster8` is no greater than the mean for `equity8`;
5. there are **zero resolved paired losses** for `matchup_cluster8` under the frozen resolution rule;
6. all structural tests and repository CI pass.

There is deliberately no new post-hoc absolute loss threshold. R4's physical freeze already established absolute suitability of the primitive; this gate tests whether turn-action conditioning causes a resolved reversal against its frozen accuracy anchor.

## Consequence of PASS

A PASS authorizes the next R6 engineering step: a bounded local-resolving interface that takes an exact public turn state plus action-conditioned ranges and constructs/solves the corresponding river subgame using the frozen representation primitive.

A PASS does **not** mark R6 PASS, prove flop/preflop integration, select the final R5 sampled traversal, satisfy R8, or authorize R9.
