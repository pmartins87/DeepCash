import json

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import RangeCombo
from deepcash_core.river_reference_lab import (
    AsymmetricRiverGameSpec,
    solve_asymmetric_river_cfr_plus,
)
from deepcash_core.river_reference_training import (
    advance_asymmetric_river_cfr_plus,
    asymmetric_cfr_state_from_dict,
    asymmetric_cfr_state_to_dict,
    asymmetric_result_from_state,
    init_asymmetric_river_cfr_plus,
)


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str) -> RangeCombo:
    return RangeCombo((c(a), c(b)))


def spec(p0_sizes=(25, 75), p1_sizes=(25, 75, 150)) -> AsymmetricRiverGameSpec:
    return AsymmetricRiverGameSpec(
        board=(c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h")),
        p0_range=(
            combo("Qs", "Qh"),
            combo("Jc", "Js"),
            combo("Ac", "Qc"),
        ),
        p1_range=(
            combo("Qd", "Jh"),
            combo("Jd", "Th"),
            combo("Ad", "Td"),
        ),
        pot=100,
        p0_bet_sizes=tuple(p0_sizes),
        p1_bet_sizes=tuple(p1_sizes),
    )


def test_asymmetric_staged_resume_exactly_matches_monolithic_solver():
    game = spec()
    expected = solve_asymmetric_river_cfr_plus(game, iterations=240)
    state = init_asymmetric_river_cfr_plus(game)
    advance_asymmetric_river_cfr_plus(game, state, additional_iterations=17)
    advance_asymmetric_river_cfr_plus(game, state, additional_iterations=83)
    advance_asymmetric_river_cfr_plus(game, state, additional_iterations=140)
    actual = asymmetric_result_from_state(game, state)
    assert state.iterations == 240
    assert actual == expected


def test_asymmetric_json_roundtrip_preserves_exact_future_path():
    game = spec()
    state = init_asymmetric_river_cfr_plus(game)
    advance_asymmetric_river_cfr_plus(game, state, additional_iterations=70)
    payload = json.loads(json.dumps(asymmetric_cfr_state_to_dict(state)))
    restored = asymmetric_cfr_state_from_dict(game, payload)
    assert restored.regrets == state.regrets
    assert restored.strategy_sum == state.strategy_sum
    assert restored.iterations == state.iterations

    advance_asymmetric_river_cfr_plus(game, state, additional_iterations=90)
    advance_asymmetric_river_cfr_plus(game, restored, additional_iterations=90)
    assert restored.regrets == state.regrets
    assert restored.strategy_sum == state.strategy_sum
    assert asymmetric_result_from_state(game, restored) == asymmetric_result_from_state(game, state)


def test_asymmetric_checkpoint_rejects_different_action_sets():
    game = spec()
    state = init_asymmetric_river_cfr_plus(game)
    other = spec(p0_sizes=(50,), p1_sizes=(25, 75, 150))
    with pytest.raises(ValueError, match="different asymmetric river game spec"):
        advance_asymmetric_river_cfr_plus(other, state, additional_iterations=1)


def test_asymmetric_untrained_state_cannot_be_presented_as_solution():
    game = spec()
    state = init_asymmetric_river_cfr_plus(game)
    with pytest.raises(ValueError, match="untrained"):
        asymmetric_result_from_state(game, state)
