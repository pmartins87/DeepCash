from deepcash_core.cards import require_distinct
from deepcash_core.river_benchmark_fixtures import (
    HELDOUT2_RIVER_BOARDS,
    HELDOUT_RIVER_BOARDS,
    RIVER_BOARDS,
    parse_cards,
)
from deepcash_core.river_raise_size_heldout_fixtures import (
    RAISE_SIZE_HELDOUT_BOARDS,
    RAISE_SIZE_HELDOUT_CHECKPOINTS,
    RAISE_SIZE_HELDOUT_P0_PHASE,
    RAISE_SIZE_HELDOUT_P1_PHASE,
    RAISE_SIZE_HELDOUT_RANGE_COMBOS,
    RAISE_SIZE_HELDOUT_STACKS,
)


def test_raise_size_heldout_is_separate_and_card_valid():
    existing_names = set(RIVER_BOARDS) | set(HELDOUT_RIVER_BOARDS) | set(HELDOUT2_RIVER_BOARDS)
    assert existing_names.isdisjoint(RAISE_SIZE_HELDOUT_BOARDS)
    assert len(RAISE_SIZE_HELDOUT_BOARDS) == 6
    for text in RAISE_SIZE_HELDOUT_BOARDS.values():
        cards = parse_cards(text)
        assert len(cards) == 5
        assert len(require_distinct(cards)) == 5


def test_raise_size_heldout_precommit_constants_are_frozen():
    assert RAISE_SIZE_HELDOUT_P0_PHASE == 0.22
    assert RAISE_SIZE_HELDOUT_P1_PHASE == 0.68
    assert RAISE_SIZE_HELDOUT_RANGE_COMBOS == 6
    assert RAISE_SIZE_HELDOUT_STACKS == (100, 200, 400)
    assert RAISE_SIZE_HELDOUT_CHECKPOINTS == (300, 1200, 3600)
