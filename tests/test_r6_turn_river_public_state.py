from __future__ import annotations

import pytest

from deepcash_core.river_representation_gen2 import gen2_candidate_bucket_maps
from deepcash_core.turn_river_public_state import (
    build_turn_public_state,
    enumerate_river_children,
    river_child_spec,
)


def fixture_state(stack: int = 200):
    return build_turn_public_state(
        board_text="Ah Kd 9c 7s",
        p0_phase=0.19,
        p1_phase=0.47,
        range_combos=8,
        pot=100,
        stack=stack,
        min_bet=20,
    )


def test_turn_to_river_public_chance_is_complete_and_normalized() -> None:
    state = fixture_state()
    children = enumerate_river_children(state)
    assert children
    assert sum(child.chance_probability for child in children) == pytest.approx(1.0, abs=1e-12)
    assert all(child.chance_mass > 0.0 for child in children)
    assert len({child.river_card for child in children}) == len(children)


def test_river_children_apply_exact_card_removal_to_both_ranges() -> None:
    state = fixture_state()
    for child in enumerate_river_children(state):
        assert len(child.spec.board) == 5
        assert child.spec.board[-1] == child.river_card
        assert all(child.river_card not in combo.hole for combo in child.spec.p0_range)
        assert all(child.river_card not in combo.hole for combo in child.spec.p1_range)
        original_p0 = {combo.hole: combo.weight for combo in state.p0_range}
        original_p1 = {combo.hole: combo.weight for combo in state.p1_range}
        assert all(original_p0[combo.hole] == combo.weight for combo in child.spec.p0_range)
        assert all(original_p1[combo.hole] == combo.weight for combo in child.spec.p1_range)


@pytest.mark.parametrize(
    ("stack", "expected"),
    [
        (100, (25, 50, 100)),
        (200, (25, 50, 100, 200)),
        (400, (25, 50, 100, 200, 400)),
    ],
)
def test_turn_bridge_preserves_generation2_spr_action_geometry(stack: int, expected: tuple[int, ...]) -> None:
    state = fixture_state(stack)
    child = enumerate_river_children(state)[0]
    assert child.spec.bet_sizes == expected


def test_r4_finalists_materialize_on_every_public_river_child() -> None:
    state = fixture_state()
    children = enumerate_river_children(state)
    for child in children:
        for candidate in ("matchup_cluster8", "equity8"):
            maps = gen2_candidate_bucket_maps(child.spec, candidate)
            maps.validate(child.spec)
            assert maps.p0_bucket_count >= 1
            assert maps.p1_bucket_count >= 1


def test_board_card_cannot_be_reused_as_river() -> None:
    state = fixture_state()
    with pytest.raises(ValueError):
        river_child_spec(state, state.board[0])
