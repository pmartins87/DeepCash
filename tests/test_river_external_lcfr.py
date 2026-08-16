import json

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_external_lcfr import (
    AlternatingExternalVariant,
    _apply_player_regrets,
    advance_alternating_external,
    alternating_external_result,
    alternating_external_state_from_dict,
    alternating_external_state_to_dict,
    init_alternating_external,
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


@pytest.mark.parametrize("variant", list(AlternatingExternalVariant))
def test_same_seed_is_bit_identical(variant):
    spec = fixture_spec()
    a = init_alternating_external(spec, variant, seed=20260816)
    b = init_alternating_external(spec, variant, seed=20260816)
    advance_alternating_external(spec, a, additional_iterations=400)
    advance_alternating_external(spec, b, additional_iterations=400)
    assert a == b
    assert alternating_external_result(spec, a) == alternating_external_result(spec, b)


@pytest.mark.parametrize("variant", list(AlternatingExternalVariant))
def test_staged_matches_monolithic(variant):
    spec = fixture_spec()
    staged = init_alternating_external(spec, variant, seed=29)
    advance_alternating_external(spec, staged, additional_iterations=100)
    advance_alternating_external(spec, staged, additional_iterations=300)

    monolithic = init_alternating_external(spec, variant, seed=29)
    advance_alternating_external(spec, monolithic, additional_iterations=400)
    assert staged == monolithic
    assert alternating_external_result(spec, staged) == alternating_external_result(
        spec, monolithic
    )


@pytest.mark.parametrize("variant", list(AlternatingExternalVariant))
def test_json_roundtrip_preserves_future_rng_path(variant):
    spec = fixture_spec()
    state = init_alternating_external(spec, variant, seed=101)
    advance_alternating_external(spec, state, additional_iterations=125)
    payload = json.loads(json.dumps(alternating_external_state_to_dict(state)))
    restored = alternating_external_state_from_dict(
        spec, payload, expected_variant=variant
    )
    assert restored == state

    advance_alternating_external(spec, state, additional_iterations=275)
    advance_alternating_external(spec, restored, additional_iterations=275)
    assert restored == state


def test_lcfr_regret_accumulator_is_exact_linear_weighted_sum():
    spec = fixture_spec()
    state = init_alternating_external(
        spec, AlternatingExternalVariant.ALT_ES_LCFR, seed=1
    )
    key = next(key for key in state.regrets if key[0] == 0)
    action_count = len(state.regrets[key])

    delta1 = {k: [0.0] * len(v) for k, v in state.regrets.items()}
    delta2 = {k: [0.0] * len(v) for k, v in state.regrets.items()}
    delta1[key][0] = 2.0
    delta2[key][0] = 3.0
    if action_count > 1:
        delta1[key][1] = -1.0
        delta2[key][1] = 4.0

    _apply_player_regrets(state, delta1, player=0, iteration=1)
    _apply_player_regrets(state, delta2, player=0, iteration=2)
    assert state.regrets[key][0] == pytest.approx(1.0 * 2.0 + 2.0 * 3.0)
    if action_count > 1:
        assert state.regrets[key][1] == pytest.approx(1.0 * -1.0 + 2.0 * 4.0)


def test_lcfr_regret_update_cannot_mutate_other_player():
    spec = fixture_spec()
    state = init_alternating_external(
        spec, AlternatingExternalVariant.ALT_ES_LCFR, seed=1
    )
    delta = {k: [1.0] * len(v) for k, v in state.regrets.items()}
    before_p1 = {k: tuple(v) for k, v in state.regrets.items() if k[0] == 1}
    _apply_player_regrets(state, delta, player=0, iteration=7)
    after_p1 = {k: tuple(v) for k, v in state.regrets.items() if k[0] == 1}
    assert after_p1 == before_p1


def test_uniform_linear_average_and_lcfr_are_materially_distinct():
    spec = fixture_spec()
    states = {}
    for variant in AlternatingExternalVariant:
        state = init_alternating_external(spec, variant, seed=11)
        advance_alternating_external(spec, state, additional_iterations=300)
        states[variant] = state

    assert states[AlternatingExternalVariant.ALT_ES_CFR_UNIFORM].strategy_sum != (
        states[AlternatingExternalVariant.ALT_ES_CFR_LINEAR_AVG].strategy_sum
    )
    assert states[AlternatingExternalVariant.ALT_ES_CFR_LINEAR_AVG].regrets != (
        states[AlternatingExternalVariant.ALT_ES_LCFR].regrets
    )


def test_wrong_variant_and_nonfinite_state_fail_closed():
    spec = fixture_spec()
    state = init_alternating_external(
        spec, AlternatingExternalVariant.ALT_ES_CFR_UNIFORM, seed=1
    )
    payload = alternating_external_state_to_dict(state)
    with pytest.raises(ValueError, match="variant"):
        alternating_external_state_from_dict(
            spec,
            payload,
            expected_variant=AlternatingExternalVariant.ALT_ES_LCFR,
        )

    payload = alternating_external_state_to_dict(state)
    key = next(iter(payload["regrets"]))
    payload["regrets"][key][0] = float("inf")
    with pytest.raises(ValueError, match="non-finite"):
        alternating_external_state_from_dict(spec, payload)
