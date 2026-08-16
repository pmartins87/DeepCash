from itertools import permutations

import pytest

from deepcash_core.canonical import canonical_hole, canonical_public_cards, canonical_suits


def test_hole_order_is_invariant() -> None:
    assert canonical_hole(("As", "Kd")) == canonical_hole(("Kd", "As"))


def test_flop_order_is_invariant() -> None:
    flop = ("Ah", "7c", "2s")
    expected = canonical_public_cards(flop)
    for perm in permutations(flop):
        assert canonical_public_cards(perm) == expected


def test_global_suit_renaming_is_invariant() -> None:
    base = ("As", "Ks", "Qh", "7d", "2c")
    renamed = ("Ah", "Kh", "Qc", "7s", "2d")
    assert canonical_suits(base) == canonical_suits(renamed)


def test_duplicate_cards_rejected() -> None:
    with pytest.raises(ValueError):
        canonical_hole(("As", "As"))
