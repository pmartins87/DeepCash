from __future__ import annotations

from fractions import Fraction
from itertools import combinations

from .cards import card_from_str, full_deck
from .evaluator import evaluate_best
from .river_lab import RangeCombo

ONE_BET_CANDIDATES = {
    "S1_50": (Fraction(1, 2),),
    "S2_33_100": (Fraction(1, 3), Fraction(1, 1)),
    "S3_25_75_150": (Fraction(1, 4), Fraction(3, 4), Fraction(3, 2)),
    "S4_25_50_100_200": (
        Fraction(1, 4), Fraction(1, 2), Fraction(1, 1), Fraction(2, 1)
    ),
}

ONE_BET_REFERENCE_FRACTIONS = (
    Fraction(1, 4),
    Fraction(1, 3),
    Fraction(1, 2),
    Fraction(3, 4),
    Fraction(1, 1),
    Fraction(3, 2),
    Fraction(2, 1),
)

# Opening-size controls for the one-raise common-reference river battery.
# Candidates are literal subsets of the rich reference so restriction loss can
# be bounded without remapping actions between different trees.
ONE_RAISE_OPEN_CANDIDATES = {
    "O1_50": (Fraction(1, 2),),
    "O2_25_75": (Fraction(1, 4), Fraction(3, 4)),
    "O3_25_50_100": (Fraction(1, 4), Fraction(1, 2), Fraction(1, 1)),
}

ONE_RAISE_OPEN_REFERENCE_FRACTIONS = (
    Fraction(1, 4),
    Fraction(1, 2),
    Fraction(3, 4),
    Fraction(1, 1),
)

RIVER_BOARDS = {
    "A_high_dry": "Ah Kd 9c 7s 2h",
    "paired": "Qs Qd 9h 7c 2s",
    "four_straight": "9h 8d 7c 6s 2h",
    "four_flush": "Ah Jh 8h 4h 2c",
}


def parse_cards(text: str) -> tuple[int, ...]:
    return tuple(card_from_str(x) for x in text.split())


def quantile_range(
    board: tuple[int, ...], count: int, phase: float
) -> tuple[RangeCombo, ...]:
    if count <= 0:
        raise ValueError("range combo count must be positive")
    remaining = [c for c in full_deck() if c not in set(board)]
    combos = list(combinations(remaining, 2))
    combos.sort(key=lambda h: (evaluate_best((*h, *board)), h))
    selected = []
    used = set()
    for k in range(count):
        q = min(0.999999, max(0.000001, (k + 0.5 + phase) / count))
        idx = round(q * (len(combos) - 1))
        while combos[idx] in used:
            idx = min(len(combos) - 1, idx + 1)
        used.add(combos[idx])
        selected.append(RangeCombo(tuple(combos[idx])))
    return tuple(selected)


def parse_names(text: str, available: dict[str, object]) -> tuple[str, ...]:
    if text == "all":
        return tuple(available)
    names = tuple(x.strip() for x in text.split(",") if x.strip())
    unknown = set(names) - set(available)
    if unknown:
        raise ValueError(f"unknown names: {sorted(unknown)}")
    return names


def parse_checkpoints(text: str) -> tuple[int, ...]:
    values = tuple(sorted({int(x.strip()) for x in text.split(",") if x.strip()}))
    if not values or values[0] <= 0:
        raise ValueError("checkpoints must be positive integers")
    return values


def restriction_loss_bounds(reference, p0_restricted, p1_restricted, pot: int) -> dict:
    p0_lower = reference.br1_value - p0_restricted.br0_value
    p0_upper = reference.br0_value - p0_restricted.br1_value
    p1_lower = p1_restricted.br1_value - reference.br0_value
    p1_upper = p1_restricted.br0_value - reference.br1_value
    worst_upper = max(0.0, p0_upper, p1_upper)
    return {
        "p0_loss_lower": p0_lower,
        "p0_loss_upper": p0_upper,
        "p1_loss_lower": p1_lower,
        "p1_loss_upper": p1_upper,
        "worst_loss_upper": worst_upper,
        "worst_loss_upper_per_pot": worst_upper / float(pot),
    }
