from __future__ import annotations

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_alternating_dcfr import (
    AlternatingVariant,
    advance_alternating_solver,
    alternating_solver_result,
    init_alternating_solver,
)
from deepcash_core.river_lab import RangeCombo, RiverGameSpec
from deepcash_core.river_representation_alternating_dcfr import (
    advance_alternating_representation_solver,
    alternating_representation_result,
    alternating_representation_state_from_dict,
    alternating_representation_state_to_dict,
    init_alternating_representation_solver,
)
from deepcash_core.river_representation_gen2 import gen2_candidate_bucket_maps
from deepcash_core.river_representation_lab import exact_bucket_maps


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str, weight: float = 1.0) -> RangeCombo:
    return RangeCombo((c(a), c(b)), weight)


def fixture_spec() -> RiverGameSpec:
    board = (c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h"))
    p0 = (
        combo("Qs", "Qh", 1.0),
        combo("Jc", "Js", 1.5),
        combo("Tc", "Ts", 0.8),
        combo("Ac", "Qc", 1.2),
    )
    p1 = (
        combo("Qd", "Jh", 0.9),
        combo("Jd", "Th", 1.3),
        combo("9d", "8h", 0.8),
        combo("Ad", "Td", 1.4),
    )
    return RiverGameSpec(board, p0, p1, pot=100, bet_sizes=(25, 50, 100))


@pytest.mark.parametrize(
    "variant",
    [AlternatingVariant.ALT_CFR_PLUS_LINEAR, AlternatingVariant.ALT_DCFR_150_0_2],
)
def test_exact_bucket_path_matches_exact_alternating_solver(variant: AlternatingVariant) -> None:
    spec = fixture_spec()
    exact = init_alternating_solver(spec, variant)
    abstract_maps = exact_bucket_maps(spec)
    abstract = init_alternating_representation_solver(spec, abstract_maps, variant)

    advance_alternating_solver(spec, exact, additional_iterations=8)
    advance_alternating_representation_solver(spec, abstract_maps, abstract, additional_iterations=8)

    assert abstract.iterations == exact.iterations
    assert abstract.regrets == exact.regrets
    assert abstract.strategy_sum == exact.strategy_sum

    exact_result = alternating_solver_result(spec, exact)
    abstract_result = alternating_representation_result(spec, abstract_maps, abstract)
    assert abstract_result.policy_ev == pytest.approx(exact_result.policy_ev, abs=1e-12)
    assert abstract_result.br0_value == pytest.approx(exact_result.br0_value, abs=1e-12)
    assert abstract_result.br1_value == pytest.approx(exact_result.br1_value, abs=1e-12)
    assert abstract_result.exploitability_per_pot == pytest.approx(
        exact_result.exploitability_per_pot, abs=1e-12
    )


def test_abstract_alternating_checkpoint_resume_is_future_path_equivalent() -> None:
    spec = fixture_spec()
    maps = gen2_candidate_bucket_maps(spec, "matchup_cluster8")
    variant = AlternatingVariant.ALT_DCFR_150_0_2

    direct = init_alternating_representation_solver(spec, maps, variant)
    advance_alternating_representation_solver(spec, maps, direct, additional_iterations=9)

    split = init_alternating_representation_solver(spec, maps, variant)
    advance_alternating_representation_solver(spec, maps, split, additional_iterations=4)
    payload = alternating_representation_state_to_dict(split)
    resumed = alternating_representation_state_from_dict(
        spec, maps, payload, expected_variant=variant
    )
    advance_alternating_representation_solver(spec, maps, resumed, additional_iterations=5)

    assert alternating_representation_state_to_dict(resumed) == alternating_representation_state_to_dict(direct)


def test_matchup_cluster8_runs_under_leading_discounted_control() -> None:
    spec = fixture_spec()
    maps = gen2_candidate_bucket_maps(spec, "matchup_cluster8")
    state = init_alternating_representation_solver(
        spec, maps, AlternatingVariant.ALT_DCFR_150_0_2
    )
    advance_alternating_representation_solver(spec, maps, state, additional_iterations=20)
    result = alternating_representation_result(spec, maps, state)

    assert result.iterations == 20
    assert result.infosets > 0
    assert result.action_slots > 0
    assert result.exploitability_per_pot >= 0.0
    assert result.br0_value >= result.br1_value - 1e-12
