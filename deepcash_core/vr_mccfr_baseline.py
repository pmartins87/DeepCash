from __future__ import annotations

import math
from typing import Sequence


def _probability_vector(values: Sequence[float], *, name: str) -> tuple[float, ...]:
    out = tuple(float(v) for v in values)
    if not out:
        raise ValueError(f"{name} cannot be empty")
    if any((not math.isfinite(v) or v < 0.0) for v in out):
        raise ValueError(f"{name} must contain finite non-negative values")
    total = sum(out)
    if not math.isfinite(total) or abs(total - 1.0) > 1e-12:
        raise ValueError(f"{name} must sum to one")
    return out


def baseline_enhanced_action_values(
    *,
    sampling_policy: Sequence[float],
    baselines: Sequence[float],
    sampled_action: int,
    sampled_child_value: float,
) -> tuple[float, ...]:
    """Return Schmid et al.'s baseline-enhanced sampled action-value vector.

    For all non-sampled actions the estimate equals the baseline. For the sampled
    action ``a*`` the residual is importance-corrected by ``1/q(a*)``. This
    primitive intentionally does not know the target strategy: the same action
    estimates can be contracted with any target policy that is absolutely
    continuous with respect to the sampling policy.
    """
    q = _probability_vector(sampling_policy, name="sampling_policy")
    b = tuple(float(v) for v in baselines)
    if len(b) != len(q):
        raise ValueError("baseline length must match sampling policy")
    if any(not math.isfinite(v) for v in b):
        raise ValueError("baselines must be finite")
    if isinstance(sampled_action, bool) or not isinstance(sampled_action, int):
        raise ValueError("sampled_action must be an integer index")
    if not 0 <= sampled_action < len(q):
        raise ValueError("sampled_action is outside action support")
    if q[sampled_action] <= 0.0:
        raise ValueError("sampled action must have positive sampling probability")
    child = float(sampled_child_value)
    if not math.isfinite(child):
        raise ValueError("sampled_child_value must be finite")

    out = list(b)
    out[sampled_action] = b[sampled_action] + (
        child - b[sampled_action]
    ) / q[sampled_action]
    if any(not math.isfinite(v) for v in out):
        raise ValueError("baseline-enhanced action estimate became non-finite")
    return tuple(out)


def baseline_enhanced_node_value(
    *,
    target_policy: Sequence[float],
    sampling_policy: Sequence[float],
    baselines: Sequence[float],
    sampled_action: int,
    sampled_child_value: float,
) -> float:
    """Contract baseline-enhanced action estimates with a target policy.

    Absolute-continuity is enforced fail-closed: every target-positive action
    must have positive sampling probability. This protects later off-policy
    experiments from silently introducing biased unsupported target mass.
    """
    sigma = _probability_vector(target_policy, name="target_policy")
    q = _probability_vector(sampling_policy, name="sampling_policy")
    if len(sigma) != len(q):
        raise ValueError("target and sampling policies must have equal length")
    for target_prob, sample_prob in zip(sigma, q):
        if target_prob > 0.0 and sample_prob <= 0.0:
            raise ValueError(
                "target-positive actions require positive sampling probability"
            )
    estimates = baseline_enhanced_action_values(
        sampling_policy=q,
        baselines=baselines,
        sampled_action=sampled_action,
        sampled_child_value=sampled_child_value,
    )
    value = sum(prob * estimate for prob, estimate in zip(sigma, estimates))
    if not math.isfinite(value):
        raise ValueError("baseline-enhanced node value became non-finite")
    return value
