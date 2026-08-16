import random

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_external_sampling import (
    ExternalSamplingVariant,
    advance_external_sampling,
    init_external_sampling,
)
from deepcash_core.river_lab import (
    RangeCombo,
    RiverGameSpec,
    _actions,
    _all_infosets,
    _regret_strategy,
    p1_vs_bet_node,
)
from deepcash_core.river_vr_external_sampling import (
    VRBaselineMode,
    _vr_external_traverse,
    advance_vr_external_sampling,
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


@pytest.mark.parametrize("variant", list(ExternalSamplingVariant))
def test_zero_baseline_vr_is_bit_identical_to_ordinary_external_sampling(variant):
    spec = fixture_spec()
    ordinary = init_external_sampling(spec, variant, seed=20260816)
    zero_vr = init_external_sampling(spec, variant, seed=20260816)

    advance_external_sampling(spec, ordinary, additional_iterations=1000)
    advance_vr_external_sampling(
        spec,
        zero_vr,
        additional_iterations=1000,
        baseline_mode=VRBaselineMode.ZERO,
    )
    assert zero_vr == ordinary


def test_zero_baseline_staged_path_remains_identical_to_ordinary_external():
    spec = fixture_spec()
    ordinary = init_external_sampling(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=29
    )
    zero_vr = init_external_sampling(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=29
    )
    advance_external_sampling(spec, ordinary, additional_iterations=125)
    advance_external_sampling(spec, ordinary, additional_iterations=375)
    advance_vr_external_sampling(
        spec, zero_vr, additional_iterations=125, baseline_mode=VRBaselineMode.ZERO
    )
    advance_vr_external_sampling(
        spec, zero_vr, additional_iterations=375, baseline_mode=VRBaselineMode.ZERO
    )
    assert zero_vr == ordinary


def _fixed_node_value(spec, *, seed: int, mode: VRBaselineMode) -> float:
    infosets = _all_infosets(spec)
    zero_regrets = {
        key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets
    }
    strategies = {key: _regret_strategy(zero_regrets[key]) for key in infosets}
    delta = {key: [0.0] * len(zero_regrets[key]) for key in infosets}
    counter = [0]
    return _vr_external_traverse(
        spec,
        i=0,
        j=0,
        traverser=0,
        rng=random.Random(seed),
        strategies=strategies,
        regret_delta=delta,
        counter=counter,
        baseline_mode=mode,
        node=p1_vs_bet_node(25),
        player=1,
    )


def test_perfect_history_baseline_eliminates_sampled_opponent_action_variance_at_fixed_history():
    spec = fixture_spec()
    perfect_values = {
        _fixed_node_value(spec, seed=seed, mode=VRBaselineMode.PERFECT_HISTORY)
        for seed in range(50)
    }
    assert len(perfect_values) == 1

    zero_values = {
        _fixed_node_value(spec, seed=seed, mode=VRBaselineMode.ZERO)
        for seed in range(50)
    }
    # The response node has FOLD/CALL actions with distinct values in this fixed
    # history, so ordinary sampling must retain action-sampling variance.
    assert len(zero_values) > 1


def test_perfect_history_mode_is_explicitly_distinct_from_zero_baseline_training():
    spec = fixture_spec()
    zero = init_external_sampling(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=101
    )
    perfect = init_external_sampling(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=101
    )
    advance_vr_external_sampling(
        spec, zero, additional_iterations=200, baseline_mode=VRBaselineMode.ZERO
    )
    advance_vr_external_sampling(
        spec,
        perfect,
        additional_iterations=200,
        baseline_mode=VRBaselineMode.PERFECT_HISTORY,
    )
    assert perfect.regrets != zero.regrets
    # Perfect-history oracle enumerates hidden-history continuations and is only
    # an implementation lower bound; it must never be silently confused with
    # the production-eligible zero/no-leak paths.
    assert perfect.terminal_visits > zero.terminal_visits
