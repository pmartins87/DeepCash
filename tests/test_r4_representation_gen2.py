import itertools

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import RangeCombo, RiverGameSpec, materialize_bet_sizes
from deepcash_core.river_representation_gen2 import (
    GEN2_REFERENCE_FRACTIONS,
    R4_GEN2_CANDIDATES,
    gen2_candidate_bucket_maps,
    matchup_cluster_bucket_map,
    matchup_profile_distance_matrix,
)
from deepcash_core.river_representation_gen2_fixtures import (
    R4_GEN2_DEV_BOARDS,
    R4_GEN2_HELDOUT_V2_BOARDS,
    validate_gen2_board_firewall,
)
from deepcash_core.river_representation_lab import candidate_bucket_maps


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str, weight: float = 1.0) -> RangeCombo:
    return RangeCombo((c(a), c(b)), weight)


def fixture_spec(*, reverse_holes: bool = False, reverse_p1_range: bool = False) -> RiverGameSpec:
    board = (c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h"))
    p0_pairs = [
        ("Qs", "Qh", 1.0),
        ("Jc", "Js", 1.5),
        ("Tc", "Ts", 0.8),
        ("Ac", "Qc", 1.2),
        ("Kc", "Qd", 0.7),
        ("8c", "8d", 1.1),
    ]
    p1_pairs = [
        ("Qd", "Jh", 0.9),
        ("Jd", "Th", 1.3),
        ("9d", "8h", 0.8),
        ("Ad", "Td", 1.4),
        ("Ks", "Jd", 0.7),
        ("6c", "6d", 1.0),
    ]
    if reverse_holes:
        p0_pairs = [(b, a, w) for a, b, w in p0_pairs]
        p1_pairs = [(b, a, w) for a, b, w in p1_pairs]
    if reverse_p1_range:
        p1_pairs = list(reversed(p1_pairs))
    p0 = tuple(combo(a, b, w) for a, b, w in p0_pairs)
    p1 = tuple(combo(a, b, w) for a, b, w in p1_pairs)
    return RiverGameSpec(board, p0, p1, pot=100, bet_sizes=(25, 50, 100))


def permute_suits(spec: RiverGameSpec, permutation: tuple[int, int, int, int]) -> RiverGameSpec:
    def pc(card: int) -> int:
        return permutation[card // 13] * 13 + (card % 13)

    def pr(rng: tuple[RangeCombo, ...]) -> tuple[RangeCombo, ...]:
        return tuple(
            RangeCombo((pc(item.hole[0]), pc(item.hole[1])), item.weight)
            for item in rng
        )

    return RiverGameSpec(
        tuple(pc(card) for card in spec.board),
        pr(spec.p0_range),
        pr(spec.p1_range),
        spec.pot,
        spec.bet_sizes,
    )


def test_generation2_candidate_pool_is_frozen_and_separate():
    assert R4_GEN2_CANDIDATES == (
        "equity8",
        "matchup_cluster4",
        "matchup_cluster8",
        "equity4_matchup2",
    )


def test_generation2_reference_has_distinct_spr_geometries():
    assert materialize_bet_sizes(
        pot=100, stack=100, min_bet=20, fractions=GEN2_REFERENCE_FRACTIONS
    ) == (25, 50, 100)
    assert materialize_bet_sizes(
        pot=100, stack=200, min_bet=20, fractions=GEN2_REFERENCE_FRACTIONS
    ) == (25, 50, 100, 200)
    assert materialize_bet_sizes(
        pot=100, stack=400, min_bet=20, fractions=GEN2_REFERENCE_FRACTIONS
    ) == (25, 50, 100, 200, 400)


def test_matchup_distance_is_symmetric_bounded_and_zero_on_diagonal():
    matrix = matchup_profile_distance_matrix(fixture_spec(), 0)
    assert len(matrix) == 6
    for i in range(6):
        assert matrix[i][i] == pytest.approx(0.0)
        for j in range(6):
            assert matrix[i][j] == pytest.approx(matrix[j][i])
            assert 0.0 <= matrix[i][j] <= 1.0


def test_matchup_clustering_is_invariant_to_opponent_range_enumeration():
    normal = fixture_spec(reverse_p1_range=False)
    reversed_opp = fixture_spec(reverse_p1_range=True)
    assert matchup_cluster_bucket_map(normal, 0, 4) == matchup_cluster_bucket_map(
        reversed_opp, 0, 4
    )


@pytest.mark.parametrize("name", R4_GEN2_CANDIDATES)
def test_generation2_bucket_maps_ignore_hole_card_order(name: str):
    normal = fixture_spec(reverse_holes=False)
    reversed_spec = fixture_spec(reverse_holes=True)
    assert gen2_candidate_bucket_maps(normal, name) == gen2_candidate_bucket_maps(
        reversed_spec, name
    )


@pytest.mark.parametrize("name", R4_GEN2_CANDIDATES)
def test_generation2_bucket_maps_ignore_all_24_global_suit_permutations(name: str):
    base = fixture_spec()
    expected = gen2_candidate_bucket_maps(base, name)
    for permutation in itertools.permutations(range(4)):
        assert gen2_candidate_bucket_maps(permute_suits(base, permutation), name) == expected


def test_equity8_anchor_is_bitwise_same_as_generation1_candidate():
    spec = fixture_spec()
    assert gen2_candidate_bucket_maps(spec, "equity8") == candidate_bucket_maps(
        spec, "equity8"
    )


def test_matchup_candidates_never_exceed_nominal_cluster_count():
    spec = fixture_spec()
    c4 = gen2_candidate_bucket_maps(spec, "matchup_cluster4")
    c8 = gen2_candidate_bucket_maps(spec, "matchup_cluster8")
    assert 1 <= c4.p0_bucket_count <= 4
    assert 1 <= c4.p1_bucket_count <= 4
    assert 1 <= c8.p0_bucket_count <= 6
    assert 1 <= c8.p1_bucket_count <= 6


def test_generation2_board_firewall_is_frozen_and_disjoint():
    validate_gen2_board_firewall()
    assert len(R4_GEN2_DEV_BOARDS) == 8
    assert len(R4_GEN2_HELDOUT_V2_BOARDS) == 8
    assert not set(R4_GEN2_DEV_BOARDS).intersection(R4_GEN2_HELDOUT_V2_BOARDS)
    assert not {
        frozenset(text.split()) for text in R4_GEN2_DEV_BOARDS.values()
    }.intersection(
        frozenset(text.split()) for text in R4_GEN2_HELDOUT_V2_BOARDS.values()
    )
