import random

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import RangeCombo
from deepcash_core.river_raise_reference_dp import exact_best_response_values_dp
from deepcash_core.river_raise_reference_lab import (
    AsymmetricRiverRaiseGameSpec,
    actions,
    all_infosets,
    exact_best_response_values,
    solve_asymmetric_river_raise_cfr_plus,
)


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str) -> RangeCombo:
    return RangeCombo((c(a), c(b)))


def game() -> AsymmetricRiverRaiseGameSpec:
    return AsymmetricRiverRaiseGameSpec(
        board=(c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h")),
        p0_range=(
            combo("Qs", "Qh"),
            combo("Ac", "Qc"),
        ),
        p1_range=(
            combo("Qd", "Jh"),
            combo("Ad", "Td"),
        ),
        pot=100,
        p0_bet_sizes=(25, 75),
        p1_bet_sizes=(50,),
        p1_raise_targets_vs_p0=((25, (100,)), (75, (200,))),
        p0_raise_targets_vs_p1=((50, (150,)),),
    )


def random_policy(spec: AsymmetricRiverRaiseGameSpec, seed: int):
    rng = random.Random(seed)
    policy = {}
    for key in all_infosets(spec):
        n = len(actions(spec, key[0], key[1]))
        raw = [rng.random() + 0.01 for _ in range(n)]
        total = sum(raw)
        policy[key] = tuple(x / total for x in raw)
    return policy


@pytest.mark.parametrize("seed", range(6))
def test_dynamic_one_raise_br_matches_pure_plan_enumerator(seed: int):
    spec = game()
    policy = random_policy(spec, seed)
    enum = exact_best_response_values(spec, policy)
    dp = exact_best_response_values_dp(spec, policy)
    assert dp[0] == pytest.approx(enum[0], abs=1e-12)
    assert dp[1] == pytest.approx(enum[1], abs=1e-12)


def test_dynamic_one_raise_br_matches_trained_policy_oracle():
    spec = game()
    trained = solve_asymmetric_river_raise_cfr_plus(spec, iterations=120)
    dp = exact_best_response_values_dp(spec, trained.policy)
    assert dp[0] == pytest.approx(trained.br0_value, abs=1e-12)
    assert dp[1] == pytest.approx(trained.br1_value, abs=1e-12)


def test_dynamic_one_raise_br_handles_richer_small_reference_without_plan_explosion():
    spec = AsymmetricRiverRaiseGameSpec(
        board=game().board,
        p0_range=game().p0_range,
        p1_range=game().p1_range,
        pot=100,
        p0_bet_sizes=(25, 50, 75),
        p1_bet_sizes=(25, 50, 75),
        p1_raise_targets_vs_p0=(
            (25, (100, 150)),
            (50, (150, 200)),
            (75, (200, 250)),
        ),
        p0_raise_targets_vs_p1=(
            (25, (100, 150)),
            (50, (150, 200)),
            (75, (200, 250)),
        ),
    )
    br0, br1 = exact_best_response_values_dp(spec, random_policy(spec, 20260816))
    assert br0 >= br1
