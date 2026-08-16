from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SeatPlan:
    occupied: tuple[int, ...]
    button: int
    small_blind: int
    big_blind: int
    preflop_order: tuple[int, ...]
    postflop_order: tuple[int, ...]


def _rotate_after(order: tuple[int, ...], seat: int) -> tuple[int, ...]:
    idx = order.index(seat)
    return order[idx + 1 :] + order[: idx + 1]


def build_seat_plan(occupied_clockwise: Iterable[int], button: int) -> SeatPlan:
    """Resolve blinds and action order for 2..6 handed conventional Hold'em."""
    occupied = tuple(occupied_clockwise)
    if not 2 <= len(occupied) <= 6:
        raise ValueError("cash NLHE seat plan requires 2..6 occupied seats")
    if len(set(occupied)) != len(occupied):
        raise ValueError("occupied seats must be unique")
    if button not in occupied:
        raise ValueError("button must be occupied")

    after_button = _rotate_after(occupied, button)
    if len(occupied) == 2:
        # Heads-up exception: button posts SB and acts first preflop; BB acts
        # first after the flop.
        small_blind = button
        big_blind = after_button[0]
        preflop_order = (button, big_blind)
        postflop_order = (big_blind, button)
    else:
        small_blind = after_button[0]
        big_blind = after_button[1]
        preflop_order = _rotate_after(occupied, big_blind)
        postflop_order = after_button

    return SeatPlan(
        occupied=occupied,
        button=button,
        small_blind=small_blind,
        big_blind=big_blind,
        preflop_order=preflop_order,
        postflop_order=postflop_order,
    )
