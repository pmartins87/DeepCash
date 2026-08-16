from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Iterable

from .cards import card_rank, card_suit, require_distinct

# Higher tuple compares as stronger poker hand.
# Categories: high card, pair, two pair, trips, straight, flush, full house,
# quads, straight flush.
HandValue = tuple[int, ...]


def _straight_high(ranks: Iterable[int]) -> int | None:
    unique = set(ranks)
    if 14 in unique:
        unique.add(1)  # wheel A2345
    for high in range(14, 4, -1):
        if all(r in unique for r in range(high - 4, high + 1)):
            return high
    return None


def evaluate_five(cards: Iterable[int]) -> HandValue:
    vals = require_distinct(cards)
    if len(vals) != 5:
        raise ValueError("evaluate_five requires exactly five cards")

    ranks = [card_rank(c) for c in vals]
    suits = [card_suit(c) for c in vals]
    counts = Counter(ranks)
    groups = sorted(((n, r) for r, n in counts.items()), reverse=True)
    flush = len(set(suits)) == 1
    straight_high = _straight_high(ranks)

    if flush and straight_high is not None:
        return (8, straight_high)
    if groups[0][0] == 4:
        quad_rank = groups[0][1]
        kicker = max(r for r in ranks if r != quad_rank)
        return (7, quad_rank, kicker)
    if groups[0][0] == 3 and groups[1][0] == 2:
        return (6, groups[0][1], groups[1][1])
    if flush:
        return (5, *sorted(ranks, reverse=True))
    if straight_high is not None:
        return (4, straight_high)
    if groups[0][0] == 3:
        trip_rank = groups[0][1]
        kickers = sorted((r for r in ranks if r != trip_rank), reverse=True)
        return (3, trip_rank, *kickers)

    pairs = sorted((r for r, n in counts.items() if n == 2), reverse=True)
    if len(pairs) >= 2:
        hi, lo = pairs[:2]
        kicker = max(r for r in ranks if r not in (hi, lo))
        return (2, hi, lo, kicker)
    if len(pairs) == 1:
        pair = pairs[0]
        kickers = sorted((r for r in ranks if r != pair), reverse=True)
        return (1, pair, *kickers)
    return (0, *sorted(ranks, reverse=True))


def evaluate_best(cards: Iterable[int]) -> HandValue:
    vals = require_distinct(cards)
    if not 5 <= len(vals) <= 7:
        raise ValueError("evaluate_best requires five, six, or seven cards")
    return max(evaluate_five(combo) for combo in combinations(vals, 5))
