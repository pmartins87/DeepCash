from __future__ import annotations

from typing import Mapping

from .river_external_sampling import InfoKey
from .river_lab import (
    P1_AFTER_CHECK,
    ROOT,
    RiverGameSpec,
    _actions,
    _bet_amount,
    _profile_value,
    _terminal_showdown,
    _valid_deals,
    p0_vs_bet_node,
    p1_vs_bet_node,
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
    """Exact P0 payoff after forcing one public action, then following policy."""
    if player == 0 and node == ROOT:
        if action == "CHECK":
            return _profile_value(spec, policy, i=i, j=j, node=P1_AFTER_CHECK, player=1)
        return _profile_value(
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
        return _profile_value(
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

    raise ValueError(f"unsupported public node for forced action baseline: {(player, node)}")


def _conditional_hidden_deals(
    spec: RiverGameSpec,
    *,
    traverser: int,
    own_hand_index: int,
    player: int,
    node: str,
    policy: Mapping[InfoKey, tuple[float, ...]],
) -> tuple[tuple[int, int, float], ...]:
    """Compatible hidden-opponent deals weighted only by traverser-visible history."""
    if traverser not in (0, 1) or player not in (0, 1) or player == traverser:
        raise ValueError("baseline requested only at a non-traverser player node")

    out: list[tuple[int, int, float]] = []
    for i, j, raw_weight in _valid_deals(spec):
        if traverser == 0:
            if i != own_hand_index:
                continue
            # Every P1 node in this river tree occurs before P1 has taken any
            # earlier public action. P0's own action reach is known from i and
            # constant across hidden j, so it cancels on normalization.
            if player != 1:
                raise ValueError("P0 traverser expects a P1 non-traverser node")
            visible_weight = raw_weight
        else:
            if j != own_hand_index:
                continue
            if player != 0:
                raise ValueError("P1 traverser expects a P0 non-traverser node")
            visible_weight = raw_weight
            if node.startswith("P0_VS_BET_"):
                # Public history includes P0 CHECK. Reweight hidden P0 combos by
                # the probability of that observed action before normalization.
                root_key = (0, ROOT, i)
                root_actions = _actions(spec, 0, ROOT)
                check_idx = root_actions.index("CHECK")
                visible_weight *= policy[root_key][check_idx]
            elif node != ROOT:
                raise ValueError(f"unsupported P0 public node {node!r}")

        if visible_weight > 0.0:
            out.append((i, j, float(visible_weight)))

    total = sum(weight for _, _, weight in out)
    if total <= 0.0:
        raise ValueError("no positive traverser-visible hidden-opponent posterior mass")
    return tuple((i, j, weight / total) for i, j, weight in out)


def exact_infoset_action_baselines(
    spec: RiverGameSpec,
    *,
    traverser: int,
    own_hand_index: int,
    player: int,
    node: str,
    policy: Mapping[InfoKey, tuple[float, ...]],
) -> tuple[float, ...]:
    """Exact no-private-leak baseline vector for one augmented infoset.

    The API intentionally contains no realized opponent-hand argument. It
    integrates over all compatible hidden opponent combos using only the
    traverser's private combo and public history.
    """
    if traverser not in (0, 1):
        raise ValueError("traverser must be 0 or 1")
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

    values: list[float] = []
    for action in actions:
        value = 0.0
        for i, j, probability in posterior:
            value += probability * _forced_action_child_value(
                spec,
                i=i,
                j=j,
                player=player,
                node=node,
                action=action,
                policy=policy,
            )
        values.append(value)
    return tuple(values)
