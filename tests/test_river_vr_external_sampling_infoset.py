import inspect

from deepcash_core.cards import card_from_str
from deepcash_core.river_external_sampling import (
    ExternalSamplingVariant,
    init_external_sampling,
)
from deepcash_core.river_lab import RangeCombo, RiverGameSpec
from deepcash_core.river_vr_external_sampling import (
    VRBaselineMode,
    advance_vr_external_sampling,
)
from deepcash_core.river_vr_infoset_baseline_v2 import (
    exact_infoset_action_baselines_v2,
)


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


def test_infoset_exact_baseline_api_has_no_realized_opponent_hand_parameter():
    params = inspect.signature(exact_infoset_action_baselines_v2).parameters
    assert "i" not in params
    assert "j" not in params
    assert "opponent_hand_index" not in params
    assert "realized_opponent_hand" not in params
    assert "own_hand_index" in params


def test_infoset_exact_checkpoint_partition_preserves_exact_future_path():
    spec = fixture_spec()
    mono = init_external_sampling(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=20260816
    )
    staged = init_external_sampling(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=20260816
    )

    advance_vr_external_sampling(
        spec,
        mono,
        additional_iterations=500,
        baseline_mode=VRBaselineMode.INFOSET_EXACT,
    )
    advance_vr_external_sampling(
        spec,
        staged,
        additional_iterations=125,
        baseline_mode=VRBaselineMode.INFOSET_EXACT,
    )
    advance_vr_external_sampling(
        spec,
        staged,
        additional_iterations=375,
        baseline_mode=VRBaselineMode.INFOSET_EXACT,
    )
    assert staged == mono


def test_infoset_exact_is_a_real_control_variate_not_zero_alias():
    spec = fixture_spec()
    zero = init_external_sampling(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=29
    )
    infoset = init_external_sampling(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=29
    )
    advance_vr_external_sampling(
        spec, zero, additional_iterations=300, baseline_mode=VRBaselineMode.ZERO
    )
    advance_vr_external_sampling(
        spec,
        infoset,
        additional_iterations=300,
        baseline_mode=VRBaselineMode.INFOSET_EXACT,
    )

    # A control variate changes regret estimates and therefore can change all
    # later strategy-dependent sampled trajectories.  Cross-mode RNG-state or
    # terminal-visit equality is not a valid invariant.  What matters here is
    # that INFOSET_EXACT is actually distinct while remaining a valid state.
    assert infoset.iterations == zero.iterations == 300
    assert infoset.regrets != zero.regrets
    infoset.validate(spec)
    zero.validate(spec)


def test_infoset_exact_same_seed_is_fully_deterministic():
    spec = fixture_spec()
    first = init_external_sampling(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=101
    )
    second = init_external_sampling(
        spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=101
    )

    advance_vr_external_sampling(
        spec,
        first,
        additional_iterations=400,
        baseline_mode=VRBaselineMode.INFOSET_EXACT,
    )
    advance_vr_external_sampling(
        spec,
        second,
        additional_iterations=400,
        baseline_mode=VRBaselineMode.INFOSET_EXACT,
    )

    assert first == second
    assert first.terminal_visits > 0
