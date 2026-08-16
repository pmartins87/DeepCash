# R5 alternating external-sampling LCFR — precommit 2026-08-16

Primary source: Brown & Sandholm, *Solving Imperfect-Information Games via Discounted Regret Minimization*, arXiv:1809.04040.

The accepted first DeepCash external-sampling control deliberately used a simultaneous two-traverser snapshot to isolate a simple deterministic MCCFR baseline. The literature audit now requires a second, more faithful sampled control: **alternating player updates**, with Linear CFR weighting applied to both regrets and output strategy.

This generation is frozen before numerical results are consumed.

## Frozen variants

### `ALT_ES_CFR_UNIFORM`

- external sampling: chance and opponent actions sampled; traverser's actions enumerated;
- P0 traversal/update followed immediately by P1 traversal/update under the refreshed profile;
- ordinary cumulative regrets;
- uniform average-strategy contribution.

### `ALT_ES_CFR_LINEAR_AVG`

- same alternating external sampling and ordinary regrets;
- output average weighted by global iteration `t`;
- isolates average weighting from regret weighting.

### `ALT_ES_LCFR`

- same alternating external sampling;
- instantaneous regret delta on iteration `t` receives weight `t`, giving cumulative weighted regret `sum_t t*r_t`;
- output average contribution also receives weight `t`;
- no RM+ clipping.

Weighted-regret accumulation is mathematically equivalent, up to a common scale factor irrelevant to regret matching, to LCFR's repeated `t/(t+1)` discount representation.

## Deliberate small-game average-strategy control

For this first exact river control, the traversing player's output average is accumulated **exactly from its own realization reach at every infoset**, rather than sampled only on visited opponent/chance paths. This removes average-strategy sampling noise so the comparison isolates regret-update/sampling behavior.

P0's average is accumulated immediately before P0's traversal. P1's average is accumulated after P0's regret refresh and immediately before P1's traversal.

## Frozen numerical battery

- four existing R3 control boards;
- 6 exact combos/player;
- phases 0.00 / 0.27;
- pot 100, stack 400, SPR 4;
- fixed 25% / 50% / 100% action family;
- seeds `11,29,101,20260816`;
- checkpoints `1000,5000,20000`;
- exact best-response evaluation.

## Correctness / determinism gates

- same seed -> bit-identical state/result;
- staged training == monolithic training;
- JSON checkpoint roundtrip preserves PRNG and exact future path;
- P0 half-step changes only P0 regrets;
- P1 traversal uses a profile refreshed after P0's update;
- LCFR weighted-regret update has a direct analytical fixture (`R_t = sum k*r_k`);
- uniform / linear-average / LCFR variants remain materially distinct;
- wrong game/variant and non-finite state fail closed.

## Acceptance discipline

The paper reports that the CFR+ modifications do not automatically improve MCCFR, whereas LCFR-style discounting does in its HUNL sampled experiments. DeepCash will not assume that carries to our abstraction: every board/seed remains in the paired evidence.

If LCFR wins, it becomes a sampled-control candidate, not the production solver. The later production architecture still needs large-support scaling, R4 representation integration, and target-Ryzen equal-compute tests.

`R5 alternating external LCFR = PRECOMMITTED`

`R5 production solver = NOT SELECTED`
