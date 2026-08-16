import itertools
import json

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_benchmark_fixtures import restriction_loss_bounds
from deepcash_core.river_lab import RangeCombo, RiverGameSpec, solve_river_cfr_plus
from deepcash_core.river_representation_lab import (
    RIVER_REPRESENTATION_CANDIDATES,
    candidate_bucket_maps,
    exact_bucket_maps,
    one_sided_bucket_maps,
)
from deepcash_core.river_representation_solver import solve_river_representation_cfr_plus
from deepcash_core.river_representation_training import (
    advance_representation_cfr_plus,
    init_representation_cfr_plus,
    representation_result_from_state,
    state_from_dict,
    state_to_dict,
)


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str, weight: float = 1.0) -> RangeCombo:
    return RangeCombo((c(a), c(b)), weight)


def fixture_spec(*, reverse_holes: bool = False) -> RiverGameSpec:
    board = (c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h"))
    p0_pairs = [
        ("Qs", "Qh"),
        ("Jc", "Js"),
        ("Tc", "Ts"),
        ("Ac", "Qc"),
        ("Kc", "Qd"),
        ("8c", "8d"),
    ]
    p1_pairs = [
        ("Qd", "Jh"),
        ("Jd", "Th"),
        ("9d", "8h"),
        ("Ad", "Td"),
        ("Ks", "Jd"),
        ("6c", "6d"),
    ]
    if reverse_holes:
        p0_pairs = [(b, a) for a, b in p0_pairs]
        p1_pairs = [(b, a) for a, b in p1_pairs]
    p0 = tuple(combo(a, b) for a, b in p0_pairs)
    p1 = tuple(combo(a, b) for a, b in p1_pairs)
    return RiverGameSpec(board, p0, p1, pot=100, bet_sizes=(40, 100))


def permute_suits(spec: RiverGameSpec, permutation: tuple[int, int, int, int]) -> RiverGameSpec:
    def pc(card: int) -> int:
        return permutation[card // 13] * 13 + (card % 13)

    def pr(rng: tuple[RangeCombo, ...]) -> tuple[RangeCombo, ...]:
        return tuple(RangeCombo((pc(item.hole[0]), pc(item.hole[1])), item.weight) for item in rng)

    return RiverGameSpec(
        tuple(pc(card) for card in spec.board),
        pr(spec.p0_range),
        pr(spec.p1_range),
        spec.pot,
        spec.bet_sizes,
    )


def test_exact_infoset_map_reproduces_original_solver_bitwise():
    spec = fixture_spec()
    baseline = solve_river_cfr_plus(spec, iterations=120)
    represented = solve_river_representation_cfr_plus(
        spec, exact_bucket_maps(spec), iterations=120
    )
    assert represented == baseline


def test_category_control_really_compresses_exact_combo_infosets():
    spec = fixture_spec()
    exact = exact_bucket_maps(spec)
    category = candidate_bucket_maps(spec, "category")
    assert category.p0_bucket_count == 1  # all six P0 fixtures make one pair
    assert category.p0_bucket_count < exact.p0_bucket_count
    assert category.p1_bucket_count < exact.p1_bucket_count

    result = solve_river_representation_cfr_plus(spec, category, iterations=80)
    exact_result = solve_river_representation_cfr_plus(spec, exact, iterations=80)
    assert result.infosets < exact_result.infosets
    assert result.action_slots < exact_result.action_slots
    assert result.br0_value + 1e-9 >= result.policy_ev
    assert result.policy_ev + 1e-9 >= result.br1_value


@pytest.mark.parametrize("name", RIVER_REPRESENTATION_CANDIDATES)
def test_feature_bucket_maps_ignore_hole_card_order(name: str):
    normal = fixture_spec(reverse_holes=False)
    reversed_spec = fixture_spec(reverse_holes=True)
    assert candidate_bucket_maps(normal, name) == candidate_bucket_maps(reversed_spec, name)


@pytest.mark.parametrize("name", RIVER_REPRESENTATION_CANDIDATES)
def test_feature_bucket_maps_ignore_all_24_global_suit_permutations(name: str):
    base = fixture_spec()
    expected = candidate_bucket_maps(base, name)
    for permutation in itertools.permutations(range(4)):
        assert candidate_bucket_maps(permute_suits(base, permutation), name) == expected


def test_one_sided_restriction_keeps_other_player_exact():
    spec = fixture_spec()
    candidate = candidate_bucket_maps(spec, "equity4")
    exact = exact_bucket_maps(spec)

    p0_only = one_sided_bucket_maps(spec, candidate, 0)
    p1_only = one_sided_bucket_maps(spec, candidate, 1)
    assert p0_only.p0 == candidate.p0
    assert p0_only.p1 == exact.p1
    assert p1_only.p0 == exact.p0
    assert p1_only.p1 == candidate.p1


def test_common_reference_representation_loss_is_measured_in_exact_game():
    spec = fixture_spec()
    candidate = candidate_bucket_maps(spec, "equity4")
    reference = solve_river_representation_cfr_plus(
        spec, exact_bucket_maps(spec), iterations=180
    )
    p0_restricted = solve_river_representation_cfr_plus(
        spec, one_sided_bucket_maps(spec, candidate, 0), iterations=180
    )
    p1_restricted = solve_river_representation_cfr_plus(
        spec, one_sided_bucket_maps(spec, candidate, 1), iterations=180
    )
    bounds = restriction_loss_bounds(reference, p0_restricted, p1_restricted, spec.pot)
    assert bounds["worst_loss_upper"] >= 0.0
    assert bounds["worst_loss_upper_per_pot"] == pytest.approx(
        bounds["worst_loss_upper"] / spec.pot
    )


def test_representation_cfr_staged_training_matches_monolithic_exactly():
    spec = fixture_spec()
    maps = candidate_bucket_maps(spec, "equity4_blocker2")

    staged = init_representation_cfr_plus(spec, maps)
    advance_representation_cfr_plus(spec, maps, staged, additional_iterations=35)
    advance_representation_cfr_plus(spec, maps, staged, additional_iterations=65)

    monolithic = init_representation_cfr_plus(spec, maps)
    advance_representation_cfr_plus(spec, maps, monolithic, additional_iterations=100)

    assert staged == monolithic
    assert representation_result_from_state(spec, maps, staged) == (
        representation_result_from_state(spec, maps, monolithic)
    )
    assert representation_result_from_state(spec, maps, staged) == (
        solve_river_representation_cfr_plus(spec, maps, iterations=100)
    )


def test_representation_checkpoint_json_roundtrip_preserves_future_path():
    spec = fixture_spec()
    maps = candidate_bucket_maps(spec, "category_equity4")
    original = init_representation_cfr_plus(spec, maps)
    advance_representation_cfr_plus(spec, maps, original, additional_iterations=40)

    payload = json.loads(json.dumps(state_to_dict(original)))
    restored = state_from_dict(spec, maps, payload)
    assert restored == original

    advance_representation_cfr_plus(spec, maps, original, additional_iterations=60)
    advance_representation_cfr_plus(spec, maps, restored, additional_iterations=60)
    assert restored == original
    assert representation_result_from_state(spec, maps, restored) == (
        representation_result_from_state(spec, maps, original)
    )
