from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ActionKind(str, Enum):
    FOLD = "FOLD"
    CHECK = "CHECK"
    CALL = "CALL"
    RAISE_TO = "RAISE_TO"


@dataclass(frozen=True)
class AbstractAction:
    """Solver-facing action intent.

    ``pot_fraction`` is used for postflop bet/raise abstractions. ``raise_to_bb``
    supports preflop blind-denominated abstractions. Exactly one sizing field is
    normally populated for RAISE_TO; concrete legalization happens against the
    exact game state.
    """

    kind: ActionKind
    pot_fraction: float | None = None
    raise_to_bb: float | None = None

    def __post_init__(self) -> None:
        if self.kind != ActionKind.RAISE_TO:
            if self.pot_fraction is not None or self.raise_to_bb is not None:
                raise ValueError("non-raise actions cannot carry a sizing")
            return
        if self.pot_fraction is None and self.raise_to_bb is None:
            raise ValueError("RAISE_TO requires a sizing intent")
        if self.pot_fraction is not None and self.raise_to_bb is not None:
            raise ValueError("RAISE_TO accepts one sizing coordinate at a time")
        value = self.pot_fraction if self.pot_fraction is not None else self.raise_to_bb
        assert value is not None
        if value <= 0:
            raise ValueError("raise sizing must be positive")


def legalize_raise_to(
    desired_raise_to: int,
    *,
    min_raise_to: int,
    max_raise_to: int,
) -> int:
    """Clip a solver sizing to the exact legal interval.

    The engine, not the abstraction, owns the minimum-raise/reopen semantics.
    This helper therefore assumes ``min_raise_to`` and ``max_raise_to`` were
    computed by the exact betting state machine.
    """
    if min_raise_to < 0 or max_raise_to < 0:
        raise ValueError("raise bounds cannot be negative")
    if min_raise_to > max_raise_to:
        raise ValueError("min_raise_to cannot exceed max_raise_to")
    return max(min_raise_to, min(int(desired_raise_to), max_raise_to))
