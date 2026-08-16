# R5 paper-equation DCFR / Hyperparameter Schedules v1 — accepted 2026-08-16

This document accepts the precommitted **Equation-2/3 recurrence implementation** as a DeepCash development control, including its negative result. It does not overwrite the previously accepted OpenSpiel-style post-update discounted control.

## Specification audit

Primary source: Zhang, McAleer & Sandholm, *Faster Game Solving via Hyperparameter Schedules* (AAAI 2026 / arXiv:2404.09097v2).

The source equations specify:

- positive old cumulative regret discounted by `t^alpha / (t^alpha + 1)`, then new instantaneous regret added;
- negative/non-positive old cumulative regret discounted analogously with beta;
- old cumulative strategy discounted by `(t/(t+1))^gamma`, then the current reach-weighted strategy contribution added;
- HS schedules `alpha(t)=1+3t/n`, `beta(t)=-1-2t/n`, and gamma schedules `30-5t/n` / `15-5t/n`.

DeepCash v1 freezes the implementation coordinate explicitly: processed global iteration `k=1..n` uses `t=k` in those factors/schedules. This is a named implementation contract, not an attempt to make the historical OpenSpiel implementation disappear. Any later alternate indexing convention must receive its own precommit/generation.

The prior semantics audit remains authoritative: `docs/R5_DCFR_SEMANTICS_AUDIT_20260816.md`.

## Correctness gate

General CI run `31966914597` on commit `dd510a33e34ce92dfe24960a8cdd6d1bac152767`: **PASS**.

Tests cover:

- direct old-regret-discount-then-add recurrence and explicit distinction from post-update discounting;
- direct average recurrence `old * factor + current contribution`;
- exact HS alpha/beta/gamma coordinates at beginning/middle/end of the frozen horizon;
- staged == monolithic training;
- JSON checkpoint future-path equivalence;
- frozen-horizon mismatch/overrun fail closed;
- player-half-step isolation;
- non-finite checkpoint rejection.

## Numerical gate

Workflow run `31966914580`: **PASS**.

Artifact:

- ID `9268760347`;
- SHA-256 `a05440224844d6515944b89428aeccae0fe64fb0c63958c737a316be03887976`.

Frozen battery:

- four exact R3 control river boards;
- 6 exact combos/player;
- phases 0.00 / 0.27;
- pot 100, stack 400 / SPR 4;
- 25% / 50% / 100% action family;
- frozen solve horizon `n=1200`;
- checkpoints 100 / 400 / 1200;
- exact compatible-card chance tree and exact best responses.

Same-run algorithms:

- corrected `ALT_CFR_PLUS_LINEAR`;
- accepted historical `OPEN_SPIEL_STYLE_POST_DCFR_150_0_2`;
- `PAPER_DCFR_150_0_2` (Equation-2/3 old-discount-then-add recurrence);
- `HS_DCFR_30`;
- `HS_DCFR_15`.

## Aggregate exploitability per pot

| checkpoint | ALT CFR+ linear mean / worst | post-update DCFR 1.5/0/2 mean / worst | equation DCFR 1.5/0/2 mean / worst | HS-DCFR(30) mean / worst | HS-DCFR(15) mean / worst |
|---:|---:|---:|---:|---:|---:|
| 100 | 0.00028329 / 0.00093476 | **0.00011405 / 0.00015787** | 0.00276968 / 0.00380632 | 0.00504216 / 0.00650196 | 0.00475760 / 0.00669334 |
| 400 | 0.00003449 / 0.00008560 | **0.00001392 / 0.00001939** | 0.00278867 / 0.00381195 | 0.00333224 / 0.00577458 | 0.00315345 / 0.00464777 |
| 1200 | 0.00000946 / 0.00002445 | **0.00000587 / 0.00000767** | 0.00277609 / 0.00380888 | 0.00284574 / 0.00374350 | 0.00277798 / 0.00380822 |

Mean hosted training time at checkpoint 1200 was similar for all alternating full-tree variants (~5.56–5.91 seconds), so the strategic ranking is not explained by a major runtime disparity in this tiny control.

## Per-board endpoint sanity

At checkpoint 1200, the equation-recurrence families remained in the same broad `~0.002–0.004 pot` exploitability range on every board rather than failing because of one isolated texture:

- `PAPER_DCFR_150_0_2`: approximately 0.00197–0.00381;
- `HS_DCFR_30`: approximately 0.00210–0.00374;
- `HS_DCFR_15`: approximately 0.00195–0.00381.

By contrast, the accepted post-update discounted control remained around `1.8e-06` to `7.7e-06` per pot across the same four boards.

## Accepted negative result

The published HS schedules do **not** improve the DeepCash Equation-2/3 recurrence implementation on this exact river microgame. More strongly, the entire old-discount-then-add family in this generation is dramatically worse than both corrected alternating CFR+ and the historical post-update discounted control.

This is retained as real evidence rather than tuned away.

It does **not** establish that the AAAI method is generally weak. DeepCash is testing one exact implementation contract on a small, unusual poker microgame; the source paper reports broad gains on its own benchmark suite. The correct project conclusion is narrower:

- Hyperparameter schedules are **not promoted** into the current DeepCash exact-control shortlist from this generation;
- the implementation/update-order distinction is strategically enormous and must remain explicit in every future solver comparison;
- `OPEN_SPIEL_STYLE_POST_DCFR_150_0_2` remains the strongest exact tabular control tested so far;
- future predictive/discounted candidates must state their update and indexing semantics precisely instead of inheriting an ambiguous `DCFR` label.

## Next R5 implications

The highest-value R5 path is now:

1. finish exact-vs-sampled support crossover;
2. extend the accepted correlated-chance primitive to larger chance support;
3. implement variance-reduced MCCFR baselines, because measured sampled variance is a much clearer bottleneck than lack of another exact discount schedule;
4. keep modern predictive/optimistic methods in the registry, but only after their exact update semantics can be independently gated.

`R5 paper-equation DCFR / HS v1 = ACCEPTED NEGATIVE DEVELOPMENT EVIDENCE`

`R5 leading exact tabular control = OPEN_SPIEL_STYLE_POST_DCFR_150_0_2`

`R5 production solver = NOT SELECTED`

`READY FOR TABLES = NO`
