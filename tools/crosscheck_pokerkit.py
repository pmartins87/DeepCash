"""Deterministic independent evaluator cross-check against pinned PokerKit.

Expected dependency:
    pip install git+https://github.com/uoftcprg/pokerkit.git@5841c0afe4d6eb71ae5db0f8a6a376ee3e329afb
"""

from __future__ import annotations

import random

from pokerkit.hands import StandardHighHand

from deepcash_core.cards import card_to_str
from deepcash_core.evaluator import evaluate_best, evaluate_five

SEED = 0xD33FC45
FIVE_CARD_PAIR_CASES = 10_000
SEVEN_CARD_SHOWDOWN_CASES = 5_000


def text(cards: tuple[int, ...] | list[int]) -> str:
    return "".join(card_to_str(card) for card in cards)


def compare(a, b) -> int:
    return int(a > b) - int(a < b)


def main() -> None:
    rng = random.Random(SEED)
    deck = list(range(52))

    for case in range(FIVE_CARD_PAIR_CASES):
        sample = rng.sample(deck, 10)
        cards_a = tuple(sample[:5])
        cards_b = tuple(sample[5:])
        ours = compare(evaluate_five(cards_a), evaluate_five(cards_b))
        oracle = compare(StandardHighHand(text(cards_a)), StandardHighHand(text(cards_b)))
        if ours != oracle:
            raise AssertionError(
                f"5-card mismatch case={case} a={text(cards_a)} b={text(cards_b)} "
                f"ours={ours} pokerkit={oracle}"
            )

    for case in range(SEVEN_CARD_SHOWDOWN_CASES):
        sample = rng.sample(deck, 9)
        hero = tuple(sample[:2])
        villain = tuple(sample[2:4])
        board = tuple(sample[4:9])
        ours = compare(
            evaluate_best(hero + board),
            evaluate_best(villain + board),
        )
        oracle = compare(
            StandardHighHand.from_game(text(hero), text(board)),
            StandardHighHand.from_game(text(villain), text(board)),
        )
        if ours != oracle:
            raise AssertionError(
                f"7-card mismatch case={case} hero={text(hero)} villain={text(villain)} "
                f"board={text(board)} ours={ours} pokerkit={oracle}"
            )

    print(
        "PokerKit cross-check PASS: "
        f"{FIVE_CARD_PAIR_CASES} five-card pair comparisons + "
        f"{SEVEN_CARD_SHOWDOWN_CASES} seven-card showdowns; seed={SEED}"
    )


if __name__ == "__main__":
    main()
