from __future__ import annotations

from collections import Counter
from itertools import combinations

from deepcash_core.cards import full_deck
from deepcash_core.evaluator import evaluate_five

EXPECTED = {
    8: 40,       # straight flush
    7: 624,      # quads
    6: 3744,     # full house
    5: 5108,     # flush excluding straight flush
    4: 10200,    # straight excluding straight flush
    3: 54912,    # trips
    2: 123552,   # two pair
    1: 1098240,  # one pair
    0: 1302540,  # high card
}


def main() -> None:
    counts = Counter(evaluate_five(cards)[0] for cards in combinations(full_deck(), 5))
    got = dict(counts)
    print("five-card combinations:", sum(got.values()))
    print("observed:", got)
    print("expected:", EXPECTED)
    if got != EXPECTED:
        raise SystemExit("FAIL: evaluator category distribution mismatch")
    print("PASS: exhaustive 2,598,960-combination distribution audit")


if __name__ == "__main__":
    main()
