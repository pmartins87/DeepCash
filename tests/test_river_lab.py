from fractions import Fraction

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import (
    RangeCombo,
    RiverGameSpec,
    materialize_bet_sizes,
    solve_river_cfr_plus,
)


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str, weight: float = 1.0) -> RangeCombo:
    return RangeCombo((c(a), c(b)), weight)


def fixture_spec(bet_sizes=(40, 100)) -> RiverGameSpec:
    board = (c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h"))
    p0 = (
        combo("Qs", "Qh"),
        combo("Jc", "Js"),
        combo("Tc", "Ts"),
        combo("Ac", "Qc"),
        combo("Kc", "Qd"),
        combo("8c", "8d"),
    )
    p1 = (
        combo("Qd", "Jh"),
        combo("Jd", "Th"),
        combo("9d", "8h"),
        combo("Ad", "Td"),
        combo("Ks", "Jd"),
        combo("6c", "6d"),
    )
    return RiverGameSpec(board, p0, p1, pot=100, bet_sizes=tuple(bet_sizes))


def test_materialize_bet_sizes_clips_deduplicates_and_keeps_allin():
    assert materialize_bet_sizes(
        pot=100,
        stack=150,
        min_bet=20,
        fractions=(Fraction(1, 3), Fraction(3, 4), Fraction(2, 1)),
    ) == (33, 75, 150)
    assert materialize_bet_sizes(
        pot=100,
        stack=15,
        min_bet=20,
        fractions=(Fraction(1, 3), Fraction(1, 1)),
    ) == (15,)


def test_exact_best_response_bounds_policy_value():
    result = solve_river_cfr_plus(fixture_spec(), iterations=300)
    assert result.br0_value + 1e-9 >= result.policy_ev
    assert result.policy_ev + 1e-9 >= result.br1_value
    assert result.exploitability >= 0.0
    assert result.exploitability_per_pot == pytest.approx(result.exploitability / 100.0)


def test_solver_is_bitwise_deterministic_for_same_spec_and_budget():
    a = solve_river_cfr_plus(fixture_spec(), iterations=180)
    b = solve_river_cfr_plus(fixture_spec(), iterations=180)
    assert a == b


def test_richer_action_abstraction_expands_infoset_action_slots_predictably():
    narrow = solve_river_cfr_plus(fixture_spec((50,)), iterations=80)
    rich = solve_river_cfr_plus(fixture_spec((25, 75, 150)), iterations=80)
    assert narrow.infosets < rich.infosets
    assert narrow.action_slots < rich.action_slots
    assert narrow.infosets == 24  # (6 + 6) * (root-or-after-check + one response node)
    assert rich.infosets == 48    # (6 + 6) * (1 + three response nodes)


def test_more_training_reduces_exploitability_on_frozen_fixture():
    early = solve_river_cfr_plus(fixture_spec(), iterations=20)
    later = solve_river_cfr_plus(fixture_spec(), iterations=600)
    assert later.exploitability_per_pot < early.exploitability_per_pot
