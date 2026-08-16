# R5 VR-MCCFR integration oracle v1 — accepted 2026-08-16

This gate accepts the first solver-level integration of the VR-MCCFR baseline estimator. It is still an **oracle/correctness stage**, not a production baseline benchmark.

## Workflow evidence

Run `31968834501`: **PASS**.

The gate combines:

- the already accepted baseline-enhanced estimator algebra;
- external-sampling traversal integration;
- deterministic checkpoint/RNG semantics inherited from the accepted external sampler.

## Zero-baseline equivalence

`VRBaselineMode.ZERO` uses the baseline-enhanced action-value formula with every baseline equal to zero.

For both accepted external-sampling variants, and for staged as well as monolithic training, the zero-baseline VR traversal is **bit-identical** to the ordinary external sampler for the same seed:

- same private-deal sequence;
- same opponent-action RNG sequence;
- same regret tables;
- same average-strategy sums;
- same terminal-visit accounting;
- same final PRNG state.

This proves the VR integration itself does not silently change MCCFR when the control variate is disabled.

## Perfect-history lower-bound oracle

`VRBaselineMode.PERFECT_HISTORY` deliberately uses the exact hidden-history continuation value of every action at a sampled opponent node as its baseline.

At a fixed private history, the tests show:

- ordinary zero-baseline opponent-action sampling returns multiple values across RNG seeds;
- the perfect-history baseline returns **exactly one value across every tested sampled action/seed**, demonstrating the source estimator's zero-residual limit;
- full training under the perfect-history oracle is materially different from zero-baseline training, as expected.

The oracle also expands more hidden-history continuations and is therefore explicitly **not production eligible**. It exists only to establish the variance-reduction ceiling and validate the implementation.

## Next VR gate

Production relevance now depends on a baseline that does not see opponent private information. The next generation must:

1. define an augmented-infoset baseline keyed only by the traverser's private information plus public/action history;
2. prove that two histories indistinguishable to the traverser receive the same baseline even if the opponent's hidden hand differs;
3. prove the resulting sampled regret estimator remains unbiased by exact enumeration on small river fixtures;
4. compare variance against zero baseline and the perfect-history lower bound;
5. only after correctness, benchmark a cheap tabular/bootstrapped online baseline per wall-clock.

`R5 VR-MCCFR estimator algebra = PASS`

`R5 VR-MCCFR zero-baseline integration = PASS`

`R5 VR-MCCFR perfect-history lower-bound oracle = PASS`

`R5 production no-leak baseline = NOT YET IMPLEMENTED`

`READY FOR TABLES = NO`
