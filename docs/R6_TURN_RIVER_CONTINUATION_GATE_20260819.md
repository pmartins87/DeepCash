# R6 turn-to-river continuation gate — 2026-08-19

Status: **IN PROGRESS / FIRST STREET-COMPOSITION PRIMITIVE IMPLEMENTED / NOT R6 PASS**

The physical R4/R5/R6 compatibility gate passed and freezes `matchup_cluster8` as the R4 production private-state representation primitive. R6 can therefore progress without reopening representation engineering.

## Implemented boundary

`deepcash_core.turn_river_continuation.solve_turn_river_continuation` composes the already-validated pieces in the first street-aware continuation path:

```text
TurnPublicState
-> exact public river chance enumeration
-> exact card-removal conditioning of both private ranges
-> immutable R4 production representation per river child
-> ALT_DCFR_150_0_2 exact alternating update semantics
-> independently solved public river subgames
-> chance-weighted turn continuation value
```

The production path resolves its representation name through `deepcash_core/data/r4_production_representation_v1.json`; the name is not copied as an informal constant into R6. An `exact` representation mode is retained as a regression/reference path.

## Correctness boundary

For every legal river child:

- the public river card is exact;
- every private combo containing the public river card is removed before representation construction;
- incompatible p0/p1 private deals remain excluded;
- exact marginal public chance probability comes from normalized compatible private-deal mass;
- pot/stack/action geometry remains exact;
- only private solver infoset identity may be aliased by `matchup_cluster8`;
- the child uses `ALT_DCFR_150_0_2`, the same update semantics frozen by the physical compatibility bridge.

The aggregate `policy_ev` is the exact chance-weighted sum of child policy EVs for this chance-only boundary. The reported `weighted_child_exploitability_per_pot` is a diagnostic weighted average across independently observable public river children.

## Structural tests

The new tests require:

1. exact-representation turn continuation to equal a manual chance-weighted composition of independently solved exact river children;
2. public river probabilities to sum to one;
3. the weighted continuation EV to remain inside the min/max child EV range;
4. production mode to resolve to the immutable `matchup_cluster8` freeze;
5. deterministic repeated execution;
6. unknown non-production representations to fail closed;
7. non-positive iteration budgets to fail closed.

## What this is not

This module deliberately does not pretend that the turn itself has been solved. There is still no turn betting tree around the chance node, no turn counterfactual range propagation through actions, and no local turn resolving latency contract.

The next R6 milestone is therefore a **real turn betting + river continuation microgame** whose terminal continuation enters the exact public river chance primitive implemented here. Only after that gate is validated should R6 advance to flop+turn+river composition.

R6 remains **IN PROGRESS**.
