# R5 VR-MCCFR no-private-leak integration — precommit 2026-08-16

This gate is frozen before any solver-level `INFOSET_EXACT` result is accepted. It may be executed only after the standalone no-leak baseline oracle passes.

## Frozen modes

The external-sampling VR traversal will expose three explicitly distinct baseline modes:

1. `ZERO`
   - all baselines zero;
   - must remain bit-identical to the accepted ordinary external sampler.

2. `INFOSET_EXACT`
   - baseline vector computed only from the traverser's exact private combo plus public node/history and current policy/range model;
   - integrates exactly over every compatible hidden opponent combo;
   - realized opponent private cards are **not** an argument to the baseline API;
   - expensive correctness/variance oracle, not production eligible on cost grounds.

3. `PERFECT_HISTORY`
   - privileged hidden-history continuation values;
   - already accepted as a zero-residual lower-bound oracle;
   - permanently forbidden from production because it sees hidden opponent state.

## Frozen traversal contract

At a non-traverser node:

- sample the public action from the current non-traverser strategy exactly as ordinary external sampling does;
- evaluate the sampled actual-history child recursively;
- obtain the selected baseline vector for the current mode;
- apply the accepted baseline-enhanced action-value estimator with `q = sigma`;
- return that baseline-enhanced node value to the traverser's regret recursion.

At traverser nodes, enumerate all traverser actions exactly as ordinary external sampling does.

Private-deal chance sampling and PRNG order remain unchanged.

## Mandatory correctness gates

- `ZERO` remains bit-identical to ordinary external sampling for same seed/checkpoint;
- `INFOSET_EXACT` baseline call has no realized-opponent-hand parameter;
- swapping only the realized opponent private combo while preserving the traverser's infoset cannot change the baseline vector;
- conditional action-sampling unbiasedness is inherited from and rechecked against the accepted estimator algebra;
- checkpoint/resume determinism remains exact;
- perfect-history mode stays explicitly distinct and privileged;
- no mode may silently fall back to a different baseline on zero posterior mass.

## Frozen numerical oracle battery after correctness

Only if integration tests pass:

- four existing river control boards;
- 6 exact combos/player;
- phases 0.00 / 0.27;
- pot 100, stack 400 / SPR 4;
- fixed 25% / 50% / 100% action family;
- seeds `11,29,101,20260816`;
- checkpoints `1000,5000`;
- exact best-response evaluation;
- compare `ZERO`, `INFOSET_EXACT`, `PERFECT_HISTORY`.

Interpretation must report both strategic variance/error and wall-clock. `INFOSET_EXACT` is expected to be expensive because it enumerates hidden-opponent support; its role is to define the production no-leak baseline target, not to win runtime.

A cheap online tabular/bootstrapped baseline may be designed only after this oracle integration is accepted.

`R5 VR-MCCFR no-leak integration = PRECOMMITTED`

`R5 production baseline = NOT SELECTED`
