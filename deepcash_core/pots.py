from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class UncalledReturn:
    seat: int
    amount: int


@dataclass(frozen=True)
class SidePot:
    amount: int
    contributors: tuple[int, ...]
    eligible: tuple[int, ...]


def normalize_uncalled(contributions: Mapping[int, int]) -> tuple[dict[int, int], UncalledReturn | None]:
    """Return the unique unmatched top contribution before pot construction.

    At most one unmatched tranche can exist after betting is terminal. Returning
    it before rake/side-pot construction prevents money that was never called
    from being treated as contested pot.
    """
    if not contributions:
        return {}, None
    out = {int(seat): int(amount) for seat, amount in contributions.items()}
    if any(amount < 0 for amount in out.values()):
        raise ValueError("contributions cannot be negative")

    ranked = sorted(out.items(), key=lambda x: x[1], reverse=True)
    top_seat, top = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0
    top_count = sum(1 for amount in out.values() if amount == top)
    if top_count != 1 or top <= second:
        return out, None

    amount = top - second
    out[top_seat] -= amount
    return out, UncalledReturn(top_seat, amount)


def build_side_pots(contributions: Mapping[int, int], eligible_seats: Iterable[int]) -> tuple[SidePot, ...]:
    contrib = {int(seat): int(amount) for seat, amount in contributions.items()}
    if any(amount < 0 for amount in contrib.values()):
        raise ValueError("contributions cannot be negative")
    eligible_set = set(int(s) for s in eligible_seats)
    if not eligible_set.issubset(contrib):
        raise ValueError("eligible seat missing from contributions")

    levels = sorted({amount for amount in contrib.values() if amount > 0})
    pots: list[SidePot] = []
    previous = 0
    for level in levels:
        contributors = tuple(sorted(seat for seat, amount in contrib.items() if amount >= level))
        tranche = (level - previous) * len(contributors)
        if tranche <= 0:
            previous = level
            continue
        eligible = tuple(seat for seat in contributors if seat in eligible_set)
        if not eligible:
            raise ValueError("side pot has no eligible winner")
        pots.append(SidePot(tranche, contributors, eligible))
        previous = level
    return tuple(pots)


def award_side_pots(
    pots: Sequence[SidePot],
    hand_values: Mapping[int, tuple[int, ...]],
    *,
    odd_chip_order: Sequence[int],
) -> dict[int, int]:
    payouts: dict[int, int] = {}
    order = tuple(int(seat) for seat in odd_chip_order)
    if len(set(order)) != len(order):
        raise ValueError("odd_chip_order cannot contain duplicate seats")
    order_index = {seat: i for i, seat in enumerate(order)}

    for pot in pots:
        missing = [seat for seat in pot.eligible if seat not in hand_values]
        if missing:
            raise ValueError(f"missing hand value for eligible seats: {missing}")
        best = max(hand_values[seat] for seat in pot.eligible)
        winners = [seat for seat in pot.eligible if hand_values[seat] == best]
        missing_order = [seat for seat in winners if seat not in order_index]
        if missing_order:
            raise ValueError(
                "odd_chip_order must explicitly cover every tied winner; "
                f"missing={missing_order}"
            )
        winners.sort(key=order_index.__getitem__)
        share, remainder = divmod(pot.amount, len(winners))
        for seat in winners:
            payouts[seat] = payouts.get(seat, 0) + share
        for seat in winners[:remainder]:
            payouts[seat] += 1
    return payouts
