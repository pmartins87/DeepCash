import json

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_alternating_dcfr import (
    AlternatingVariant,
    _accumulate_player_average,
    _apply_player_update,
    _full_regret_delta,
    advance_alternating_solver,
    alternating_solver_result,
    alternating_state_from_dict,
    alternating_state_to_dict,
    dcfr_average_factor,
    dcfr_regret_factor,
    init_alternating_solver,
)
from deepcash_core.river_lab import (
    P1_AFTER_CHECK,
    RangeCombo,
    RiverGameSpec,
    _actions,
    _all_infosets,
    _regret_strategy,
)


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str) -> RangeCombo:
    return RangeCombo((c(a), c(b)))


def fixture_spec() -> RiverGameSpec:
    return RiverGameSpec(
        board=(c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h")),
        p0_range=(combo("Qs", "Qh"), combo("Jc", "Js"), combo("8c", "8d")),
        p1_range=(combo("Qd", "Jh"), combo("Jd", "Th"), combo("6c", "6d")),
        pot=100,
        bet_sizes=(25, 50, 100),
    )


@pytest.mark.parametrize("variant", list(AlternatingVariant))
def test_staged_matches_monolithic_for_all_alternating_variants(variant):
    spec = fixture_spec()
    staged = init_alternating_solver(spec, variant)
    advance_alternating_solver(spec, staged, additional_iterations=35)
    advance_alternating_solver(spec, staged, additional_iterations=65)

    monolithic = init_alternating_solver(spec, variant)
    advance_alternating_solver(spec, monolithic, additional_iterations=100)
    assert staged == monolithic
    assert alternating_solver_result(spec, staged) == alternating_solver_result(
        spec, monolithic
    )


@pytest.mark.parametrize("variant", list(AlternatingVariant))
def test_json_roundtrip_preserves_future_path(variant):
    spec = fixture_spec()
    state = init_alternating_solver(spec, variant)
    advance_alternating_solver(spec, state, additional_iterations=40)
    payload = json.loads(json.dumps(alternating_state_to_dict(state)))
    restored = alternating_state_from_dict(spec, payload, expected_variant=variant)
    assert restored == state

    advance_alternating_solver(spec, state, additional_iterations=60)
    advance_alternating_solver(spec, restored, additional_iterations=60)
    assert restored == state
    assert alternating_solver_result(spec, restored) == alternating_solver_result(
        spec, state
    )


def test_dcfr_factors_match_frozen_paper_formulas():
    assert dcfr_regret_factor(1, 1.5) == pytest.approx(0.5)
    assert dcfr_regret_factor(19, 0.0) == pytest.approx(0.5)
    assert dcfr_regret_factor(4, 0.5) == pytest.approx(2.0 / 3.0)
    assert dcfr_average_factor(1, 2.0) == pytest.approx(0.25)
    assert dcfr_average_factor(3, 2.0) == pytest.approx(9.0 / 16.0)


def test_player_half_step_cannot_mutate_other_players_regrets():
    spec = fixture_spec()
    state = init_alternating_solver(spec, AlternatingVariant.ALT_DCFR_150_0_2)
    infosets = _all_infosets(spec)
    strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
    delta = _full_regret_delta(spec, strategies)
    before_p1 = {key: tuple(values) for key, values in state.regrets.items() if key[0] == 1}
    _apply_player_update(state, delta, player=0, iteration=1)
    after_p1 = {key: tuple(values) for key, values in state.regrets.items() if key[0] == 1}
    assert after_p1 == before_p1
    assert any(
        any(abs(value) > 0.0 for value in values)
        for key, values in state.regrets.items()
        if key[0] == 0
    )


def test_dcfr_positive_and_negative_regrets_are_discounted_differently():
    spec = fixture_spec()
    state = init_alternating_solver(spec, AlternatingVariant.ALT_DCFR_150_0_2)
    key = next(key for key in state.regrets if key[0] == 0 and len(state.regrets[key]) >= 2)
    delta = {k: [0.0] * len(v) for k, v in state.regrets.items()}
    delta[key][0] = 8.0
    delta[key][1] = -8.0
    _apply_player_update(state, delta, player=0, iteration=4)
    positive_factor = dcfr_regret_factor(4, 1.5)
    negative_factor = dcfr_regret_factor(4, 0.0)
    assert state.regrets[key][0] == pytest.approx(8.0 * positive_factor)
    assert state.regrets[key][1] == pytest.approx(-8.0 * negative_factor)
    assert positive_factor > negative_factor


def test_player_local_average_mutates_only_requested_player():
    spec = fixture_spec()
    state = init_alternating_solver(spec, AlternatingVariant.ALT_CFR_PLUS_LINEAR)
    infosets = _all_infosets(spec)
    strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
    _accumulate_player_average(spec, state, strategies, player=0, iteration=1)
    assert any(sum(values) > 0.0 for key, values in state.strategy_sum.items() if key[0] == 0)
    assert all(sum(values) == 0.0 for key, values in state.strategy_sum.items() if key[0] == 1)


def test_p1_average_is_taken_after_p0_refresh_before_p1_refresh():
    spec = fixture_spec()
    state = init_alternating_solver(spec, AlternatingVariant.ALT_CFR_PLUS_LINEAR)
    infosets = _all_infosets(spec)

    initial = {key: _regret_strategy(state.regrets[key]) for key in infosets}
    _accumulate_player_average(spec, state, initial, player=0, iteration=1)
    delta0 = _full_regret_delta(spec, initial)
    _apply_player_update(state, delta0, player=0, iteration=1)

    refreshed = {key: _regret_strategy(state.regrets[key]) for key in infosets}
    _accumulate_player_average(spec, state, refreshed, player=1, iteration=1)

    # P1 has no prior own action before this root-after-check infoset, so at t=1
    # its accumulated average must equal the refreshed strategy exactly.
    key = (1, P1_AFTER_CHECK, 0)
    assert state.strategy_sum[key] == pytest.approx(refreshed[key])

    before_average = tuple(state.strategy_sum[key])
    delta1 = _full_regret_delta(spec, refreshed)
    _apply_player_update(state, delta1, player=1, iteration=1)
    assert tuple(state.strategy_sum[key]) == before_average


def test_linear_and_quadratic_output_weighting_are_materially_distinct():
    spec = fixture_spec()
    infosets = _all_infosets(spec)
    uniform = {
        key: tuple(
            1.0 / len(_actions(spec, key[0], key[1]))
            for _ in _actions(spec, key[0], key[1])
        )
        for key in infosets
    }
    biased = {}
    for key in infosets:
        n = len(_actions(spec, key[0], key[1]))
        biased[key] = tuple([1.0] + [0.0] * (n - 1))

    linear = init_alternating_solver(spec, AlternatingVariant.ALT_CFR_PLUS_LINEAR)
    quadratic = init_alternating_solver(
        spec, AlternatingVariant.ALT_CFR_PLUS_QUADRATIC
    )
    for state in (linear, quadratic):
        _accumulate_player_average(spec, state, uniform, player=1, iteration=1)
        _accumulate_player_average(spec, state, biased, player=1, iteration=2)

    key = (1, P1_AFTER_CHECK, 0)
    assert linear.strategy_sum[key] != quadratic.strategy_sum[key]
    # Quadratic weighting puts relatively more mass on the second, biased profile.
    assert quadratic.strategy_sum[key][0] / sum(quadratic.strategy_sum[key]) > (
        linear.strategy_sum[key][0] / sum(linear.strategy_sum[key])
    )


def test_wrong_variant_and_nonfinite_checkpoint_fail_closed():
    spec = fixture_spec()
    state = init_alternating_solver(spec, AlternatingVariant.ALT_CFR_PLUS_LINEAR)
    payload = alternating_state_to_dict(state)
    with pytest.raises(ValueError, match="variant"):
        alternating_state_from_dict(
            spec,
            payload,
            expected_variant=AlternatingVariant.ALT_DCFR_150_0_2,
        )

    payload = alternating_state_to_dict(state)
    key = next(iter(payload["strategy_sum"]))
    payload["strategy_sum"][key][0] = float("inf")
    with pytest.raises(ValueError, match="non-finite"):
        alternating_state_from_dict(spec, payload)
