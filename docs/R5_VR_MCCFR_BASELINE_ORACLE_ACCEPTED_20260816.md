# R5 VR-MCCFR baseline estimator oracle — accepted 2026-08-16

The first variance-reduction gate is accepted as a **mathematical/correctness oracle**, not as a production solver result.

Primary method source: Schmid et al., *Variance Reduction in Monte Carlo Counterfactual Regret Minimization for Extensive Form Games using Baselines*, arXiv:1809.03057.

## Accepted implementation

`deepcash_core/vr_mccfr_baseline.py` implements the baseline-enhanced sampled action-value estimator

`b(a) + I[a=a*]/q(a*) * (v_child(a*) - b(a*))`

and contracts it with an arbitrary target strategy `sigma` while enforcing absolute continuity against the sampling policy `q`.

## Gate

Workflow run `31968270149`: **PASS**.

The tests prove by exact finite enumeration:

- unbiasedness for arbitrary finite target policy, sampling policy, child values and baselines;
- off-policy importance correction when `q != sigma`;
- zero-baseline/on-policy equivalence to the ordinary sampled-node value;
- perfect-baseline zero variance — every possible sampled action returns the exact node value;
- fail-closed behavior for unsupported target mass, shape errors and invalid sampled actions.

This closes the estimator-algebra prerequisite before solver integration.

## Next integration gate

The next frozen sequence remains:

1. zero-baseline VR traversal must be bit-identical to ordinary external sampling for the same seed/checkpoint;
2. a perfect-history oracle baseline may then establish the zero-residual lower bound, but is explicitly forbidden from production because it may use hidden history;
3. only after that may a no-private-leak augmented-infoset baseline be designed and benchmarked;
4. online learned/tabular baselines come last.

`R5 VR-MCCFR baseline algebra = PASS`

`R5 VR-MCCFR production integration = NOT YET ACCEPTED`

`READY FOR TABLES = NO`
