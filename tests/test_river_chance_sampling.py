import json

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_chance_sampling import (
    ChanceSamplingVariant,
    advance_chance_sampling,
    chance_sampling_result,
    chance_sampling_state_from_dict,
    chance_sampling_state_to_dict,
    init_chance_sampling,
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


@pytest.mark.parametrize("variant", list(ChanceSamplingVariant))
def test_same_seed_is_bit_identical(variant):
    spec = fixture_spec()
    a = init_chance_sampling(spec, variant, seed=12345)
    b = init_chance_sampling(spec, variant, seed=12345)
    advance_chance_sampling(spec, a, additional_iterations=250)
    advance_chance_sampling(spec, b, additional_iterations=250)
    assert a == b
    assert chance_sampling_result(spec, a) == chance_sampling_result(spec, b)


@pytest.mark.parametrize("variant", list(ChanceSamplingVariant))
def test_staged_matches_monolithic_exactly(variant):
    spec = fixture_spec()
    staged = init_chance_sampling(spec, variant, seed=777)
    advance_chance_sampling(spec, staged, additional_iterations=75)
    advance_chance_sampling(spec, staged, additional_iterations=175)

    monolithic = init_chance_sampling(spec, variant, seed=777)
    advance_chance_sampling(spec, monolithic, additional_iterations=250)
    assert staged == monolithic
    assert chance_sampling_result(spec, staged) == chance_sampling_result(spec, monolithic)


@pytest.mark.parametrize("variant", list(ChanceSamplingVariant))
def test_json_roundtrip_preserves_future_rng_path(variant):
    spec = fixture_spec()
    state = init_chance_sampling(spec, variant, seed=20260816)
    advance_chance_sampling(spec, state, additional_iterations=90)
    payload = json.loads(json.dumps(chance_sampling_state_to_dict(state)))
    restored = chance_sampling_state_from_dict(spec, payload, expected_variant=variant)
    assert restored == state

    advance_chance_sampling(spec, state, additional_iterations=160)
    advance_chance_sampling(spec, restored, additional_iterations=160)
    assert restored == state
    assert chance_sampling_result(spec, restored) == chance_sampling_result(spec, state)


def test_wrong_variant_fails_closed():
    spec = fixture_spec()
    state = init_chance_sampling(spec, ChanceSamplingVariant.CS_CFR_LINEAR, seed=1)
    payload = chance_sampling_state_to_dict(state)
    with pytest.raises(ValueError, match="variant"):
        chance_sampling_state_from_dict(
            spec, payload, expected_variant=ChanceSamplingVariant.CS_CFR_PLUS_LINEAR
        )


def test_nonfinite_checkpoint_fails_closed():
    spec = fixture_spec()
    state = init_chance_sampling(spec, ChanceSamplingVariant.CS_CFR_LINEAR, seed=1)
    payload = chance_sampling_state_to_dict(state)
    key = next(iter(payload["regrets"]))
    payload["regrets"][key][0] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        chance_sampling_state_from_dict(spec, payload)


def test_terminal_visit_count_matches_full_action_tree_per_sampled_deal():
    spec = fixture_spec()
    state = init_chance_sampling(
        spec, ChanceSamplingVariant.CS_CFR_PLUS_LINEAR, seed=42
    )
    advance_chance_sampling(spec, state, additional_iterations=100)
    assert state.terminal_visits == 100 * (1 + 4 * len(spec.bet_sizes))
    result = chance_sampling_result(spec, state)
    assert result.br1_value <= result.policy_ev + 1e-9
    assert result.policy_ev <= result.br0_value + 1e-9
