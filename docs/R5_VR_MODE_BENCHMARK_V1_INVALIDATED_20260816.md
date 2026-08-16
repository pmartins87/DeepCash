# R5 VR mode benchmark v1 — INVALIDATED 2026-08-16

Run `31975686749` completed mechanically and produced artifact `9270998384`, SHA-256 `319120cb9f5d54c62d2954b9ed6c5e470b65b8a893764ff6eb0922035678f695`.

The artifact is **not accepted as a three-mode strategic comparison**.

## Symptom

At the frozen 2000-iteration battery, `PERFECT_HISTORY` produced much worse exploitability than both `ZERO` and `INFOSET_EXACT`, contradicting its intended role as a privileged variance-lower-bound oracle.

## Root cause

At a non-traverser node, the first implementation built the privileged baseline vector with:

```python
exact_children = tuple(descend(action) for action in actions)
```

`descend()` is the training traversal. When a counterfactual opponent action reached a traverser node, it updated `regret_delta` and terminal counters. Therefore the oracle evaluated unsampled opponent branches **with training side effects**. It was not merely a control variate; it contaminated the external-sampling update with counterfactual regret mutations.

The previous fixed-response-node variance test did not expose this because those child actions were already terminal.

## Correction

`PERFECT_HISTORY` now:

1. traverses exactly one sampled opponent action through the stateful MCCFR path;
2. evaluates all counterfactual baseline children with a pure fixed-deal policy evaluator;
3. does not mutate regret deltas, strategy sums, counters or PRNG state while computing unsampled baselines.

A new regression starts at a non-traverser node with several non-terminal actions and requires `ZERO` and `PERFECT_HISTORY`, under the same seed and policy, to leave **identical descendant regret deltas and terminal counters** on the sampled path. Only the returned control-variate value may differ.

## Evidence status

- `ZERO` results in v1 remain useful as the ordinary external-sampling control;
- the legal `INFOSET_EXACT` implementation remains separately protected by its no-private-leak and checkpoint-determinism gates;
- no conclusion about the relative performance of `PERFECT_HISTORY`, or the fraction of variance closed by `INFOSET_EXACT`, is accepted from v1;
- the complete three-mode battery must be replayed at the **same frozen coordinates** after the corrected oracle passes CI.

No v1 parameter is changed for the correction run.
