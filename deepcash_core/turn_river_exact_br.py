from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Union

from .turn_river_exact_game import (
    InfoKey,
    Policy,
    TURN_P1_AFTER_CHECK,
    TURN_ROOT,
    TurnRiverGameSpec,
    _bet_amount,
    _showdown_value,
    actions_for_infoset,
    all_infosets,
    legal_river_cards,
    p0_bet_call_history,
    p1_bet_call_history,
    river_geometry,
    river_p0_vs_bet_node,
    river_p1_after_check_node,
    river_p1_vs_bet_node,
    river_root_node,
    turn_p0_vs_bet_node,
    turn_p1_vs_bet_node,
    valid_turn_deals,
)


@dataclass(frozen=True)
class TerminalNode:
    value_p0: float


@dataclass(frozen=True)
class ChanceNode:
    children: tuple[tuple[float, "GameNode"], ...]


@dataclass(frozen=True)
class DecisionNode:
    player: int
    key: InfoKey
    actions: tuple[str, ...]
    children: tuple["GameNode", ...]
    stage: int


GameNode = Union[TerminalNode, ChanceNode, DecisionNode]


@dataclass(frozen=True)
class ExactBestResponseResult:
    player: int
    value_p0: float
    action_index: Mapping[InfoKey, int]
    action_name: Mapping[InfoKey, str]


@dataclass(frozen=True)
class TurnRiverExploitabilityResult:
    policy_ev: float
    br0_value: float
    br1_value: float
    exploitability: float
    exploitability_per_pot: float
    br0: ExactBestResponseResult
    br1: ExactBestResponseResult


POLICY_TOLERANCE = 1e-9


def validate_exact_policy(spec: TurnRiverGameSpec, policy: Policy) -> None:
    """Fail closed unless ``policy`` is a complete normalized exact policy."""

    spec.validate()
    expected = set(all_infosets(spec))
    actual = set(policy)
    if actual != expected:
        missing = len(expected - actual)
        extra = len(actual - expected)
        raise ValueError(
            f"policy infosets do not match exact turn+river game: missing={missing} extra={extra}"
        )

    for key in expected:
        probabilities = tuple(float(value) for value in policy[key])
        actions = actions_for_infoset(spec, key)
        if len(probabilities) != len(actions):
            raise ValueError(f"policy action shape mismatch at {key}")
        if any(not math.isfinite(value) or value < 0.0 for value in probabilities):
            raise ValueError("policy probabilities must be finite and non-negative")
        if not math.isclose(
            sum(probabilities),
            1.0,
            rel_tol=0.0,
            abs_tol=POLICY_TOLERANCE,
        ):
            raise ValueError(f"policy probabilities must sum to one at {key}")


def _terminal_fold_value(spec: TurnRiverGameSpec, *, player_who_bet: int) -> float:
    half = float(spec.turn_state.pot) / 2.0
    return half if player_who_bet == 0 else -half


def _build_river_node(
    spec: TurnRiverGameSpec,
    *,
    i: int,
    j: int,
    history: str,
    river_card: int,
    player: int,
    kind: str,
    faced_bet: int | None = None,
) -> GameNode:
    pot, stack = river_geometry(spec, history)
    if stack <= 0:
        return TerminalNode(_showdown_value(spec, i, j, river_card, pot=pot))

    if player == 0 and kind == "ROOT":
        node_name = river_root_node(history, river_card)
        stage = 4
    elif player == 1 and kind == "P1_AFTER_CHECK":
        node_name = river_p1_after_check_node(history, river_card)
        stage = 5
    elif player == 1 and kind == "P1_VS_BET" and faced_bet is not None:
        node_name = river_p1_vs_bet_node(history, river_card, faced_bet)
        stage = 6
    elif player == 0 and kind == "P0_VS_BET" and faced_bet is not None:
        node_name = river_p0_vs_bet_node(history, river_card, faced_bet)
        stage = 6
    else:
        raise AssertionError((player, kind, faced_bet))

    key = (player, node_name, i if player == 0 else j)
    actions = actions_for_infoset(spec, key)
    children: list[GameNode] = []
    for action in actions:
        if player == 0 and kind == "ROOT":
            if action == "CHECK":
                child = _build_river_node(
                    spec,
                    i=i,
                    j=j,
                    history=history,
                    river_card=river_card,
                    player=1,
                    kind="P1_AFTER_CHECK",
                )
            else:
                child = _build_river_node(
                    spec,
                    i=i,
                    j=j,
                    history=history,
                    river_card=river_card,
                    player=1,
                    kind="P1_VS_BET",
                    faced_bet=_bet_amount(action),
                )
        elif player == 1 and kind == "P1_AFTER_CHECK":
            if action == "CHECK":
                child = TerminalNode(
                    _showdown_value(spec, i, j, river_card, pot=pot)
                )
            else:
                child = _build_river_node(
                    spec,
                    i=i,
                    j=j,
                    history=history,
                    river_card=river_card,
                    player=0,
                    kind="P0_VS_BET",
                    faced_bet=_bet_amount(action),
                )
        elif player == 1 and kind == "P1_VS_BET":
            assert faced_bet is not None
            child = TerminalNode(
                float(pot) / 2.0
                if action == "FOLD"
                else _showdown_value(
                    spec,
                    i,
                    j,
                    river_card,
                    pot=pot,
                    matched_bet=faced_bet,
                )
            )
        elif player == 0 and kind == "P0_VS_BET":
            assert faced_bet is not None
            child = TerminalNode(
                -float(pot) / 2.0
                if action == "FOLD"
                else _showdown_value(
                    spec,
                    i,
                    j,
                    river_card,
                    pot=pot,
                    matched_bet=faced_bet,
                )
            )
        else:  # pragma: no cover
            raise AssertionError((player, kind, action))
        children.append(child)
    return DecisionNode(player, key, actions, tuple(children), stage)


def _build_river_chance(
    spec: TurnRiverGameSpec,
    *,
    i: int,
    j: int,
    history: str,
) -> ChanceNode:
    cards = legal_river_cards(spec, i, j)
    probability = 1.0 / float(len(cards))
    pot, stack = river_geometry(spec, history)
    children: list[tuple[float, GameNode]] = []
    for river_card in cards:
        if stack <= 0:
            child: GameNode = TerminalNode(
                _showdown_value(spec, i, j, river_card, pot=pot)
            )
        else:
            child = _build_river_node(
                spec,
                i=i,
                j=j,
                history=history,
                river_card=river_card,
                player=0,
                kind="ROOT",
            )
        children.append((probability, child))
    return ChanceNode(tuple(children))


def _build_turn_node(
    spec: TurnRiverGameSpec,
    *,
    i: int,
    j: int,
    player: int,
    kind: str,
    faced_bet: int | None = None,
) -> DecisionNode:
    if player == 0 and kind == "ROOT":
        node_name = TURN_ROOT
        stage = 0
    elif player == 1 and kind == "P1_AFTER_CHECK":
        node_name = TURN_P1_AFTER_CHECK
        stage = 1
    elif player == 1 and kind == "P1_VS_BET" and faced_bet is not None:
        node_name = turn_p1_vs_bet_node(faced_bet)
        stage = 2
    elif player == 0 and kind == "P0_VS_BET" and faced_bet is not None:
        node_name = turn_p0_vs_bet_node(faced_bet)
        stage = 2
    else:
        raise AssertionError((player, kind, faced_bet))

    key = (player, node_name, i if player == 0 else j)
    actions = actions_for_infoset(spec, key)
    children: list[GameNode] = []
    for action in actions:
        if player == 0 and kind == "ROOT":
            if action == "CHECK":
                child = _build_turn_node(
                    spec, i=i, j=j, player=1, kind="P1_AFTER_CHECK"
                )
            else:
                child = _build_turn_node(
                    spec,
                    i=i,
                    j=j,
                    player=1,
                    kind="P1_VS_BET",
                    faced_bet=_bet_amount(action),
                )
        elif player == 1 and kind == "P1_AFTER_CHECK":
            if action == "CHECK":
                child = _build_river_chance(
                    spec, i=i, j=j, history="CHECK_CHECK"
                )
            else:
                child = _build_turn_node(
                    spec,
                    i=i,
                    j=j,
                    player=0,
                    kind="P0_VS_BET",
                    faced_bet=_bet_amount(action),
                )
        elif player == 1 and kind == "P1_VS_BET":
            assert faced_bet is not None
            child = (
                TerminalNode(_terminal_fold_value(spec, player_who_bet=0))
                if action == "FOLD"
                else _build_river_chance(
                    spec,
                    i=i,
                    j=j,
                    history=p0_bet_call_history(faced_bet),
                )
            )
        elif player == 0 and kind == "P0_VS_BET":
            assert faced_bet is not None
            child = (
                TerminalNode(_terminal_fold_value(spec, player_who_bet=1))
                if action == "FOLD"
                else _build_river_chance(
                    spec,
                    i=i,
                    j=j,
                    history=p1_bet_call_history(faced_bet),
                )
            )
        else:  # pragma: no cover
            raise AssertionError((player, kind, action))
        children.append(child)
    return DecisionNode(player, key, actions, tuple(children), stage)


def _build_game_tree(spec: TurnRiverGameSpec) -> ChanceNode:
    """Materialize the finite exact control tree used only by the R6 BR oracle."""

    spec.validate()
    deals = valid_turn_deals(spec)
    total = sum(weight for _, _, weight in deals)
    return ChanceNode(
        tuple(
            (
                weight / total,
                _build_turn_node(spec, i=i, j=j, player=0, kind="ROOT"),
            )
            for i, j, weight in deals
        )
    )


def _node_value(
    node: GameNode,
    *,
    fixed_policy: Policy,
    br_player: int,
    choices: Mapping[InfoKey, int],
) -> float:
    if isinstance(node, TerminalNode):
        return node.value_p0
    if isinstance(node, ChanceNode):
        return sum(
            probability
            * _node_value(
                child,
                fixed_policy=fixed_policy,
                br_player=br_player,
                choices=choices,
            )
            for probability, child in node.children
        )

    if node.player == br_player:
        index = choices.get(node.key, 0)
        if not 0 <= index < len(node.children):
            raise ValueError(f"invalid best-response action index at {node.key}")
        return _node_value(
            node.children[index],
            fixed_policy=fixed_policy,
            br_player=br_player,
            choices=choices,
        )

    probabilities = fixed_policy[node.key]
    return sum(
        probability
        * _node_value(
            child,
            fixed_policy=fixed_policy,
            br_player=br_player,
            choices=choices,
        )
        for probability, child in zip(probabilities, node.children)
    )


def _collect_br_occurrences(
    node: GameNode,
    *,
    fixed_policy: Policy,
    br_player: int,
    counterfactual_reach: float,
    out: dict[InfoKey, list[tuple[DecisionNode, float]]],
) -> None:
    if isinstance(node, TerminalNode):
        return
    if isinstance(node, ChanceNode):
        for probability, child in node.children:
            _collect_br_occurrences(
                child,
                fixed_policy=fixed_policy,
                br_player=br_player,
                counterfactual_reach=counterfactual_reach * probability,
                out=out,
            )
        return

    if node.player == br_player:
        out.setdefault(node.key, []).append((node, counterfactual_reach))
        # Counterfactual reach deliberately excludes the BR player's own action
        # probabilities. Enumerate all own branches unchanged.
        for child in node.children:
            _collect_br_occurrences(
                child,
                fixed_policy=fixed_policy,
                br_player=br_player,
                counterfactual_reach=counterfactual_reach,
                out=out,
            )
        return

    probabilities = fixed_policy[node.key]
    for probability, child in zip(probabilities, node.children):
        if probability <= 0.0:
            continue
        _collect_br_occurrences(
            child,
            fixed_policy=fixed_policy,
            br_player=br_player,
            counterfactual_reach=counterfactual_reach * probability,
            out=out,
        )


def exact_best_response(
    spec: TurnRiverGameSpec,
    fixed_policy: Policy,
    *,
    player: int,
) -> ExactBestResponseResult:
    """Return an exact information-set best response to ``fixed_policy``.

    The returned action map contains one action per best-response infoset. Hidden
    opponent private deals are integrated with chance/opponent counterfactual
    reach and never appear in an action key.
    """

    if player not in (0, 1):
        raise ValueError("best-response player must be 0 or 1")
    validate_exact_policy(spec, fixed_policy)
    root = _build_game_tree(spec)

    occurrences: dict[InfoKey, list[tuple[DecisionNode, float]]] = {}
    _collect_br_occurrences(
        root,
        fixed_policy=fixed_policy,
        br_player=player,
        counterfactual_reach=1.0,
        out=occurrences,
    )

    br_keys = [key for key in all_infosets(spec) if key[0] == player]
    choices: dict[InfoKey, int] = {key: 0 for key in br_keys}
    stages: dict[InfoKey, int] = {}
    for key, nodes in occurrences.items():
        node_stages = {node.stage for node, _reach in nodes}
        if len(node_stages) != 1:
            raise RuntimeError(f"best-response infoset spans multiple stages: {key}")
        stages[key] = next(iter(node_stages))

    # Deepest information sets are independent of all shallower own choices.
    # Same-stage infosets cannot be descendants of one another in this tree.
    ordered = sorted(
        br_keys,
        key=lambda key: (stages.get(key, -1), key[1], key[2]),
        reverse=True,
    )
    for key in ordered:
        nodes = occurrences.get(key, ())
        if not nodes:
            choices[key] = 0
            continue
        action_count = len(nodes[0][0].actions)
        if any(len(node.actions) != action_count for node, _reach in nodes):
            raise RuntimeError(f"best-response infoset action shape is inconsistent: {key}")

        action_values: list[float] = []
        for action_index in range(action_count):
            value = 0.0
            for node, reach in nodes:
                if reach <= 0.0:
                    continue
                value += reach * _node_value(
                    node.children[action_index],
                    fixed_policy=fixed_policy,
                    br_player=player,
                    choices=choices,
                )
            action_values.append(value)

        if player == 0:
            best_value = max(action_values)
        else:
            best_value = min(action_values)
        choices[key] = next(
            index
            for index, value in enumerate(action_values)
            if math.isclose(value, best_value, rel_tol=0.0, abs_tol=1e-15)
            or value == best_value
        )

    value_p0 = _node_value(
        root,
        fixed_policy=fixed_policy,
        br_player=player,
        choices=choices,
    )
    action_names = {
        key: actions_for_infoset(spec, key)[index]
        for key, index in choices.items()
    }
    return ExactBestResponseResult(
        player=player,
        value_p0=value_p0,
        action_index=dict(choices),
        action_name=action_names,
    )


def exact_best_response_values(
    spec: TurnRiverGameSpec,
    policy: Policy,
) -> tuple[float, float]:
    """Return ``(P0 BR value, P0 value versus P1 BR)``."""

    br0 = exact_best_response(spec, policy, player=0)
    br1 = exact_best_response(spec, policy, player=1)
    return br0.value_p0, br1.value_p0


def exact_turn_river_exploitability(
    spec: TurnRiverGameSpec,
    policy: Policy,
    *,
    policy_ev: float | None = None,
) -> TurnRiverExploitabilityResult:
    """Evaluate exact two-street BR values and exploitability for a fixed policy."""

    validate_exact_policy(spec, policy)
    if policy_ev is None:
        from .turn_river_exact_game import evaluate_turn_river_policy

        policy_ev = evaluate_turn_river_policy(spec, policy)
    if not math.isfinite(float(policy_ev)):
        raise ValueError("policy_ev must be finite")

    br0 = exact_best_response(spec, policy, player=0)
    br1 = exact_best_response(spec, policy, player=1)
    if br0.value_p0 + 1e-10 < float(policy_ev):
        raise RuntimeError("P0 best response is worse than fixed-policy self-play")
    if br1.value_p0 - 1e-10 > float(policy_ev):
        raise RuntimeError("P1 best response is worse than fixed-policy self-play")

    exploitability = max(0.0, (br0.value_p0 - br1.value_p0) / 2.0)
    return TurnRiverExploitabilityResult(
        policy_ev=float(policy_ev),
        br0_value=br0.value_p0,
        br1_value=br1.value_p0,
        exploitability=exploitability,
        exploitability_per_pot=exploitability / float(spec.turn_state.pot),
        br0=br0,
        br1=br1,
    )
