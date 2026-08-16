# R4 best-response methodology correction — 2026-08-16

Status: **methodology corrected before finalist selection or held-out consumption**.

## What the first development evaluator did

The representation solver trained exact chance/payoffs/actions while aliasing only private infosets. Candidate-vs-reference comparisons were one-sided: one player bucketed, the other exact.

However, after expanding the candidate policy back to exact combo keys, `representation_result_from_state()` evaluated both best responses with the unrestricted exact-combo BR oracle.

For a one-sided bucketed game this produced a conservative but unnecessarily wide game-value interval:

- if P0 was bucketed, unrestricted P0 BR was stronger than the BR actually available to P0 in that game;
- if P1 was bucketed, unrestricted P1 BR was stronger than the BR actually available to P1.

Therefore the old interval mixed two effects:

1. solver non-convergence inside the abstract game;
2. the strategic value of information removed by the representation itself.

The bounds were conservative, but labeling the entire width as convergence uncertainty was misleading and could prevent a clean Pareto decision even after more CFR iterations.

## Correct evaluator

`deepcash_core/river_representation_br.py` now computes exact **bucket-constrained best responses**.

For each player and each private bucket:

- every exact hand mapped to that bucket must share one pure root/response action pattern;
- the oracle enumerates all legal pure patterns for the bucket;
- expected value is aggregated over all compatible exact chance deals belonging to that bucket;
- each bucket is optimized independently;
- exact card removal, payoffs and the opponent policy remain unchanged.

This is exact for the current tractable one-bet river representation game.

With exact one-hand-per-bucket maps, the new oracle must reproduce the original unrestricted exact BR bit-for-bit/tolerance. With merged buckets, the restricted player's BR can never be stronger than the unrestricted exact BR.

## Consequence for earlier R4 artifacts

Runs `31964142661` and `31975623597` remain valid evidence for:

- deterministic bucket construction;
- CFR training paths;
- compression ratios;
- training-time observations;
- exact-card/payoff/action separation;
- suit/card-order invariance gates.

Their reported `max_value_interval_width_per_pot` and restriction-loss upper bounds are **superseded for representation selection**, because they used the looser unrestricted-BR interval.

No held-out R4 board has been consumed, so the correction costs compute but does not contaminate validation.

## Required replay

The original frozen R4 development coordinates are replayed unchanged with bucket-constrained BRs before any deterministic finalist is selected. The existing held-out-v1 generation remains unopened.
