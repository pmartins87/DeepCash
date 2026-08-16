# R5 paper-equation DCFR / Hyperparameter Schedules — precommit 2026-08-16

This generation is frozen before any numerical result from these variants is consumed.

Primary specification: Zhang, McAleer & Sandholm, *Faster Game Solving via Hyperparameter Schedules* (AAAI 2026 / arXiv:2404.09097v2).

## Why a new generation is necessary

The existing accepted DeepCash discounted control follows OpenSpiel's add-current-regret-then-discount implementation order. The 2026 HS paper writes DCFR Equation 2 explicitly as **discount old cumulative regret, then add the new instantaneous regret**. These are distinct algorithms and must not share one label.

This generation implements the paper equations directly and retains the old control only as a comparator.

## Frozen recurrence

For each player's alternating traversal at global iteration `t >= 1`:

1. current strategy is computed from the player's current cumulative regrets;
2. the player's cumulative average strategy is updated as
   `C <- C * (t/(t+1))^gamma_t + current_own_reach_policy`;
3. exact instantaneous counterfactual regret `r_t` is computed under that same current profile;
4. each old cumulative regret `R` is updated as
   - `R <- R * t^alpha_t/(t^alpha_t+1) + r_t` if old `R > 0`;
   - `R <- R * t^beta_t/(t^beta_t+1) + r_t` otherwise;
5. the strategy profile is refreshed before the other player's alternating traversal.

The sign used for discounting is the **old cumulative-regret sign**, before adding the new instantaneous regret.

## Frozen variants

### `PAPER_DCFR_150_0_2`

Constant parameters:

- alpha = 1.5;
- beta = 0;
- gamma = 2.

### `HS_DCFR_30`

At global iteration `t` with frozen total horizon `n`:

- alpha(t) = `1 + 3t/n`;
- beta(t) = `-1 - 2t/n`;
- gamma(t) = `30 - 5t/n`.

### `HS_DCFR_15`

Same alpha/beta schedules, with:

- gamma(t) = `15 - 5t/n`.

The total horizon is part of the checkpoint/game-solving contract. A state created for one horizon cannot be resumed under another.

## Frozen horizon and checkpoints

Development horizon:

`n = 1200`

Inspection checkpoints:

`100, 400, 1200`

HS parameters are always computed against the frozen `n=1200`, including at intermediate checkpoints. Checkpoint 100 is therefore the first 100 iterations of a precommitted 1200-iteration scheduled run, not a standalone n=100 schedule.

## Same-run comparators

The benchmark also includes, unchanged:

- `ALT_CFR_PLUS_LINEAR` from the corrected alternating CFR+ control;
- `OPEN_SPIEL_STYLE_POST_DCFR_150_0_2`, the accepted v2 add-then-discount control.

This makes the semantic effect of update order visible instead of silently replacing old evidence.

## Correctness gates

Before numerical interpretation:

- direct one-step fixture proves `old * discount(old_sign) + instantaneous`, and distinguishes it from `(old + instantaneous) * discount`;
- direct average fixture proves `old_average * discount + current_contribution`;
- alpha/beta/gamma schedule values are exact at beginning/middle/end coordinates;
- staged training == monolithic training for every paper-equation variant;
- JSON checkpoint roundtrip preserves exact future path;
- horizon mismatch fails closed;
- wrong game/variant and non-finite state fail closed;
- P0 half-step cannot mutate P1 regrets/averages;
- P1 traversal uses the profile refreshed after P0's update.

## Frozen numerical battery

Same exact river development family used by the previous R5 controls:

- four existing R3 control boards;
- 6 exact combos/player;
- range phases 0.00 / 0.27;
- pot 100;
- stack 400 / SPR 4;
- fixed 25% / 50% / 100% river action family;
- exact compatible-card chance tree;
- exact best-response evaluation.

## Acceptance discipline

The 2026 paper reports strong gains for HS methods across its benchmarks, including poker-like games, but DeepCash assumes no gain until its own exact held development battery confirms one.

No result here selects the production 6-max solver. A winner must later survive larger-support scaling, sampled/hybrid traversal, R4 representation integration and physical Ryzen equal-compute tests.

`R5 paper-equation DCFR / HS = PRECOMMITTED`

`R5 production solver = NOT SELECTED`
