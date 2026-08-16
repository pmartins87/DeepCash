import inspect
import json

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_external_sampling import (
    ExternalSamplingVariant,
    advance_external_sampling,
    init_external_sampling,
)
from deepcash_core.river_lab import RangeCombo, RiverGameSpec
from deepcash_core.river_vr_tabular import (
    _estimate_then_update_running_baseline,
    advance_tabular_vr,
    init_tabular_vr,
    tabular_vr_state_from_dict,
    tabular_vr_state_to_dict,
)
from deepcash_core.vr_mccfr_baseline import baseline_enhanced_node_value


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str, weight: float = 1.0) -> RangeCombo:
    return RangeCombo((c(a), c(b)), weight)


def fixture_spec() -> RiverGameSpec:
    return RiverGameSpec(
        board=(c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h")),
        p0_range=(
            combo("Qs", "Qh", 0.4),
            combo("Jc", "Js", 1.3),
            combo("8c", "8d", 0.8),
        ),
        p1_range=(
            combo("Qd", "Jh", 1.1),
            combo("Jd", "Th", 0.5),
            combo("6c", "6d", 1.7),
        ),
        pot=100,
        bet_sizes=(25, 50, 100),
    )


def test_tabular_baseline_key_has_no_realized_opponent_hand_component():
    spec = fixture_spec()
    state = init_tabular_vr(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=7
    )
    for key in state.baseline_mean:
        assert len(key) == 4
        traverser, own_hand, acting_player, public_node = key
        assert acting_player == 1 - traverser
        assert isinstance(own_hand, int)
        assert isinstance(public_node, str)

    # The state constructor/training API receives the game and seed, not a
    # realized opponent hand. Hidden opponent identity can affect a sampled
    # child return but never baseline identity.
    params = inspect.signature(init_tabular_vr).parameters
    assert "opponent_hand_index" not in params
    assert "realized_opponent_hand" not in params


def test_running_baseline_uses_old_value_before_current_sample_update():
    sigma = (0.25, 0.75)
    means = [10.0, -4.0]
    counts = [5, 3]
    sampled = 1
    child = 20.0
    frozen = tuple(means)
    expected = baseline_enhanced_node_value(
        target_policy=sigma,
        sampling_policy=sigma,
        baselines=frozen,
        sampled_action=sampled,
        sampled_child_value=child,
    )

    observed = _estimate_then_update_running_baseline(
        sigma=sigma,
        means=means,
        counts=counts,
        sampled_action=sampled,
        sampled_child_value=child,
    )
    assert observed == pytest.approx(expected, abs=1e-12)
    assert counts == [5, 4]
    assert means[0] == 10.0
    assert means[1] == pytest.approx((-4.0 * 3.0 + 20.0) / 4.0, abs=1e-12)


def test_first_iteration_matches_zero_baseline_external_update():
    spec = fixture_spec()
    ordinary = init_external_sampling(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=20260816
    )
    tabular = init_tabular_vr(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=20260816
    )
    advance_external_sampling(spec, ordinary, additional_iterations=1)
    advance_tabular_vr(spec, tabular, additional_iterations=1)

    # Every baseline starts at zero and is consumed before its first update, so
    # the first solver iteration is exactly the ZERO control path.
    assert tabular.base == ordinary
    assert sum(sum(v) for v in tabular.baseline_count.values()) > 0


def test_tabular_same_seed_is_fully_deterministic():
    spec = fixture_spec()
    first = init_tabular_vr(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=101
    )
    second = init_tabular_vr(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=101
    )
    advance_tabular_vr(spec, first, additional_iterations=400)
    advance_tabular_vr(spec, second, additional_iterations=400)
    assert first == second


def test_tabular_staged_training_matches_monolithic_exactly():
    spec = fixture_spec()
    mono = init_tabular_vr(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=29
    )
    staged = init_tabular_vr(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=29
    )
    advance_tabular_vr(spec, mono, additional_iterations=500)
    advance_tabular_vr(spec, staged, additional_iterations=125)
    advance_tabular_vr(spec, staged, additional_iterations=375)
    assert staged == mono


def test_tabular_json_roundtrip_preserves_exact_future_path():
    spec = fixture_spec()
    original = init_tabular_vr(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=503
    )
    advance_tabular_vr(spec, original, additional_iterations=173)
    payload = json.loads(json.dumps(tabular_vr_state_to_dict(original)))
    restored = tabular_vr_state_from_dict(
        spec,
        payload,
        expected_variant=ExternalSamplingVariant.ES_CFR_PLUS_LINEAR,
    )
    assert restored == original

    advance_tabular_vr(spec, original, additional_iterations=327)
    advance_tabular_vr(spec, restored, additional_iterations=327)
    assert restored == original


def test_tabular_checkpoint_fails_closed_for_wrong_variant():
    spec = fixture_spec()
    state = init_tabular_vr(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=11
    )
    payload = tabular_vr_state_to_dict(state)
    with pytest.raises(ValueError):
        tabular_vr_state_from_dict(
            spec,
            payload,
            expected_variant=ExternalSamplingVariant.ES_CFR_LINEAR,
        )
