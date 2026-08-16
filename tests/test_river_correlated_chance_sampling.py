import json

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_correlated_chance_sampling import (
    GOLDEN_ROTATION,
    advance_correlated_chance,
    correlated_chance_result,
    correlated_chance_state_from_dict,
    correlated_chance_state_to_dict,
    init_correlated_chance,
    weighted_quantile_index,
    weyl_phase,
)
from deepcash_core.river_lab import RangeCombo, RiverGameSpec


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


def test_weyl_phase_matches_frozen_formula():
    phi = 0.123456789
    assert weyl_phase(phi, 0) == pytest.approx(phi)
    assert weyl_phase(phi, 1) == pytest.approx((phi + GOLDEN_ROTATION) % 1.0)
    assert weyl_phase(phi, 17) == pytest.approx(
        (phi + 17.0 * GOLDEN_ROTATION) % 1.0
    )


def test_weighted_quantile_boundaries_are_left_closed_right_open():
    weights = (1.0, 2.0, 1.0)
    assert weighted_quantile_index(weights, 0.0) == 0
    assert weighted_quantile_index(weights, 0.249999999) == 0
    assert weighted_quantile_index(weights, 0.25) == 1
    assert weighted_quantile_index(weights, 0.749999999) == 1
    assert weighted_quantile_index(weights, 0.75) == 2
    assert weighted_quantile_index(weights, 0.999999999) == 2


def test_same_seed_is_bit_identical():
    spec = fixture_spec()
    a = init_correlated_chance(spec, seed=20260816)
    b = init_correlated_chance(spec, seed=20260816)
    assert a.phase == b.phase
    advance_correlated_chance(spec, a, additional_iterations=500)
    advance_correlated_chance(spec, b, additional_iterations=500)
    assert a == b
    assert correlated_chance_result(spec, a) == correlated_chance_result(spec, b)


def test_staged_matches_monolithic_exactly():
    spec = fixture_spec()
    staged = init_correlated_chance(spec, seed=29)
    advance_correlated_chance(spec, staged, additional_iterations=125)
    advance_correlated_chance(spec, staged, additional_iterations=375)

    monolithic = init_correlated_chance(spec, seed=29)
    advance_correlated_chance(spec, monolithic, additional_iterations=500)
    assert staged == monolithic
    assert correlated_chance_result(spec, staged) == correlated_chance_result(
        spec, monolithic
    )


def test_json_roundtrip_preserves_stream_and_future_path():
    spec = fixture_spec()
    state = init_correlated_chance(spec, seed=101)
    advance_correlated_chance(spec, state, additional_iterations=140)
    payload = json.loads(json.dumps(correlated_chance_state_to_dict(state)))
    restored = correlated_chance_state_from_dict(spec, payload)
    assert restored == state

    advance_correlated_chance(spec, state, additional_iterations=360)
    advance_correlated_chance(spec, restored, additional_iterations=360)
    assert restored == state
    assert correlated_chance_result(spec, restored) == correlated_chance_result(
        spec, state
    )


def test_visit_index_and_terminal_visits_are_exact():
    spec = fixture_spec()
    state = init_correlated_chance(spec, seed=11)
    advance_correlated_chance(spec, state, additional_iterations=100)
    assert state.visit_index == state.iterations == 100
    assert state.terminal_visits == 100 * (1 + 4 * len(spec.bet_sizes))


def test_corrupted_phase_visit_and_nonfinite_state_fail_closed():
    spec = fixture_spec()
    state = init_correlated_chance(spec, seed=11)
    payload = correlated_chance_state_to_dict(state)

    bad = json.loads(json.dumps(payload))
    bad["phase"] = 1.0
    with pytest.raises(ValueError, match="phase"):
        correlated_chance_state_from_dict(spec, bad)

    bad = json.loads(json.dumps(payload))
    bad["visit_index"] = 1
    with pytest.raises(ValueError, match="visit index"):
        correlated_chance_state_from_dict(spec, bad)

    bad = json.loads(json.dumps(payload))
    key = next(iter(bad["regrets"]))
    bad["regrets"][key][0] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        correlated_chance_state_from_dict(spec, bad)
