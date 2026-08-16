from __future__ import annotations

from itertools import permutations
from typing import Iterable, Sequence

RANKS = "23456789TJQKA"
SUITS = "cdhs"
RANK_VALUE = {r: i for i, r in enumerate(RANKS)}
SUIT_VALUE = {s: i for i, s in enumerate(SUITS)}


def _validate_card(card: str) -> str:
    if len(card) != 2 or card[0] not in RANK_VALUE or card[1] not in SUIT_VALUE:
        raise ValueError(f"invalid card: {card!r}")
    return card


def _card_key(card: str) -> tuple[int, int]:
    _validate_card(card)
    return (RANK_VALUE[card[0]], SUIT_VALUE[card[1]])


def canonical_hole(cards: Sequence[str]) -> tuple[str, str]:
    """Canonicalize the two private cards; physical order has no semantics."""
    if len(cards) != 2:
        raise ValueError("hole cards must contain exactly two cards")
    a, b = (_validate_card(str(c)) for c in cards)
    if a == b:
        raise ValueError("duplicate card")
    return tuple(sorted((a, b), key=_card_key, reverse=True))  # type: ignore[return-value]


def canonical_public_cards(cards: Sequence[str]) -> tuple[str, ...]:
    """Canonicalize a simultaneous public-card set such as the flop.

    This intentionally does not assert that turn and river order is irrelevant;
    callers should only use it for cards that were revealed simultaneously.
    """
    vals = tuple(_validate_card(str(c)) for c in cards)
    if len(set(vals)) != len(vals):
        raise ValueError("duplicate public card")
    return tuple(sorted(vals, key=_card_key, reverse=True))


def _rename_suits(cards: Iterable[str], mapping: dict[str, str]) -> tuple[str, ...]:
    return tuple(c[0] + mapping[c[1]] for c in cards)


def canonical_suits(cards: Sequence[str]) -> tuple[str, ...]:
    """Return the lexicographically minimal global-suit renaming.

    The complete card sequence is transformed under all 24 suit permutations.
    Sequence position is preserved here because action/street semantics may make
    positions meaningful. Order invariance is handled by the appropriate caller
    (e.g. ``canonical_hole`` or ``canonical_public_cards``).
    """
    vals = tuple(_validate_card(str(c)) for c in cards)
    if len(set(vals)) != len(vals):
        raise ValueError("duplicate card")

    candidates: list[tuple[str, ...]] = []
    for perm in permutations(SUITS):
        mapping = dict(zip(SUITS, perm))
        candidates.append(_rename_suits(vals, mapping))
    return min(candidates)
