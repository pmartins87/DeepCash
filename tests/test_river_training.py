import json

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import RangeCombo, RiverGameSpec, solve_river_cfr_plus
from deepcash_core.river_training import (
    advance_river_cfr_plus,
    init_river_cfr_plus,
    river_cfr_state_from_dict,
    river_cfr_state_to_dict,
    river_result_from_state,
)


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str) -> RangeCombo:
    return RangeCombo((c(a), c(b)))


def spec() -> RiverGameSpec:
    return RiverGameSpec(
        board=(c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h")),
        p0_range=(
            combo("Qs", "Qh"),
            combo("Jc", "Js"),
            combo("Tc", "Ts"),
            combo("Ac", "Qc"),
        ),
        p1_range=(
            combo("Qd", "Jh"),
            combo("Jd", "Th"),
            combo("9d", "8h"),
            combo("Ad", "Td"),
        ),
        pot=100,
        bet_sizes=(33, 100),
    )


def test_staged_resume_is_exactly_equal_to_monolithic_legacy_solver():
    game = spec()
    expected = solve_river_cfr_plus(game, iterations=300)

    state = init_river_cfr_plus(game)
    advance_river_cfr_plus(game, state, additional_iterations=37)
    advance_river_cfr_plus(game, state, additional_iterations=63)
    advance_river_cfr_plus(game, state, additional_iterations=200)
    actual = river_result_from_state(game, state)

    assert state.iterations == 300
    assert actual == expected


def test_checkpoint_json_roundtrip_preserves_exact_future_training_path():
    game = spec()
    staged = init_river_cfr_plus(game)
    advance_river_cfr_plus(game, staged, additional_iterations=75)

    payload = json.loads(json.dumps(river_cfr_state_to_dict(staged)))
    restored = river_cfr_state_from_dict(game, payload)
    assert restored.iterations == staged.iterations
    assert restored.regrets == staged.regrets
    assert restored.strategy_sum == staged.strategy_sum

    advance_river_cfr_plus(game, staged, additional_iterations=125)
    advance_river_cfr_plus(game, restored, additional_iterations=125)
    assert staged.regrets == restored.regrets
    assert staged.strategy_sum == restored.strategy_sum
    assert river_result_from_state(game, staged) == river_result_from_state(game, restored)


def test_checkpoint_refuses_different_game_spec():
    game = spec()
    state = init_river_cfr_plus(game)
    other = RiverGameSpec(
        board=game.board,
        p0_range=game.p0_range,
        p1_range=game.p1_range,
        pot=101,
        bet_sizes=game.bet_sizes,
    )
    with pytest.raises(ValueError, match="different river game spec"):
        advance_river_cfr_plus(other, state, additional_iterations=1)


def test_zero_iteration_advance_is_identity_but_untrained_result_is_rejected():
    game = spec()
    state = init_river_cfr_plus(game)
    before = river_cfr_state_to_dict(state)
    assert advance_river_cfr_plus(game, state, additional_iterations=0) is state
    assert river_cfr_state_to_dict(state) == before
    with pytest.raises(ValueError, match="untrained"):
        river_result_from_state(game, state)
