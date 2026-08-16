import json

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import RangeCombo, RiverGameSpec, solve_river_cfr_plus
from deepcash_core.river_solver_variants import (
    SolverVariant,
    advance_river_solver,
    init_river_solver,
    river_solver_result,
    river_solver_state_from_dict,
    river_solver_state_to_dict,
    solve_river_variant,
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


def test_cfr_plus_linear_matches_legacy_solver_exactly():
    spec = fixture_spec()
    assert solve_river_variant(
        spec, variant=SolverVariant.CFR_PLUS_LINEAR, iterations=120
    ) == solve_river_cfr_plus(spec, iterations=120)


@pytest.mark.parametrize("variant", list(SolverVariant))
def test_staged_training_matches_monolithic_for_every_variant(variant):
    spec = fixture_spec()
    staged = init_river_solver(spec, variant)
    advance_river_solver(spec, staged, additional_iterations=35)
    advance_river_solver(spec, staged, additional_iterations=65)

    monolithic = init_river_solver(spec, variant)
    advance_river_solver(spec, monolithic, additional_iterations=100)

    assert staged == monolithic
    assert river_solver_result(spec, staged) == river_solver_result(spec, monolithic)
    assert river_solver_result(spec, staged) == solve_river_variant(
        spec, variant=variant, iterations=100
    )


@pytest.mark.parametrize("variant", list(SolverVariant))
def test_json_roundtrip_preserves_exact_future_path(variant):
    spec = fixture_spec()
    state = init_river_solver(spec, variant)
    advance_river_solver(spec, state, additional_iterations=40)

    payload = json.loads(json.dumps(river_solver_state_to_dict(state)))
    restored = river_solver_state_from_dict(spec, payload, expected_variant=variant)
    assert restored == state

    advance_river_solver(spec, state, additional_iterations=60)
    advance_river_solver(spec, restored, additional_iterations=60)
    assert restored == state
    assert river_solver_result(spec, restored) == river_solver_result(spec, state)


def test_checkpoint_rejects_wrong_variant():
    spec = fixture_spec()
    state = init_river_solver(spec, SolverVariant.CFR_LINEAR)
    payload = river_solver_state_to_dict(state)
    with pytest.raises(ValueError, match="variant"):
        river_solver_state_from_dict(
            spec, payload, expected_variant=SolverVariant.CFR_PLUS_LINEAR
        )


def test_checkpoint_rejects_nonfinite_state():
    spec = fixture_spec()
    state = init_river_solver(spec, SolverVariant.CFR_UNIFORM)
    payload = river_solver_state_to_dict(state)
    key = next(iter(payload["regrets"]))
    payload["regrets"][key][0] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        river_solver_state_from_dict(spec, payload)
