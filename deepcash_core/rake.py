from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction


class RakeRounding(str, Enum):
    FLOOR = "FLOOR"
    CEIL = "CEIL"
    NEAREST_HALF_UP = "NEAREST_HALF_UP"


@dataclass(frozen=True)
class RakePolicy:
    """Economy layer kept separate from poker legality.

    ``rate`` is exact and ``cap`` uses the same integer chip unit as the pot.
    Rounding is deliberately optional: an unknown site/client rule must remain
    unknown instead of being silently approximated.
    """

    rate: Fraction
    cap: int | None = None
    rounding: RakeRounding | None = None

    def __post_init__(self) -> None:
        if self.rate < 0:
            raise ValueError("rake rate cannot be negative")
        if self.cap is not None and self.cap < 0:
            raise ValueError("rake cap cannot be negative")

    def exact(self, contested_pot: int, *, eligible: bool = True) -> Fraction:
        if contested_pot < 0:
            raise ValueError("pot cannot be negative")
        if not eligible:
            return Fraction(0, 1)
        value = Fraction(contested_pot, 1) * self.rate
        if self.cap is not None:
            value = min(value, Fraction(self.cap, 1))
        return value

    def charged(self, contested_pot: int, *, eligible: bool = True) -> int:
        exact = self.exact(contested_pot, eligible=eligible)
        if exact.denominator == 1:
            return exact.numerator
        if self.rounding is None:
            raise ValueError("rake rounding is unspecified")
        if self.rounding == RakeRounding.FLOOR:
            return exact.numerator // exact.denominator
        if self.rounding == RakeRounding.CEIL:
            return -(-exact.numerator // exact.denominator)
        if self.rounding == RakeRounding.NEAREST_HALF_UP:
            q, r = divmod(exact.numerator, exact.denominator)
            return q + int(2 * r >= exact.denominator)
        raise AssertionError(self.rounding)
