import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import (
    P1_AFTER_CHECK,
    ROOT,
    RangeCombo,
    RiverGameSpec,
    _actions,
    _all_infosets,
    exact_best_response_values,
    p1_vs_bet_node,
)
from deepcash_core.river_representation_br import (
    bucket_constrained_best_response_values,
)
from deepcash_core.river_representation_lab import (
    RiverBucketMaps,
    exact_bucket_maps,
)
from deepcash_core.river_representation_training import (
    advance_representation_cfr_plus,
    init_representation_cfr_plus,
    representation_result_from_state,
)


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str, weight: float = 1.0) -> RangeCombo:
    return RangeCombo((c(a), c(b)), weight)


def fixture_spec() -> RiverGameSpec:
    return RiverGameSpec(
        board=(c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h")),
        p0_range=(
            combo("Qs", "Qh", 0.8),
            combo("4c", "3c", 0.2),
            combo("8c", "8d", 0.7),
        ),
        p1_range=(
            combo("Jd", "Jh", 1.0),
            combo("6c", "6d", 0.6),
        ),
        pot=100,
        bet_sizes=(25, 50),
    )


def uniform_policy(spec):
    return {
        key: tuple(
            1.0 / len(_actions(spec, key[0], key[1]))
            for _ in _actions(spec, key[0], key[1])
        )
        for key in _all_infosets(spec)
    }


def test_exact_bucket_maps_reproduce_unrestricted_exact_best_responses():
    spec = fixture_spec()
    policy = uniform_policy(spec)
    expected = exact_best_response_values(spec, policy)
    observed = bucket_constrained_best_response_values(
        spec, exact_bucket_maps(spec), policy
    )
    assert observed == pytest.approx(expected, abs=1e-12)


def test_merging_p0_private_hands_cannot_improve_p0_best_response():
    spec = fixture_spec()
    policy = uniform_policy(spec)

    # Make P1 check behind after P0 checks and call every P0 bet. Under this
    # fixed policy the strong and weak P0 hands prefer different root actions.
    for j in range(len(spec.p1_range)):
        root = (1, P1_AFTER_CHECK, j)
        root_actions = _actions(spec, 1, P1_AFTER_CHECK)
        policy[root] = tuple(1.0 if action == "CHECK" else 0.0 for action in root_actions)
        for bet in spec.bet_sizes:
            key = (1, p1_vs_bet_node(bet), j)
            actions = _actions(spec, 1, p1_vs_bet_node(bet))
            policy[key] = tuple(1.0 if action == "CALL" else 0.0 for action in actions)

    exact = exact_bucket_maps(spec)
    merged = RiverBucketMaps(
        p0=(0, 0, 1),
        p1=exact.p1,
        name="merge_first_two_p0",
    )
    exact_br0, exact_br1 = bucket_constrained_best_response_values(
        spec, exact, policy
    )
    merged_br0, merged_br1 = bucket_constrained_best_response_values(
        spec, merged, policy
    )

    assert merged_br0 < exact_br0
    # P1 remained exact, so its best response is unchanged.
    assert merged_br1 == pytest.approx(exact_br1, abs=1e-12)


def test_representation_training_result_uses_bucket_constrained_interval():
    spec = fixture_spec()
    maps = RiverBucketMaps(
        p0=(0, 0, 1),
        p1=(0, 1),
        name="p0_merged",
    )
    state = init_representation_cfr_plus(spec, maps)
    advance_representation_cfr_plus(spec, maps, state, additional_iterations=80)
    result = representation_result_from_state(spec, maps, state)
    expected = bucket_constrained_best_response_values(spec, maps, result.policy)
    unrestricted = exact_best_response_values(spec, result.policy)

    assert (result.br0_value, result.br1_value) == pytest.approx(expected, abs=1e-12)
    assert result.br0_value <= unrestricted[0] + 1e-12
    assert result.br1_value >= unrestricted[1] - 1e-12


def test_exact_training_result_still_matches_unrestricted_br_oracle():
    spec = fixture_spec()
    maps = exact_bucket_maps(spec)
    state = init_representation_cfr_plus(spec, maps)
    advance_representation_cfr_plus(spec, maps, state, additional_iterations=50)
    result = representation_result_from_state(spec, maps, state)
    assert (result.br0_value, result.br1_value) == pytest.approx(
        exact_best_response_values(spec, result.policy), abs=1e-12
    )
