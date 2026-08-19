from __future__ import annotations

import math
from fractions import Fraction

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.evaluator import evaluate_best
from deepcash_core.river_alternating_dcfr import AlternatingVariant
from deepcash_core.river_lab import RangeCombo
from deepcash_core.turn_river_exact_game import (
    TURN_ROOT,
    actions_for_infoset,
    advance_turn_river_solver,
    all_infosets,
    build_turn_river_game,
    conditioned_river_ranges,
    continuation_histories,
    evaluate_turn_river_policy,
    init_turn_river_solver,
    legal_river_cards,
    p0_bet_call_history,
    river_bet_sizes,
    river_geometry,
    turn_p1_vs_bet_node,
    turn_river_solver_result,
    valid_turn_deals,
)
from deepcash_core.turn_river_public_state import TurnPublicState


def c(text: str) -> int:
    return card_from_str(text)


def tiny_state(*, stack: int = 100) -> TurnPublicState:
    state = TurnPublicState(
        board=(c("Ah"), c("Kd"), c("9c"), c("4s")),
        p0_range=(RangeCombo((c("Qh"), c("Qc")), 1.0),),
        p1_range=(RangeCombo((c("Jh"), c("Jc")), 1.0),),
        pot=100,
        stack=stack,
        min_bet=20,
    )
    state.validate()
    return state


def deterministic_policy(spec, selector):
    policy = {}
    for key in all_infosets(spec):
        actions = actions_for_infoset(spec, key)
        chosen = selector(key, actions)
        policy[key] = tuple(1.0 if index == chosen else 0.0 for index in range(len(actions)))
    return policy


def all_check_policy(spec):
    def selector(_key, actions):
        if "CHECK" in actions:
            return actions.index("CHECK")
        if "CALL" in actions:
            return actions.index("CALL")
        return 0

    return deterministic_policy(spec, selector)


def manual_showdown_ev(spec, pot: int) -> float:
    state = spec.turn_state
    deals = valid_turn_deals(spec)
    deal_mass = sum(weight for _, _, weight in deals)
    total = 0.0
    for i, j, weight in deals:
        river_total = 0.0
        cards = legal_river_cards(spec, i, j)
        for river_card in cards:
            v0 = evaluate_best((*state.p0_range[i].hole, *state.board, river_card))
            v1 = evaluate_best((*state.p1_range[j].hole, *state.board, river_card))
            sign = int(v0 > v1) - int(v0 < v1)
            river_total += float(sign) * float(pot) / 2.0
        total += weight * river_total / float(len(cards))
    return total / deal_mass


def test_turn_and_river_geometry_carries_called_bets_exactly():
    spec = build_turn_river_game(
        tiny_state(),
        turn_fractions=(Fraction(1, 2), Fraction(1, 1)),
        river_fractions=(Fraction(1, 2), Fraction(1, 1)),
    )
    assert spec.turn_bet_sizes == (50, 100)
    assert continuation_histories(spec) == (
        "CHECK_CHECK",
        "P0_BET_50_CALL",
        "P0_BET_100_CALL",
        "P1_BET_50_CALL",
        "P1_BET_100_CALL",
    )
    assert river_geometry(spec, "CHECK_CHECK") == (100, 100)
    assert river_geometry(spec, "P0_BET_50_CALL") == (200, 50)
    assert river_geometry(spec, "P1_BET_50_CALL") == (200, 50)
    assert river_geometry(spec, "P0_BET_100_CALL") == (300, 0)
    assert river_bet_sizes(spec, "P0_BET_50_CALL") == (50,)
    assert river_bet_sizes(spec, "P0_BET_100_CALL") == ()


def test_all_check_policy_equals_exact_public_river_showdown_average():
    spec = build_turn_river_game(
        tiny_state(),
        turn_fractions=(Fraction(1, 2),),
        river_fractions=(Fraction(1, 2),),
    )
    policy = all_check_policy(spec)
    assert evaluate_turn_river_policy(spec, policy) == pytest.approx(
        manual_showdown_ev(spec, 100),
        abs=1e-12,
    )


def test_called_turn_allin_goes_to_forced_public_river_showdown():
    spec = build_turn_river_game(
        tiny_state(),
        turn_fractions=(Fraction(1, 1),),
        river_fractions=(Fraction(1, 2),),
    )

    def selector(key, actions):
        player, node, _hand = key
        if player == 0 and node == TURN_ROOT:
            return actions.index("BET_100")
        if player == 1 and node == turn_p1_vs_bet_node(100):
            return actions.index("CALL")
        if "CHECK" in actions:
            return actions.index("CHECK")
        if "CALL" in actions:
            return actions.index("CALL")
        return 0

    policy = deterministic_policy(spec, selector)
    assert evaluate_turn_river_policy(spec, policy) == pytest.approx(
        manual_showdown_ev(spec, 300),
        abs=1e-12,
    )
    assert river_geometry(spec, p0_bet_call_history(100)) == (300, 0)
    assert not any(
        p0_bet_call_history(100) in node
        for _player, node, _hand in all_infosets(spec)
        if node.startswith("RIVER|")
    )


def test_action_conditioned_ranges_use_only_own_reach_and_exact_card_removal():
    state = TurnPublicState(
        board=(c("Ah"), c("Kd"), c("9c"), c("4s")),
        p0_range=(
            RangeCombo((c("Qh"), c("Qc")), 2.0),
            RangeCombo((c("Th"), c("Tc")), 1.0),
        ),
        p1_range=(
            RangeCombo((c("Jh"), c("Jc")), 3.0),
            RangeCombo((c("8h"), c("8c")), 1.0),
        ),
        pot=100,
        stack=100,
        min_bet=20,
    )
    spec = build_turn_river_game(
        state,
        turn_fractions=(Fraction(1, 2),),
        river_fractions=(Fraction(1, 2),),
    )
    policy = all_check_policy(spec)

    policy[(0, TURN_ROOT, 0)] = (0.25, 0.75)
    policy[(0, TURN_ROOT, 1)] = (0.60, 0.40)
    response0 = (1, turn_p1_vs_bet_node(50), 0)
    response1 = (1, turn_p1_vs_bet_node(50), 1)
    policy[response0] = (0.20, 0.80)
    policy[response1] = (0.50, 0.50)

    p0, p1 = conditioned_river_ranges(
        spec,
        policy,
        history=p0_bet_call_history(50),
        river_card=c("2d"),
    )
    assert [combo.weight for combo in p0] == pytest.approx([1.50, 0.40])
    assert [combo.weight for combo in p1] == pytest.approx([2.40, 0.50])

    p0_removed, _ = conditioned_river_ranges(
        spec,
        policy,
        history=p0_bet_call_history(50),
        river_card=c("Qh"),
    )
    assert [combo.hole for combo in p0_removed] == [(c("Th"), c("Tc"))]
    assert p0_removed[0].weight == pytest.approx(0.40)


def test_alternating_dcfr_is_deterministic_and_resumable_in_memory():
    spec = build_turn_river_game(
        tiny_state(),
        turn_fractions=(Fraction(1, 2),),
        river_fractions=(Fraction(1, 2),),
    )
    one_plus_one = init_turn_river_solver(spec)
    advance_turn_river_solver(spec, one_plus_one, additional_iterations=1)
    advance_turn_river_solver(spec, one_plus_one, additional_iterations=1)

    two = init_turn_river_solver(spec)
    advance_turn_river_solver(spec, two, additional_iterations=2)

    assert one_plus_one.variant == AlternatingVariant.ALT_DCFR_150_0_2
    assert one_plus_one.iterations == two.iterations == 2
    assert one_plus_one.regrets == two.regrets
    assert one_plus_one.strategy_sum == two.strategy_sum

    result = turn_river_solver_result(spec, two)
    assert result.iterations == 2
    assert math.isfinite(result.policy_ev)
    assert result.infosets == len(all_infosets(spec))
    assert result.action_slots > result.infosets
    assert all(
        sum(probabilities) == pytest.approx(1.0)
        for probabilities in result.policy.values()
    )


def test_solver_rejects_negative_advance_and_zero_iteration_result():
    spec = build_turn_river_game(
        tiny_state(),
        turn_fractions=(Fraction(1, 2),),
        river_fractions=(Fraction(1, 2),),
    )
    state = init_turn_river_solver(spec)
    with pytest.raises(ValueError, match="additional_iterations cannot be negative"):
        advance_turn_river_solver(spec, state, additional_iterations=-1)
    with pytest.raises(ValueError, match="cannot evaluate an untrained turn\\+river solver"):
        turn_river_solver_result(spec, state)
