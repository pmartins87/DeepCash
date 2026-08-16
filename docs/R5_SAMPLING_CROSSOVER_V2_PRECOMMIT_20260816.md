# R5 full-tree vs external-sampling scaling crossover v2 — precommit 2026-08-16

v2 is a **semantic-coordinate replay** of invalidated v1 after removing the hot-loop compatible-deal enumeration from external sampling. No candidate, board, range phase or checkpoint was changed after seeing v1.

## Frozen coordinates — identical to v1

Boards:

- `A_high_dry`;
- `four_straight`.

Geometry:

- pot 100;
- stack 400 / SPR 4;
- 25% / 50% / 100% river bet family;
- phases 0.00 / 0.27;
- exact combos/player `6,12,24,48`.

Full-tree comparator:

- synchronous `CFR_PLUS_LINEAR`;
- checkpoints `100,400`.

External-sampling comparator:

- `ES_CFR_PLUS_LINEAR`;
- seeds `29,101`;
- checkpoints `20000,80000`.

## New implementation condition

The only intended change is the chance-deal hot path:

- exact compatible deal support/CDF constructed once per `advance` batch;
- repeated chance draw by binary search;
- deterministic regression proves 10,000 optimized draws exactly match the legacy sampled-deal sequence and final PRNG state.

Therefore v2 must also act as a semantic replay check: for fixed board/range/seed/checkpoint, external-sampling exploitability and policy outputs should match v1 up to serialization/FP identity expected from the unchanged sample sequence, while training time should no longer include repeated O(N^2) deal-support rebuilding.

## Acceptance discipline

- if strategic outputs materially differ from v1, investigate before timing interpretation;
- compare scaling trend, not only one endpoint;
- hosted timing remains development evidence only;
- the full-tree comparator is still old synchronous CFR+ and therefore answers traversal scaling, not current best-exact-solver ranking;
- physical Ryzen equal-compute remains mandatory later.

`R5 sampling crossover v2 = PRECOMMITTED`
