import random

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import RangeCombo
from deepcash_core.river_reference_dp import exact_best_response_values_dp
from deepcash_core.river_reference_lab import (
    AsymmetricRiverGameSpec,
    actions,
    all_infosets,
    exact_best_response_values,
    solve_asymmetric_river_cfr_plus,
)


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str) -> RangeCombo:
    return RangeCombo((c(a), c(b)))


def spec(p0_sizes=(25, 75), p1_sizes=(33, 100)) -> AsymmetricRiverGameSpec:
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


def random_policy(game: AsymmetricRiverGameSpec, seed: int):
    rng = random.Random(seed)
    policy = {}
    for key in all_infosets(game):
        n = len(actions(game, key[0], key[1]))
        raw = [rng.random() + 0.01 for _ in range(n)]
        total = sum(raw)
        policy[key] = tuple(x / total for x in raw)
    return policy


@pytest.mark.parametrize("seed", range(8))
def test_dynamic_exact_br_matches_independent_pure_plan_enumerator(seed: int):
    game = spec()
    policy = random_policy(game, seed)
    enum = exact_best_response_values(game, policy)
    dp = exact_best_response_values_dp(game, policy)
    assert dp[0] == pytest.approx(enum[0], abs=1e-12)
    assert dp[1] == pytest.approx(enum[1], abs=1e-12)


def test_dynamic_br_matches_enumerator_on_trained_policy_and_asymmetric_sizes():
    game = spec(p0_sizes=(25,), p1_sizes=(33, 100, 150))
    result = solve_asymmetric_river_cfr_plus(game, iterations=120)
    dp = exact_best_response_values_dp(game, result.policy)
    assert dp[0] == pytest.approx(result.br0_value, abs=1e-12)
    assert dp[1] == pytest.approx(result.br1_value, abs=1e-12)


def test_dynamic_br_scales_to_richer_reference_without_pure_plan_enumeration():
    game = spec(
        p0_sizes=(25, 33, 50, 75, 100, 150, 200),
        p1_sizes=(25, 33, 50, 75, 100, 150, 200),
    )
    policy = random_policy(game, 20260816)
    br0, br1 = exact_best_response_values_dp(game, policy)
    assert br0 >= br1
