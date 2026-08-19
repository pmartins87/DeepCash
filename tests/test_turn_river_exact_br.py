from __future__ import annotations

from fractions import Fraction

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import RangeCombo
from deepcash_core.turn_river_exact_br import (
    ChanceNode,
    DecisionNode,
    TerminalNode,
    _build_game_tree,
    exact_best_response,
    exact_turn_river_exploitability,
    validate_exact_policy,
)
from deepcash_core.turn_river_exact_game import (
    TURN_ROOT,
    actions_for_infoset,
    all_infosets,
    build_turn_river_game,
    evaluate_turn_river_policy,
)
from deepcash_core.turn_river_public_state import TurnPublicState


def c(text: str) -> int:
    return card_from_str(text)


def singleton_spec():
    state = TurnPublicState(
        board=(c("Ah"), c("Kd"), c("9c"), c("4s")),
        p0_range=(RangeCombo((c("Qh"), c("Qc")), 1.0),),
        p1_range=(RangeCombo((c("Jh"), c("Jc")), 1.0),),
        pot=100,
        stack=50,
        min_bet=20,
    )
    state.validate()
    return build_turn_river_game(
        state,
        turn_fractions=(Fraction(1, 2),),
        river_fractions=(Fraction(1, 2),),
    )


def uniform_policy(spec):
    return {
        key: tuple(
            1.0 / len(actions_for_infoset(spec, key))
            for _ in actions_for_infoset(spec, key)
        )
        for key in all_infosets(spec)
    }


def perfect_information_value(node, policy, br_player):
    """Independent local BR recursion, valid when both ranges are singleton."""
    if isinstance(node, TerminalNode):
        return node.value_p0
    if isinstance(node, ChanceNode):
        return sum(
            probability * perfect_information_value(child, policy, br_player)
            for probability, child in node.children
        )
    assert isinstance(node, DecisionNode)
    child_values = [
        perfect_information_value(child, policy, br_player)
        for child in node.children
    ]
    if node.player == br_player:
        return max(child_values) if br_player == 0 else min(child_values)
    return sum(
        probability * value
        for probability, value in zip(policy[node.key], child_values)
    )


def test_exact_br_brackets_fixed_policy_self_play_and_is_deterministic():
    spec = singleton_spec()
    policy = uniform_policy(spec)
    policy_ev = evaluate_turn_river_policy(spec, policy)

    first = exact_turn_river_exploitability(spec, policy, policy_ev=policy_ev)
    second = exact_turn_river_exploitability(spec, policy, policy_ev=policy_ev)

    assert first == second
    assert first.br0_value >= policy_ev - 1e-12
    assert first.br1_value <= policy_ev + 1e-12
    assert first.exploitability == pytest.approx(
        max(0.0, (first.br0_value - first.br1_value) / 2.0),
        abs=1e-12,
    )
    assert first.exploitability_per_pot == pytest.approx(
        first.exploitability / 100.0,
        abs=1e-12,
    )


def test_singleton_information_set_br_matches_independent_perfect_information_oracle():
    spec = singleton_spec()
    policy = uniform_policy(spec)
    tree = _build_game_tree(spec)

    br0 = exact_best_response(spec, policy, player=0)
    br1 = exact_best_response(spec, policy, player=1)

    assert br0.value_p0 == pytest.approx(
        perfect_information_value(tree, policy, 0), abs=1e-12
    )
    assert br1.value_p0 == pytest.approx(
        perfect_information_value(tree, policy, 1), abs=1e-12
    )


def two_opponent_combo_spec(reverse: bool):
    p1 = [
        RangeCombo((c("Jh"), c("Jc")), 3.0),
        RangeCombo((c("8h"), c("8c")), 1.0),
    ]
    if reverse:
        p1.reverse()
    state = TurnPublicState(
        board=(c("Ah"), c("Kd"), c("9c"), c("4s")),
        p0_range=(RangeCombo((c("Qh"), c("Qc")), 1.0),),
        p1_range=tuple(p1),
        pot=100,
        stack=50,
        min_bet=20,
    )
    state.validate()
    return build_turn_river_game(
        state,
        turn_fractions=(Fraction(1, 2),),
        river_fractions=(Fraction(1, 2),),
    )


def hand_dependent_opponent_policy(spec):
    policy = {}
    for key in all_infosets(spec):
        player, _node, hand_index = key
        actions = actions_for_infoset(spec, key)
        if player == 0:
            policy[key] = tuple(1.0 / len(actions) for _ in actions)
            continue

        hole = set(spec.turn_state.p1_range[hand_index].hole)
        is_jacks = hole == {c("Jh"), c("Jc")}
        if len(actions) == 2 and actions == ("FOLD", "CALL"):
            policy[key] = (0.2, 0.8) if is_jacks else (0.8, 0.2)
        else:
            # Same semantic hand gets the same public-action tendency regardless
            # of where that combo appears in the range tuple.
            if is_jacks:
                last = 0.8
                rest = 0.2 / float(len(actions) - 1)
                policy[key] = tuple(
                    last if index == len(actions) - 1 else rest
                    for index in range(len(actions))
                )
            else:
                first = 0.8
                rest = 0.2 / float(len(actions) - 1)
                policy[key] = tuple(
                    first if index == 0 else rest
                    for index in range(len(actions))
                )
    return policy


def test_br_aggregates_hidden_opponent_hands_and_is_invariant_to_range_enumeration_order():
    left = two_opponent_combo_spec(False)
    right = two_opponent_combo_spec(True)
    left_policy = hand_dependent_opponent_policy(left)
    right_policy = hand_dependent_opponent_policy(right)

    left_br = exact_best_response(left, left_policy, player=0)
    right_br = exact_best_response(right, right_policy, player=0)

    assert left_br.value_p0 == pytest.approx(right_br.value_p0, abs=1e-12)
    assert left_br.action_name == right_br.action_name
    assert (0, TURN_ROOT, 0) in left_br.action_name
    assert all(len(key) == 3 for key in left_br.action_name)


def test_policy_validation_fails_closed_on_shape_mass_and_extra_hidden_state_key():
    spec = singleton_spec()
    policy = uniform_policy(spec)
    key = next(iter(policy))

    broken_shape = dict(policy)
    broken_shape[key] = (1.0,)
    with pytest.raises(ValueError, match="action shape mismatch"):
        validate_exact_policy(spec, broken_shape)

    broken_mass = dict(policy)
    broken_mass[key] = tuple(value * 0.5 for value in broken_mass[key])
    with pytest.raises(ValueError, match="sum to one"):
        validate_exact_policy(spec, broken_mass)

    extra = dict(policy)
    extra[(0, "LEAKED_OPPONENT_HAND", 0)] = (1.0,)
    with pytest.raises(ValueError, match="policy infosets do not match"):
        validate_exact_policy(spec, extra)


def test_invalid_best_response_player_fails_closed():
    spec = singleton_spec()
    with pytest.raises(ValueError, match="best-response player must be 0 or 1"):
        exact_best_response(spec, uniform_policy(spec), player=2)
