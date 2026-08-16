# R5 sampling crossover v1 — invalidated for scaling/timing 2026-08-16

Workflow run `31965398733` completed successfully and produced internally consistent strategic outputs. It is **not accepted as a sampling-scaling benchmark**.

## Root cause found before acceptance

A post-run source audit found an avoidable O(|range0|*|range1|) operation inside every sampled chance event:

`_sample_deal(spec, rng)` rebuilt `_valid_deals(spec)` and rebuilt its weight vector on every call.

Therefore the measured external-sampling wall clock contained repeated full compatible-deal-support enumeration before the actual sampled CFR traversal. As range support grew from 6 to 48 combos/player, the benchmark increasingly measured this harness/implementation inefficiency rather than the asymptotic advantage external sampling was intended to test.

The strategic policy/regret sequence itself is not considered corrupted: the optimized sampler uses the identical compatible-deal order, cumulative weights, one RNG uniform draw per chance sample and strict cumulative-boundary semantics. A 10,000-draw deterministic regression proves the optimized sampler returns the same deal sequence and final PRNG state as the old linear selector on a weighted fixture.

## Correction

`deepcash_core.river_external_sampling.WeightedDealSampler` now:

- builds the exact compatible weighted deal support once per training batch;
- stores cumulative masses once;
- uses binary search for repeated weighted chance draws;
- preserves the original chance distribution and RNG draw count.

`advance_external_sampling` constructs that immutable sampler once before the iteration loop.

## Consequence

The v1 artifact remains audit history but its timing/crossover conclusion is rejected. In particular, the fact that no crossover appeared by 48 combos/player cannot be used as evidence against external sampling because the sampled implementation was paying a hidden full-support enumeration cost every iteration.

A new v2 generation must rerun the same frozen game coordinates with the optimized sampler. Candidate/checkpoint geometry should remain unchanged so v1/v2 strategic identity and timing correction can be diagnosed directly.

`R5 sampling crossover v1 timing = INVALIDATED`

`R5 production solver = NOT SELECTED`
