# R5 alternating CFR+ / DCFR development v2 — accepted 2026-08-16

This document accepts only the **corrected v2** alternating-update generation. The earlier v1 workflow was invalidated before any numerical result was consumed because its average-strategy timing was not faithful to alternating CFR semantics.

## Correctness / audit trail

Corrected precommit:

- `docs/R5_ALTERNATING_DCFR_PRECOMMIT_V2_20260816.md`.

Corrected implementation:

- `deepcash_core/river_alternating_dcfr.py`.

The accepted player-local alternating order is:

1. accumulate P0 average under the current profile;
2. traverse/update P0 regrets;
3. refresh the profile;
4. accumulate P1 average under the refreshed profile;
5. traverse/update P1 regrets.

This prevents a synthetic post-both-updates average from contaminating the comparison.

General CI for the corrected generation:

- run `31966030259` on commit `a68931034847aa474c39fd845922cc3c4c3335cd`: **PASS**.

The tests cover:

- staged training == monolithic training for every alternating variant;
- JSON checkpoint roundtrip with exact future-path equivalence;
- player-local average accumulation changes only the requested player's sums;
- P1 average is accumulated after P0's refresh but before P1's own refresh;
- P0 half-step cannot mutate P1 regrets;
- direct DCFR alpha/beta/gamma factor fixtures;
- positive and negative DCFR regrets receive the intended distinct discount factors;
- linear and quadratic output weighting are materially distinct;
- wrong variant/game and non-finite checkpoint state fail closed.

The obsolete v1 workflow is retained only as audit history and now refuses manual numerical generation.

## Numerical gate

Corrected workflow:

- `.github/workflows/r5-alternating-dcfr-dev-v2.yml`;
- run `31966030278`: **PASS**;
- source commit `a68931034847aa474c39fd845922cc3c4c3335cd`;
- artifact ID `9268529202`;
- artifact SHA-256 `5c000f61a9d14722f927851942e6b44b8311f5d7f2d575c5fd1e5b761a97643b`.

Frozen exact development battery:

- four R3 control river boards;
- 6 exact combos/player;
- phases 0.00 / 0.27;
- pot 100;
- stack 400 / SPR 4;
- fixed 25% / 50% / 100% action family;
- checkpoints 100 / 400 / 1200;
- exact compatible chance tree and exact best responses.

Same-run algorithms:

- existing synchronous `SYNC_CFR_PLUS_LINEAR`;
- `ALT_CFR_PLUS_LINEAR`;
- `ALT_CFR_PLUS_QUADRATIC`;
- `ALT_DCFR_150_0_2`;
- `ALT_DCFR_150_050_2`.

## Aggregate exploitability per pot

| checkpoint | synchronous CFR+ linear | alternating CFR+ linear | alternating CFR+ quadratic | DCFR 1.5/0/2 | DCFR 1.5/0.5/2 |
|---:|---:|---:|---:|---:|---:|
| 100 | 0.00688802 | 0.00028329 | 0.00019588 | **0.00011405** | 0.00028404 |
| 400 | 0.00155223 | 0.00003449 | 0.00003076 | **0.00001392** | 0.00003042 |
| 1200 | 0.00039815 | 0.00000946 | 0.00001077 | **0.00000587** | 0.00001071 |

Worst-board exploitability at checkpoint 1200:

| algorithm | worst exploitability/pot |
|---|---:|
| synchronous CFR+ linear | 0.00045542 |
| alternating CFR+ linear | 0.00002445 |
| alternating CFR+ quadratic | 0.00002870 |
| **DCFR 1.5/0/2** | **0.00000767** |
| DCFR 1.5/0.5/2 | 0.00002722 |

## Wall-clock context

Mean cumulative hosted-run training time at checkpoint 1200:

- synchronous CFR+ linear: ~2.845 s;
- alternating CFR+ linear: ~5.762 s;
- alternating CFR+ quadratic: ~5.774 s;
- DCFR 1.5/0/2: ~5.784 s;
- DCFR 1.5/0.5/2: ~5.769 s.

An alternating global iteration deliberately performs two exact player regret traversals, so roughly 2x synchronous per-iteration cost is expected.

The strategic gain is much larger than that local cost. At equal checkpoint 1200, `ALT_DCFR_150_0_2` has about **67.9x lower mean exploitability** than synchronous CFR+ linear for about **2.03x** the hosted training time.

Even a stricter cross-check favors the alternating DCFR control: its 400-iteration point averages about `1.392e-05` exploitability/pot in ~1.926 s, while synchronous CFR+ at 1200 averages about `3.982e-04` in ~2.845 s. Thus the 400-iteration DCFR point is about **28.6x more converged while also using less hosted wall-clock** in this exact microgame.

Hosted timing remains development evidence rather than target-Ryzen evidence.

## Per-board stability

`ALT_DCFR_150_0_2` does not win only by one favorable board. At checkpoint 1200 its exploitability/pot is approximately:

- A-high dry: `0.00000184`;
- paired: `0.00000669`;
- four-straight: `0.00000727`;
- four-flush: `0.00000767`.

The beta=0.5 variant is materially less stable on the current controls, especially the four-flush board, despite occasionally winning an individual board. The literature-default beta=0 variant therefore has the cleaner current evidence.

## Accepted interpretation

The first synchronous battery understated how much the update schedule matters. The corrected evidence changes the exact-control ranking materially:

- alternating updates are dramatically stronger than the synchronous control on this river battery;
- quadratic output weighting alone does not beat alternating linear CFR+ consistently;
- **`ALT_DCFR_150_0_2` is now the leading exact tabular development control**;
- beta=0.5 is preserved as a future pruning-compatible candidate, but it is not the current leader;
- the previous synchronous `CFR_PLUS_LINEAR` result remains valid as a narrower synchronous baseline rather than being erased.

This still does **not** select the production 6-max solver. R5 must now compare scalable sampled/hybrid traversal against the stronger alternating/DCFR oracle, and later evaluate newer discounted/predictive variants under the same fail-closed methodology.

`R5 = IN PROGRESS`

`R5 leading exact tabular control = ALT_DCFR_150_0_2`

`R5 production solver = NOT SELECTED`

`READY FOR TABLES = NO`
