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

# Exhaustive non-empty proper subset lattice of the same four-size opening
# reference. The first candidate set intentionally sampled only one singleton,
# one pair and one triple. Held-out evidence showed that the triple remained far
# better than those smaller controls but still had measurable residual loss on
# some boards. Before adding any new arbitrary size, enumerate every existing
# reference subset so we know whether the earlier candidate choice itself left
# easy EV on the table.
ONE_RAISE_OPEN_SUBSET_LATTICE = {
    "L1_25": (Fraction(1, 4),),
    "L1_50": (Fraction(1, 2),),
    "L1_75": (Fraction(3, 4),),
    "L1_100": (Fraction(1, 1),),
    "L2_25_50": (Fraction(1, 4), Fraction(1, 2)),
    "L2_25_75": (Fraction(1, 4), Fraction(3, 4)),
    "L2_25_100": (Fraction(1, 4), Fraction(1, 1)),
    "L2_50_75": (Fraction(1, 2), Fraction(3, 4)),
    "L2_50_100": (Fraction(1, 2), Fraction(1, 1)),
    "L2_75_100": (Fraction(3, 4), Fraction(1, 1)),
    "L3_25_50_75": (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)),
    "L3_25_50_100": (Fraction(1, 4), Fraction(1, 2), Fraction(1, 1)),
    "L3_25_75_100": (Fraction(1, 4), Fraction(3, 4), Fraction(1, 1)),
    "L3_50_75_100": (Fraction(1, 2), Fraction(3, 4), Fraction(1, 1)),
}

# Raise-size controls. Fractions are measured against the pot *after calling*
# the faced opening bet. A 1.0 fraction therefore means a pot-sized raise over
# the call. Candidates are strict subsets of the rich 0.5/1.0/1.5 reference.
ONE_RAISE_SIZE_CANDIDATES = {
    "Q1_100": (Fraction(1, 1),),
    "Q2_50_100": (Fraction(1, 2), Fraction(1, 1)),
    "Q2_100_150": (Fraction(1, 1), Fraction(3, 2)),
    "Q3_50_100_150": (Fraction(1, 2), Fraction(1, 1), Fraction(3, 2)),
}

ONE_RAISE_SIZE_REFERENCE_FRACTIONS = (
    Fraction(1, 2),
    Fraction(1, 1),
    Fraction(3, 2),
)

# Development/control boards. These are intentionally small and stable because
# earlier convergence curves and regression artifacts reference them directly.
RIVER_BOARDS = {
    "A_high_dry": "Ah Kd 9c 7s 2h",
    "paired": "Qs Qd 9h 7c 2s",
    "four_straight": "9h 8d 7c 6s 2h",
    "four_flush": "Ah Jh 8h 4h 2c",
}

# Precommitted held-out board families. They are kept separate from RIVER_BOARDS
# so adding them never silently changes the historical `--boards all` control
# battery. Held-out workflows must opt into this set explicitly.
HELDOUT_RIVER_BOARDS = {
    "K_high_dry_heldout": "Kc 8d 5s 3h 2c",
    "double_paired_heldout": "Js Jd 6c 6h 2s",
    "three_flush_heldout": "Kh Qh 8h 5c 2d",
    "broadway_connected_heldout": "Ks Qd Jh 5c 2s",
    "low_connected_heldout": "7h 6d 5c 3s 2h",
    "trips_board_heldout": "9s 9h 9d 4c 2h",
}


def board_registry(name: str) -> dict[str, str]:
    if name == "control":
        return dict(RIVER_BOARDS)
    if name == "heldout":
        return dict(HELDOUT_RIVER_BOARDS)
    if name == "all":
        overlap = set(RIVER_BOARDS).intersection(HELDOUT_RIVER_BOARDS)
        if overlap:
            raise RuntimeError(f"control/heldout board names overlap: {sorted(overlap)}")
        return {**RIVER_BOARDS, **HELDOUT_RIVER_BOARDS}
    raise ValueError("board set must be control, heldout, or all")


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
