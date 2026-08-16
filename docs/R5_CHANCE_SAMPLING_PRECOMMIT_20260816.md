# R5 chance-sampled CFR control — precommit 2026-08-16

The first external-sampling generation mixed two sources of Monte Carlo variance: sampled private chance and sampled non-traverser actions. Before attributing its slower convergence to sampling in general, R5 will isolate **chance sampling alone**.

This precommit is frozen before numerical chance-sampling results are accepted.

## Frozen variants

1. `CS_CFR_LINEAR`
   - sample one exact compatible private deal per global iteration from the true weighted chance distribution;
   - enumerate the full action tree for that sampled deal;
   - ordinary cumulative regrets;
   - linear average strategy.

2. `CS_CFR_PLUS_LINEAR`
   - same chance sampling and full action enumeration;
   - non-negative regret clipping after every global iteration;
   - linear average strategy.

For this small-game control, average strategy is accumulated exactly from each player's own realization reach across all infosets, just as in the accepted external-sampling control. Therefore the experiment isolates regret-update variance rather than conflating it with sampled average-strategy estimation.

## Determinism / checkpoint contract

Checkpoint must preserve:

- exact game signature;
- variant;
- seed;
- iterations;
- sampled terminal visits;
- regret/strategy tables;
- complete PRNG state.

Mandatory tests:

- same seed exact identity;
- staged == monolithic;
- JSON roundtrip preserves exact future path;
- wrong game/variant fails closed;
- non-finite corruption fails closed.

## Frozen numerical battery

Same game family as R5 external-sampling dev v1:

- four existing control boards;
- 6 exact combos/player;
- pot 100, stack 400, SPR 4;
- 25% / 50% / 100% river bet family;
- range phases 0.00 / 0.27;
- exact best-response evaluation.

Seeds:

`11, 29, 101, 20260816`

Checkpoints:

`1000, 5000, 20000`

## Required interpretation

Compare chance sampling against:

- exact full-tree `CFR_PLUS_LINEAR`;
- external-sampling `ES_CFR_PLUS_LINEAR`.

If chance sampling converges materially faster than external sampling at similar sampled iteration cost, the additional variance is attributable largely to opponent-action sampling and R5 should investigate hybrid/public-state traversal before moving directly to higher-variance outcome sampling.

If chance sampling does not improve, preserve that negative result.

Hosted CI remains development timing only; physical Ryzen evidence is mandatory before production selection.

`R5 chance sampling = PRECOMMITTED`

`R5 production solver = NOT SELECTED`
