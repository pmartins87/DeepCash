# R5 full-tree vs external-sampling scaling crossover — precommit 2026-08-16

The first R5 sampled control showed a clear negative result on a tiny 6x6 exact range support: full-tree CFR+ was both faster and much more converged. This generation is frozen before measuring where that conclusion begins to change as the exact chance/range support grows.

## Question

At what exact range-support scale does `ES_CFR_PLUS_LINEAR` begin to buy enough throughput to compensate for its sampling variance relative to synchronous full-tree `CFR_PLUS_LINEAR`?

This is a **development scaling experiment**, not a production solver selection.

## Frozen games

Boards:

- `A_high_dry`;
- `four_straight`.

Shared geometry:

- pot 100;
- stack 400 / SPR 4;
- fixed 25% / 50% / 100% river bet family;
- deterministic quantile ranges;
- phases 0.00 / 0.27;
- exact card removal and exact best-response evaluation.

Exact combos per player:

`6, 12, 24, 48`

The larger range supports remain exact; no private-state abstraction is introduced in this R5 control.

## Frozen algorithms/work

### Full-tree control

`CFR_PLUS_LINEAR`

Checkpoints:

`100, 400`

### External-sampling control

`ES_CFR_PLUS_LINEAR`

Seeds:

`29, 101`

Checkpoints:

`20000, 80000`

The asymmetric iteration counts are intentional: an exact full-tree iteration and an external-sampling iteration do not represent equal work. The experiment records real training seconds and terminal visits rather than pretending iteration counts are comparable.

## Measurements

For every board/range-size/checkpoint:

- exact compatible deal count;
- exploitability per pot;
- policy EV and BR interval;
- cumulative training seconds;
- exact-BR evaluation seconds;
- external sampled terminal visits;
- seed mean/worst/dispersion for sampling.

Postprocessing may compare points by observed wall-clock neighborhood, but it may not invent a production threshold after seeing data.

## Interpretation discipline

- hosted GitHub runners measure algorithmic scaling trends only;
- final worker/batch choice still requires the physical Ryzen 9;
- if no crossover appears by 48 combos/player, preserve that result and expand through a new precommitted range generation rather than assuming sampling will eventually win;
- if sampling wins throughput but remains strategically much noisier, both facts must be retained;
- neural approximation remains downstream of trustworthy sampled traversal.

`R5 sampling crossover = PRECOMMITTED`

`R5 production solver = NOT SELECTED`
