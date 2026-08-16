import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import RangeCombo
from deepcash_core.river_raise_lab import (
    RiverRaiseGameSpec,
    actions,
    all_infosets,
    exact_best_response_values,
    solve_river_raise_cfr_plus,
)


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str) -> RangeCombo:
    return RangeCombo((c(a), c(b)))


def fixture() -> RiverRaiseGameSpec:
    return RiverRaiseGameSpec(
        board=(c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h")),
        p0_range=(combo("Qs", "Qh"), combo("Jc", "Js"), combo("Ac", "Qc")),
        p1_range=(combo("Qd", "Jh"), combo("Jd", "Th"), combo("Ad", "Td")),
        pot=100,
        bet_sizes=(50,),
        raise_targets=((50, (150,)),),
    )


def test_one_raise_tree_has_expected_infosets_and_action_slots():
    spec = fixture()
    infosets = all_infosets(spec)
    assert len(infosets) == 18
    slots = sum(len(actions(spec, key[0], key[1])) for key in infosets)
    assert slots == 42


def test_raise_targets_are_exact_and_must_exceed_opening_bet():
    with pytest.raises(ValueError, match="exceed"):
        RiverRaiseGameSpec(
            board=fixture().board,
            p0_range=fixture().p0_range,
            p1_range=fixture().p1_range,
            pot=100,
            bet_sizes=(50,),
            raise_targets=((50, (50,)),),
        )


def test_exact_best_response_bounds_average_policy_value():
    result = solve_river_raise_cfr_plus(fixture(), iterations=250)
    assert result.br0_value + 1e-9 >= result.policy_ev
    assert result.policy_ev + 1e-9 >= result.br1_value
    br0, br1 = exact_best_response_values(fixture(), result.policy)
    assert br0 == result.br0_value
    assert br1 == result.br1_value


def test_one_raise_solver_is_deterministic():
    a = solve_river_raise_cfr_plus(fixture(), iterations=180)
    b = solve_river_raise_cfr_plus(fixture(), iterations=180)
    assert a == b


def test_one_raise_cfr_converges_on_frozen_fixture():
    early = solve_river_raise_cfr_plus(fixture(), iterations=20)
    later = solve_river_raise_cfr_plus(fixture(), iterations=500)
    assert later.exploitability_per_pot < early.exploitability_per_pot


def test_single_combo_known_nuts_converges_to_sunk_pot_half_value():
    spec = RiverRaiseGameSpec(
        board=(c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h")),
        p0_range=(combo("Ac", "Ad"),),
        p1_range=(combo("Qc", "Qd"),),
        pot=100,
        bet_sizes=(50,),
        raise_targets=((50, (150,)),),
    )
    result = solve_river_raise_cfr_plus(spec, iterations=600)
    assert result.policy_ev == pytest.approx(50.0, abs=0.5)
    assert result.exploitability_per_pot < 0.005
