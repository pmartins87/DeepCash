from deepcash_core.cards import require_distinct
from deepcash_core.river_benchmark_fixtures import (
    HELDOUT_RIVER_BOARDS,
    RIVER_BOARDS,
    board_registry,
    parse_cards,
    quantile_range,
)


def test_control_and_heldout_board_registries_are_disjoint_and_valid():
    assert set(RIVER_BOARDS).isdisjoint(HELDOUT_RIVER_BOARDS)
    assert board_registry("control") == RIVER_BOARDS
    assert board_registry("heldout") == HELDOUT_RIVER_BOARDS
    combined = board_registry("all")
    assert len(combined) == len(RIVER_BOARDS) + len(HELDOUT_RIVER_BOARDS)
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
