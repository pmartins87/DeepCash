import json

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import RangeCombo
from deepcash_core.river_raise_reference_lab import (
    AsymmetricRiverRaiseGameSpec,
    solve_asymmetric_river_raise_cfr_plus,
)
from deepcash_core.river_raise_reference_training import (
    advance_cfr_plus,
    init_cfr_plus,
    result_from_state,
    state_from_dict,
    state_to_dict,
)


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str) -> RangeCombo:
    return RangeCombo((c(a), c(b)))


def spec() -> AsymmetricRiverRaiseGameSpec:
    return AsymmetricRiverRaiseGameSpec(
        board=(c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h")),
        p0_range=(combo("Qs", "Qh"), combo("Ac", "Qc")),
        p1_range=(combo("Qd", "Jh"), combo("Ad", "Td")),
        pot=100,
        p0_bet_sizes=(25, 75),
        p1_bet_sizes=(50,),
        p1_raise_targets_vs_p0=((25, (100,)), (75, (200,))),
        p0_raise_targets_vs_p1=((50, (150,)),),
    )


def test_staged_one_raise_training_matches_monolithic_solver():
    game = spec()
    expected = solve_asymmetric_river_raise_cfr_plus(game, iterations=200)
    state = init_cfr_plus(game)
    advance_cfr_plus(game, state, additional_iterations=17)
    advance_cfr_plus(game, state, additional_iterations=83)
    advance_cfr_plus(game, state, additional_iterations=100)
    actual = result_from_state(game, state)
    assert actual.policy == expected.policy
    assert actual.policy_ev == expected.policy_ev
    assert actual.br0_value == pytest.approx(expected.br0_value, abs=1e-12)
    assert actual.br1_value == pytest.approx(expected.br1_value, abs=1e-12)
    assert actual.exploitability == pytest.approx(expected.exploitability, abs=1e-12)


def test_one_raise_checkpoint_json_roundtrip_preserves_future_path():
    game = spec()
    state = init_cfr_plus(game)
    advance_cfr_plus(game, state, additional_iterations=60)
    payload = json.loads(json.dumps(state_to_dict(state)))
    restored = state_from_dict(game, payload)
    assert restored.regrets == state.regrets
    assert restored.strategy_sum == state.strategy_sum

    advance_cfr_plus(game, state, additional_iterations=90)
    advance_cfr_plus(game, restored, additional_iterations=90)
    assert restored.regrets == state.regrets
    assert restored.strategy_sum == state.strategy_sum
    assert result_from_state(game, restored) == result_from_state(game, state)


def test_one_raise_checkpoint_rejects_different_raise_geometry():
    game = spec()
    state = init_cfr_plus(game)
    other = AsymmetricRiverRaiseGameSpec(
        board=game.board,
        p0_range=game.p0_range,
        p1_range=game.p1_range,
        pot=game.pot,
        p0_bet_sizes=game.p0_bet_sizes,
        p1_bet_sizes=game.p1_bet_sizes,
        p1_raise_targets_vs_p0=((25, (125,)), (75, (225,))),
        p0_raise_targets_vs_p1=game.p0_raise_targets_vs_p1,
    )
    with pytest.raises(ValueError, match="different one-raise river game spec"):
        advance_cfr_plus(other, state, additional_iterations=1)
