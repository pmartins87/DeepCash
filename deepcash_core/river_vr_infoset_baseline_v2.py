from __future__ import annotations

from typing import Mapping

from .river_external_sampling import InfoKey
from .river_lab import (
    P1_AFTER_CHECK,
    ROOT,
    RiverGameSpec,
    _actions,
    _bet_amount,
    _terminal_showdown,
    _valid_deals,
    p0_vs_bet_node,
    p1_vs_bet_node,
)


def _continuation_value(
    spec: RiverGameSpec,
    policy: Mapping[InfoKey, tuple[float, ...]],
    *,
    i: int,
    j: int,
    node: str,
    player: int,
) -> float:
    key = (player, node, i if player == 0 else j)
    actions = _actions(spec, player, node)
    sigma = policy[key]
    if len(sigma) != len(actions):
        raise ValueError(f"policy/action shape mismatch at {key}")
    return sum(
        probability
        * _forced_action_child_value(
            spec,
            i=i,
            j=j,
            player=player,
            node=node,
            action=action,
            policy=policy,
        )
        for probability, action in zip(sigma, actions)
    )


def _forced_action_child_value(
    spec: RiverGameSpec,
    *,
    i: int,
    j: int,
    player: int,
    node: str,
    action: str,
    policy: Mapping[InfoKey, tuple[float, ...]],
) -> float:
    """Exact P0 payoff after forcing one public action then following policy."""
    if player == 0 and node == ROOT:
        if action == "CHECK":
            return _continuation_value(
                spec, policy, i=i, j=j, node=P1_AFTER_CHECK, player=1
            )
        return _continuation_value(
            spec,
            policy,
            i=i,
            j=j,
            node=p1_vs_bet_node(_bet_amount(action)),
            player=1,
        )

    if player == 1 and node == P1_AFTER_CHECK:
        if action == "CHECK":
            return _terminal_showdown(spec, i, j)
        return _continuation_value(
            spec,
            policy,
            i=i,
            j=j,
            node=p0_vs_bet_node(_bet_amount(action)),
            player=0,
        )

    if player == 1 and node.startswith("P1_VS_BET_"):
        amount = int(node.rsplit("_", 1)[1])
        if action == "FOLD":
            return float(spec.pot) / 2.0
        if action == "CALL":
            return _terminal_showdown(spec, i, j, amount)
        raise ValueError(f"unexpected P1 response action {action!r}")

    if player == 0 and node.startswith("P0_VS_BET_"):
        amount = int(node.rsplit("_", 1)[1])
        if action == "FOLD":
            return -float(spec.pot) / 2.0
        if action == "CALL":
            return _terminal_showdown(spec, i, j, amount)
        raise ValueError(f"unexpected P0 response action {action!r}")

    raise ValueError(f"unsupported public node {(player, node)!r}")


def _conditional_hidden_deals(
    spec: RiverGameSpec,
    *,
    traverser: int,
    own_hand_index: int,
    player: int,
    node: str,
    policy: Mapping[InfoKey, tuple[float, ...]],
) -> tuple[tuple[int, int, float], ...]:
    if traverser not in (0, 1):
        raise ValueError("traverser must be 0 or 1")
    if player not in (0, 1) or player == traverser:
        raise ValueError("baseline is defined only at a non-traverser node")

    weighted: list[tuple[int, int, float]] = []
    for i, j, raw_weight in _valid_deals(spec):
        if traverser == 0:
            if i != own_hand_index:
                continue
            if player != 1:
                raise ValueError("P0 traverser expects P1 as non-traverser")
            visible_weight = float(raw_weight)
        else:
            if j != own_hand_index:
                continue
            if player != 0:
                raise ValueError("P1 traverser expects P0 as non-traverser")
            visible_weight = float(raw_weight)
            if node.startswith("P0_VS_BET_"):
                root_actions = _actions(spec, 0, ROOT)
                check_index = root_actions.index("CHECK")
                visible_weight *= policy[(0, ROOT, i)][check_index]
            elif node != ROOT:
                raise ValueError(f"unsupported traverser-visible P0 node {node!r}")
        if visible_weight > 0.0:
            weighted.append((i, j, visible_weight))

    total = sum(weight for _, _, weight in weighted)
    if total <= 0.0:
        raise ValueError("no positive traverser-visible hidden-opponent posterior mass")
    return tuple((i, j, weight / total) for i, j, weight in weighted)


def exact_infoset_action_baselines_v2(
    spec: RiverGameSpec,
    *,
    traverser: int,
    own_hand_index: int,
    player: int,
    node: str,
    policy: Mapping[InfoKey, tuple[float, ...]],
) -> tuple[float, ...]:
    """Exact no-private-leak baseline for one augmented infoset.

    There is intentionally no realized opponent-hand parameter. The baseline
    integrates over all hidden hands consistent with the traverser's private
    combo and the observed public history.
    """
    own_range = spec.p0_range if traverser == 0 else spec.p1_range
    if isinstance(own_hand_index, bool) or not isinstance(own_hand_index, int):
        raise ValueError("own_hand_index must be an integer")
    if not 0 <= own_hand_index < len(own_range):
        raise ValueError("own_hand_index outside traverser range")

    actions = _actions(spec, player, node)
    posterior = _conditional_hidden_deals(
        spec,
        traverser=traverser,
        own_hand_index=own_hand_index,
        player=player,
        node=node,
        policy=policy,
    )
    return tuple(
        sum(
            probability
            * _forced_action_child_value(
                spec,
                i=i,
                j=j,
                player=player,
                node=node,
                action=action,
                policy=policy,
            )
            for i, j, probability in posterior
        )
        for action in actions
    )
