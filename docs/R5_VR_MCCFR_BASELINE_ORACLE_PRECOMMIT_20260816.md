# R5 VR-MCCFR baseline estimator oracle — precommit 2026-08-16

Primary source: Schmid, Burch, Lanctot, Moravcik, Kadlecnik & Bowling, *Variance Reduction in Monte Carlo Counterfactual Regret Minimization (VR-MCCFR) for Extensive Form Games using Baselines*, arXiv:1809.03057.

This first VR generation is deliberately an **estimator-correctness oracle**, not a claim that a learned baseline is ready for production.

## Frozen mathematical primitive

For a sampled action `a*` drawn from sampling policy `q(a)` and a baseline `b(a)`, DeepCash will implement the baseline-enhanced sampled action value

`v_hat_b(a) = b(a) + I[a=a*] / q(a*) * (v_child(a*) - b(a*))`.

The corresponding node estimate under target strategy `sigma` is

`sum_a sigma(a) * v_hat_b(a)`.

This is the source paper's control-variate construction specialized to one sampled action node.

## Mandatory algebraic gates

Before solver integration:

1. **unbiasedness by exact enumeration** — for arbitrary finite `sigma`, `q`, true child values and baselines, enumerate every possible sampled action and prove the expectation of the baseline-enhanced node estimate equals `sum sigma(a) * true_value(a)`;
2. **zero-baseline equivalence** — when `b(a)=0` and `q=sigma`, the estimator must reduce exactly to the ordinary on-policy sampled-node value;
3. **perfect-baseline zero variance** — when `b(a)=true_value(a)` for every action, every possible sampled action must return the exact node value;
4. **off-policy importance correction** — unbiasedness must still hold when `q != sigma`, provided every target-positive action has positive sampling probability;
5. invalid probability/support/non-finite inputs fail closed.

## Integration sequence frozen before results

After the algebraic oracle passes:

A. integrate a **zero-baseline** version into a copied external-sampling traversal and prove bit-identical regret/policy/checkpoint results to the accepted ordinary external sampler for the same seed;

B. integrate a **perfect-history oracle baseline** only as a variance lower-bound test. This oracle may use full hidden history and is explicitly forbidden from becoming a production policy input; its only purpose is to prove that the implementation can reach the paper's zero-residual limit;

C. only then introduce a **no-private-leak infoset/augmented-infoset baseline**, indexed exclusively by information available to the traverser plus public history;

D. only after the no-leak estimator is proved unbiased may an online learned/tabular baseline be benchmarked.

## Why this gate matters now

DeepCash has already measured that sampled variance, especially opponent-action sampling, is a major convergence cost. Correlated chance allocation reduced chance-sampling error substantially, but it does not solve opponent-action variance. VR-MCCFR directly targets that remaining source.

No timing/strategic claim is allowed from the oracle-baseline phase. The production question is whether a cheap no-leak baseline reduces enough variance per Ryzen CPU-hour to beat simpler sampled traversal.

`R5 VR-MCCFR baseline oracle = PRECOMMITTED`

`R5 production solver = NOT SELECTED`
