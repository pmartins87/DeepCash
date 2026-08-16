from __future__ import annotations

from typing import Iterable

RANK_CHARS = "23456789TJQKA"
SUIT_CHARS = "cdhs"
RANK_TO_VALUE = {r: i + 2 for i, r in enumerate(RANK_CHARS)}
VALUE_TO_RANK = {v: r for r, v in RANK_TO_VALUE.items()}
SUIT_TO_VALUE = {s: i for i, s in enumerate(SUIT_CHARS)}
VALUE_TO_SUIT = {v: s for s, v in SUIT_TO_VALUE.items()}


def card_from_str(text: str) -> int:
    """Encode a conventional two-character card (e.g. ``As``) as 0..51."""
    if not isinstance(text, str) or len(text) != 2:
        raise ValueError(f"invalid card text: {text!r}")
    rank_ch = text[0].upper()
    suit_ch = text[1].lower()
    if rank_ch not in RANK_TO_VALUE or suit_ch not in SUIT_TO_VALUE:
        raise ValueError(f"invalid card text: {text!r}")
    rank_idx = RANK_TO_VALUE[rank_ch] - 2
    return SUIT_TO_VALUE[suit_ch] * 13 + rank_idx


def card_to_str(card: int) -> str:
    validate_card(card)
    return VALUE_TO_RANK[card_rank(card)] + VALUE_TO_SUIT[card_suit(card)]


def validate_card(card: int) -> int:
    if isinstance(card, bool) or not isinstance(card, int) or not 0 <= card < 52:
        raise ValueError(f"invalid encoded card: {card!r}")
    return card


def card_rank(card: int) -> int:
    validate_card(card)
    return (card % 13) + 2


def card_suit(card: int) -> int:
    validate_card(card)
    return card // 13


def full_deck() -> tuple[int, ...]:
    return tuple(range(52))


def require_distinct(cards: Iterable[int]) -> tuple[int, ...]:
    vals = tuple(validate_card(c) for c in cards)
    if len(set(vals)) != len(vals):
        raise ValueError("duplicate card")
    return vals
