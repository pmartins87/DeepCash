from collections import Counter

from deepcash_core.cards import require_distinct
from deepcash_core.river_benchmark_fixtures import (
    HELDOUT2_RIVER_BOARDS,
    HELDOUT_RIVER_BOARDS,
    ONE_RAISE_OPEN_SUBSET_LATTICE,
    RIVER_BOARDS,
    board_registry,
    parse_cards,
    quantile_range,
)


def test_control_and_both_heldout_board_registries_are_disjoint_and_valid():
    assert set(RIVER_BOARDS).isdisjoint(HELDOUT_RIVER_BOARDS)
    assert set(RIVER_BOARDS).isdisjoint(HELDOUT2_RIVER_BOARDS)
    assert set(HELDOUT_RIVER_BOARDS).isdisjoint(HELDOUT2_RIVER_BOARDS)
    assert board_registry("control") == RIVER_BOARDS
    assert board_registry("heldout") == HELDOUT_RIVER_BOARDS
    assert board_registry("heldout_v2") == HELDOUT2_RIVER_BOARDS
    combined = board_registry("all")
    assert len(combined) == (
        len(RIVER_BOARDS) + len(HELDOUT_RIVER_BOARDS) + len(HELDOUT2_RIVER_BOARDS)
    )
    for text in combined.values():
        cards = parse_cards(text)
        assert len(cards) == 5
        assert len(require_distinct(cards)) == 5


def test_heldout_range_phases_are_deterministic_and_change_sample():
    board = parse_cards(HELDOUT_RIVER_BOARDS["K_high_dry_heldout"])
    a = quantile_range(board, 6, 0.13)
    b = quantile_range(board, 6, 0.13)
    c = quantile_range(board, 6, 0.61)
    assert a == b
    assert a != c
    assert len({combo.hole for combo in a}) == 6
    assert len({combo.hole for combo in c}) == 6


def test_heldout_v2_range_phases_are_deterministic_and_distinct_from_v1_samples():
    board = parse_cards(HELDOUT2_RIVER_BOARDS["ace_wheel_connected_v2"])
    p0 = quantile_range(board, 8, 0.31)
    p1 = quantile_range(board, 8, 0.79)
    assert p0 == quantile_range(board, 8, 0.31)
    assert p1 == quantile_range(board, 8, 0.79)
    assert p0 != p1
    assert len({combo.hole for combo in p0}) == 8
    assert len({combo.hole for combo in p1}) == 8


def test_opening_subset_lattice_is_the_complete_nonempty_proper_four_size_lattice():
    assert len(ONE_RAISE_OPEN_SUBSET_LATTICE) == 14
    counts = Counter(len(sizes) for sizes in ONE_RAISE_OPEN_SUBSET_LATTICE.values())
    assert counts == Counter({1: 4, 2: 6, 3: 4})
    assert len(set(ONE_RAISE_OPEN_SUBSET_LATTICE.values())) == 14
    for name, sizes in ONE_RAISE_OPEN_SUBSET_LATTICE.items():
        assert name.startswith(f"L{len(sizes)}_")
        assert tuple(sorted(set(sizes))) == sizes
