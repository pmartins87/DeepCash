# R4 development selection precommit — 2026-08-16

Status: **FROZEN BEFORE THE FIRST R4 NUMERICAL DEVELOPMENT BATTERY**.

This document defines how the first deterministic private-state representation generation will be interpreted. It is deliberately frozen before the workflow that generates the development numbers, so a visually attractive result cannot change the ranking rule after the fact.

## Scope

Generation entering the first R4 development battery:

- `category`
- `strength4`
- `equity4`
- `equity8`
- `category_equity4`
- `equity4_blocker2`
- `equity8_blocker2`

The exact-combo map is the common reference/control and is not a compression candidate.

All cards, chance/card removal, payoffs, pot/stack geometry and action branches remain exact. Only private infoset identity is aliased.

## Development cells

Board set: `R4_REPRESENTATION_DEV_BOARDS`, which contains only already-seen development controls and no R3 or R4 unseen board.

Frozen first battery:

- all four current development board families;
- two deterministic range phase pairs:
  - A: P0 `0.00`, P1 `0.27`;
  - B: P0 `0.11`, P1 `0.54`;
- 6 exact combos per player;
- pot `100`;
- SPR `1`, `2`, `4` via stacks `100`, `200`, `400`;
- minimum bet `20`;
- rich one-bet reference from `ONE_BET_REFERENCE_FRACTIONS`;
- CFR+ checkpoints `100`, `400`, `1200`.

This is a development battery, not final evidence.

## Mandatory validity gates

A candidate/cell result is usable only if:

1. exact-combo reference solves and exact-BR interval ordering is valid;
2. candidate P0-only and P1-only states are evaluated in the same exact chance/action/payoff game;
3. candidate policies are expanded to exact combos before best response;
4. no checkpoint regression indicates broken staged/resumable semantics;
5. all existing unit/metamorphic tests pass.

A candidate is not rewarded for merely making its own compressed game easier to solve.

## Frozen ranking fields

For the **largest completed checkpoint shared by every candidate in every development cell**, compute for each candidate:

1. `worst_upper`: maximum `worst_loss_upper_per_pot` across all cells;
2. `mean_upper`: arithmetic mean `worst_loss_upper_per_pot` across all cells;
3. `p90_upper`: 90th percentile of `worst_loss_upper_per_pot` across cells;
4. `worst_interval`: maximum `max_value_interval_width_per_pot` across cells;
5. `mean_compression`: mean `bucket_compression_ratio`;
6. `mean_joint_infoset_ratio`: mean `joint_infosets / reference_infosets`;
7. `mean_joint_action_slot_ratio`: mean `joint_action_slots / reference_action_slots`;
8. `mean_joint_train_seconds`: mean cumulative joint candidate training time.

The development workflow may report additional diagnostics, but these fields are the precommitted decision coordinates.

## Pareto rule

Do not choose one winner by a single scalar score.

A candidate is development-dominated if another candidate is no worse in both:

- strategic loss: `worst_upper` and `mean_upper`;
- structural cost: `mean_joint_action_slot_ratio` and `mean_compression`;

and is strictly better in at least one of those four coordinates.

Only non-dominated candidates may become R4 deterministic finalists.

## Complexity preference inside unresolved strategic ties

If two non-dominated candidates have strategic differences smaller than the larger candidate's unresolved exact-BR interval envelope, the simpler candidate is preferred **for development finalist status**, in this order:

1. lower `mean_joint_action_slot_ratio`;
2. lower `mean_compression`;
3. lower `mean_joint_train_seconds`;
4. lexical candidate name only as a deterministic final tie-breaker.

This rule is not a claim that the simpler representation is truly stronger. It prevents us from paying permanent state-space cost for a gain we have not resolved statistically/computationally.

## Finalist count

Carry at most **three deterministic finalists** into the next R4 development stage. If the Pareto frontier contains more than three, apply the unresolved-tie complexity preference above until three remain.

The exact-combo control remains present in all future experiments regardless of finalist count.

## What development results are allowed to change

After inspecting development results we may:

- tighten convergence on difficult cells;
- add representation-level suit/canonical metamorphic tests;
- design counterfactual-value clustering or learned candidates;
- alter bucket counts or feature combinations for a **new generation**.

But a new candidate designed after seeing these development numbers must be labeled as a new generation. If it is designed after any R4 held-out-v1 result has been inspected, it cannot use held-out-v1 as unseen evidence.

## Held-out firewall

`R4_REPRESENTATION_HELDOUT_V1_BOARDS` remains untouched during this development stage.

The first R4 held-out workflow may run only after:

1. this development procedure is frozen — **done by this file**;
2. development results are complete and inspected;
3. deterministic finalists/new-generation candidates are explicitly recorded;
4. representation-level global suit-permutation tests pass for the candidates entering held-out.

Current state after this commit:

`R4 = IN PROGRESS`

`R4 development numerical evidence = NOT RUN`

`R4 heldout_v1 = PRECOMMITTED / NOT RUN`

`READY FOR TABLES = NO`
