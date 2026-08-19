from pathlib import Path

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_alternating_dcfr import AlternatingVariant
from deepcash_core.river_lab import RangeCombo
from deepcash_core.river_representation_alternating_dcfr import (
    advance_alternating_representation_solver,
    alternating_representation_result,
    init_alternating_representation_solver,
)
from deepcash_core.river_representation_lab import exact_bucket_maps
from deepcash_core.turn_river_continuation import (
    PRODUCTION_SOLVER_VARIANT,
    solve_turn_river_continuation,
)
from deepcash_core.turn_river_public_state import TurnPublicState, enumerate_river_children


def c(text: str) -> int:
    return card_from_str(text)


def tiny_turn_state() -> TurnPublicState:
    state = TurnPublicState(
        board=(c("Ah"), c("Kd"), c("9c"), c("4s")),
        p0_range=(RangeCombo((c("Qh"), c("Qc")), 1.0),),
        p1_range=(RangeCombo((c("Jh"), c("Jc")), 1.0),),
        pot=100,
        stack=100,
        min_bet=20,
    )
    state.validate()
    return state


def test_exact_turn_continuation_matches_manual_weighted_child_solves():
    state = tiny_turn_state()
    combined = solve_turn_river_continuation(
        state,
        river_iterations=2,
        representation="exact",
    )
    children = enumerate_river_children(state)
    manual_ev = 0.0
    manual_exploitability = 0.0
    for child in children:
        maps = exact_bucket_maps(child.spec)
        solver = init_alternating_representation_solver(
            child.spec,
            maps,
            AlternatingVariant.ALT_DCFR_150_0_2,
        )
        advance_alternating_representation_solver(
            child.spec,
            maps,
            solver,
            additional_iterations=2,
        )
        result = alternating_representation_result(child.spec, maps, solver)
        manual_ev += child.chance_probability * result.policy_ev
        manual_exploitability += child.chance_probability * result.exploitability_per_pot

    assert combined.representation == "exact"
    assert combined.solver_variant == AlternatingVariant.ALT_DCFR_150_0_2.value
    assert combined.policy_ev == pytest.approx(manual_ev, abs=1e-12)
    assert combined.weighted_child_exploitability_per_pot == pytest.approx(
        manual_exploitability, abs=1e-12
    )
    assert sum(child.chance_probability for child in combined.children) == pytest.approx(1.0)


def test_production_turn_continuation_uses_frozen_r4_name_and_is_deterministic():
    state = tiny_turn_state()
    first = solve_turn_river_continuation(state, river_iterations=2, representation="production")
    second = solve_turn_river_continuation(state, river_iterations=2, representation="production")
    assert PRODUCTION_SOLVER_VARIANT == AlternatingVariant.ALT_DCFR_150_0_2
    assert first.representation == "matchup_cluster8"
    assert second == first
    assert first.children
    assert min(child.policy_ev for child in first.children) <= first.policy_ev <= max(
        child.policy_ev for child in first.children
    )


def test_turn_continuation_rejects_nonpositive_iteration_budget():
    with pytest.raises(ValueError, match="river_iterations must be positive"):
        solve_turn_river_continuation(tiny_turn_state(), river_iterations=0)


def test_unknown_nonproduction_representation_fails_closed():
    with pytest.raises(ValueError, match="candidate is not frozen for R4 Generation-2"):
        solve_turn_river_continuation(
            tiny_turn_state(),
            river_iterations=1,
            representation="invented_candidate",
        )
