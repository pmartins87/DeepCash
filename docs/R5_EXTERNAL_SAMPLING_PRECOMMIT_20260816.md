# R5 deterministic external-sampling MCCFR — precommit 2026-08-16

This generation is frozen before any external-sampling numerical result is accepted.

The first R5 exact full-tree control established `CFR_PLUS_LINEAR` as the leading synchronous tabular control. The scalable 6-max problem cannot traverse full chance/opponent trees, so the next question is how much strategic convergence is retained when chance and opponent actions are sampled.

## Algorithm boundary

Implement two deterministic external-sampling variants on the same exact HU river game:

1. `ES_CFR_LINEAR`
   - external sampling of chance and non-traverser actions;
   - traverser's actions enumerated;
   - ordinary cumulative regrets;
   - linear average strategy.

2. `ES_CFR_PLUS_LINEAR`
   - same sampled traversal;
   - regrets clipped non-negative after each global iteration;
   - linear average strategy.

A global external-sampling iteration performs one traversal for P0 and one for P1 from a common pre-update strategy snapshot. Regret deltas from both traversals are applied only after both complete.

For this small river control, average-strategy reach is accumulated exactly from the player's own realization reach at every infoset. Chance/opponent paths remain sampled for regret updates. This deliberately removes average-strategy sampling noise from the first MCCFR correctness comparison; later scalable implementations may benchmark sampled averaging separately if its cost becomes material.

## Determinism / checkpoint contract

The checkpoint must contain:

- exact game signature;
- solver variant;
- completed global iterations;
- regret tables;
- average-strategy sums;
- full PRNG state;
- cumulative sampled terminal visits.

Mandatory tests:

- same seed -> bit-identical state/result;
- staged training -> bit-identical monolithic training;
- JSON checkpoint roundtrip -> bit-identical future path;
- wrong game/variant -> fail closed;
- corrupted/non-finite state -> fail closed.

## Frozen development battery

Use the same strategic game as R5 tabular development v1:

- four existing R3 control boards;
- pot 100;
- stack 400 / SPR 4;
- fixed 25% / 50% / 100% river bet family;
- 6 exact combos/player;
- range phases 0.00 / 0.27;
- exact card removal and exact terminal payoffs;
- exact best-response evaluation at checkpoints.

Frozen seeds:

`11, 29, 101, 20260816`

Frozen checkpoints:

`1000, 5000, 20000`

## Measurements

Per board / variant / seed / checkpoint record:

- exploitability per pot;
- BR0/BR1 and interval width;
- policy EV;
- cumulative training seconds;
- exact-BR evaluation seconds;
- sampled terminal visits;
- infosets/action slots.

Across seeds report mean/median/worst exploitability and dispersion. Do not choose a seed after seeing results.

Hosted-CI timing is development evidence only. The eventual decisive comparison remains equal wall-clock on the physical Ryzen 9.

## Acceptance discipline

The generation may establish a leading **sampled-control algorithm**, but cannot select the production solver. A sampled method must demonstrate both:

- credible convergence toward the exact-game solution across every control board and multiple frozen seeds;
- a plausible strategic-error-per-compute advantage over full-tree traversal.

If clipping harms sampled convergence, preserve that negative result. If seed variance is large, expand evidence through a new precommitted generation rather than selecting favorable seeds.

`R5 external sampling = PRECOMMITTED`

`R5 production solver = NOT SELECTED`
