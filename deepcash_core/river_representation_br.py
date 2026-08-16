from __future__ import annotations

from itertools import product
from typing import Mapping

from .river_lab import (
    P1_AFTER_CHECK,
    ROOT,
    RiverGameSpec,
    _actions,
    _policy_deal_value,
    _valid_deals,
    p0_vs_bet_node,
    p1_vs_bet_node,
)
from .river_representation_lab import RiverBucketMaps


ExactInfoKey = tuple[int, str, int]


def _bucket_members(mapping: tuple[int, ...]) -> dict[int, tuple[int, ...]]:
    groups: dict[int, list[int]] = {}
    for hand_index, bucket in enumerate(mapping):
        groups.setdefault(bucket, []).append(hand_index)
    return {bucket: tuple(indices) for bucket, indices in groups.items()}


def _player_plan_patterns(spec: RiverGameSpec, player: int):
    """Yield one pure action pattern shared by every hand in one bucket."""
    if player == 0:
        root = ROOT
        response_nodes = tuple(p0_vs_bet_node(bet) for bet in spec.bet_sizes)
    elif player == 1:
        root = P1_AFTER_CHECK
        response_nodes = tuple(p1_vs_bet_node(bet) for bet in spec.bet_sizes)
    else:
        raise ValueError("player must be 0 or 1")

    root_actions = _actions(spec, player, root)
    for root_choice in range(len(root_actions)):
        for responses in product((0, 1), repeat=len(response_nodes)):
            yield root_choice, dict(zip(response_nodes, responses))


def _expand_bucket_plan(
    spec: RiverGameSpec,
    *,
    player: int,
    hand_indices: tuple[int, ...],
    root_choice: int,
    responses: Mapping[str, int],
) -> dict[ExactInfoKey, int]:
    plan: dict[ExactInfoKey, int] = {}
    root = ROOT if player == 0 else P1_AFTER_CHECK
    for hand_index in hand_indices:
        plan[(player, root, hand_index)] = root_choice
        for node, action_index in responses.items():
            plan[(player, node, hand_index)] = action_index
    return plan


def bucket_constrained_best_response_values(
    spec: RiverGameSpec,
    maps: RiverBucketMaps,
    policy: Mapping[ExactInfoKey, tuple[float, ...]],
) -> tuple[float, float]:
    """Return exact BR bounds while respecting the supplied private buckets.

    The policy is expanded to exact combo keys, but a best responder may choose
    only one pure action pattern per bucket. Every exact hand mapped to the same
    bucket therefore shares the root and response actions, exactly matching the
    information available to the representation-aware solver.

    Returns `(br0_value, br1_value)`, where `br0_value` is P0's maximum value
    against the fixed P1 policy and `br1_value` is P0's minimum value against
    P1's best response.
    """
    maps.validate(spec)
    deals = _valid_deals(spec)
    total = sum(weight for _, _, weight in deals)
    if total <= 0.0:
        raise ValueError("game has no positive chance mass")

    p0_groups = _bucket_members(maps.p0)
    br0_numerator = 0.0
    for _, hand_indices in sorted(p0_groups.items()):
        member_set = set(hand_indices)
        compatible = [
            (i, j, weight)
            for i, j, weight in deals
            if i in member_set
        ]
        if not compatible:
            continue
        best = None
        for root_choice, responses in _player_plan_patterns(spec, 0):
            plan = _expand_bucket_plan(
                spec,
                player=0,
                hand_indices=hand_indices,
                root_choice=root_choice,
                responses=responses,
            )
            value = sum(
                weight
                * _policy_deal_value(
                    spec,
                    i,
                    j,
                    policy,
                    deterministic_player=0,
                    deterministic_plan=plan,
                )
                for i, j, weight in compatible
            )
            best = value if best is None else max(best, value)
        if best is None:  # pragma: no cover - protected by non-empty actions
            raise AssertionError("P0 bucket has no pure plan")
        br0_numerator += best

    p1_groups = _bucket_members(maps.p1)
    br1_numerator = 0.0
    for _, hand_indices in sorted(p1_groups.items()):
        member_set = set(hand_indices)
        compatible = [
            (i, j, weight)
            for i, j, weight in deals
            if j in member_set
        ]
        if not compatible:
            continue
        best_for_p1 = None
        for root_choice, responses in _player_plan_patterns(spec, 1):
            plan = _expand_bucket_plan(
                spec,
                player=1,
                hand_indices=hand_indices,
                root_choice=root_choice,
                responses=responses,
            )
            p0_value = sum(
                weight
                * _policy_deal_value(
                    spec,
                    i,
                    j,
                    policy,
                    deterministic_player=1,
                    deterministic_plan=plan,
                )
                for i, j, weight in compatible
            )
            best_for_p1 = (
                p0_value
                if best_for_p1 is None
                else min(best_for_p1, p0_value)
            )
        if best_for_p1 is None:  # pragma: no cover
            raise AssertionError("P1 bucket has no pure plan")
        br1_numerator += best_for_p1

    return br0_numerator / total, br1_numerator / total
