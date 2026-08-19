# R6 exact turn betting + river control gate — 2026-08-19

Status: **IN PROGRESS / STRUCTURAL CONTROL IMPLEMENTED / NOT R6 PASS**

This milestone advances R6 beyond the previous chance-only `TurnPublicState -> river` composition. The new control is a real two-street imperfect-information game with turn decisions, exact public river chance, exact card removal and river decisions in one CFR tree.

## Scope

`deepcash_core.turn_river_exact_game` implements a deliberately tractable heads-up control game:

```text
turn P0 decision
-> CHECK or BET
-> turn P1 decision/response
-> fold terminal OR called/check-check continuation
-> exact public river chance
-> river P0 decision
-> CHECK or BET
-> river P1 decision/response
-> fold/call/showdown terminal
```

Each street currently allows at most one bet and one fold/call response. Raises are intentionally outside this correctness control. Player 0 acts first on both streets.

## Exact state transitions

The control keeps the following exact:

- four-card turn board;
- both exact two-card private ranges and their weights;
- incompatible private deals;
- public river card chance after exact private-card removal;
- pot and remaining stack after a called turn bet;
- turn all-in calls, which correctly remove river betting and continue through public river chance directly to showdown;
- integer-chip action materialization and clipping;
- showdown payoffs;
- public action history and perfect-recall infoset identity.

A called turn bet of `b` changes `(pot, stack)` to `(pot + 2b, stack - b)` before the river. River bet sizes are materialized from that resulting geometry rather than copied from the turn.

## Solver semantics

The control uses the already audited alternating solver semantics and defaults to:

`ALT_DCFR_150_0_2`

For each alternating player update, the full exact private-deal support and all legal public river cards are traversed. Counterfactual regret reach and average-policy own realization reach are propagated through the turn action tree and the public river chance node. There is no RNG in this control.

The implementation therefore supplies a deterministic exact-control path for R6. It does **not** yet claim production-scale efficiency.

## Exact range propagation diagnostic

`conditioned_river_ranges(...)` exposes the range boundary implied by a solved or supplied turn policy.

For a public turn history, each combo is reweighted only by that player's own realization probability along the observed history, then the public river card is removed exactly. The function never uses the realized opponent private hand to compute an individual combo's reach factor.

Examples:

- `CHECK_CHECK`: P0 weight × P0(check), P1 weight × P1(check after check);
- `P0_BET_b_CALL`: P0 weight × P0(bet b), P1 weight × P1(call b);
- `P1_BET_b_CALL`: P0 weight × P0(check) × P0(call b), P1 weight × P1(bet b).

This makes the action-conditioned range transition explicit and testable before production abstraction is reintroduced.

## Structural tests

The gate tests require:

1. called turn bets to carry exact pot/stack geometry into the river;
2. clipped/deduplicated river actions to use the post-turn geometry;
3. a called turn all-in to bypass river decision infosets and reach exact public-river showdown;
4. an all-check policy to equal an independently computed exact public-river showdown average;
5. action-conditioned ranges to use only own realization reach and exact public-card removal;
6. alternating DCFR execution to be deterministic;
7. `1 + 1` iterations to equal a single two-iteration continuation exactly in memory;
8. invalid negative advances and untrained result extraction to fail closed.

## Deliberate boundary / next R6 gate

This PR is not an R6 acceptance result. In particular:

- exact two-street best-response/exploitability is not yet implemented, so this milestone makes no exploitability claim;
- the R4 production `matchup_cluster8` representation is not yet inserted into the river infosets of this two-street control;
- there is no bounded-latency local-resolving API yet;
- there are no turn raises, flop integration or preflop integration yet.

The next focused R6 gate is to add an **exact two-street best-response oracle** to this control and validate solver convergence/continuation semantics on frozen tiny games. Only after that correctness oracle passes should the production R4 representation be introduced into the two-street path and compared against the exact control.
