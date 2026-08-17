from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from fractions import Fraction
from typing import Generic, TypeVar

from .betting import BettingConfig, ShortAllInReopenPolicy
from .rake import RakePolicy, RakeRounding


T = TypeVar("T")


class EvidenceStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    UNRESOLVED = "UNRESOLVED"


class RakeEligibility(str, Enum):
    POSTFLOP_OR_PREFLOP_THREE_BET_PLUS = "POSTFLOP_OR_PREFLOP_THREE_BET_PLUS"


class RakeApplicationTiming(str, Enum):
    CONTESTED_POTS_AFTER_UNCALLED_RETURN = "CONTESTED_POTS_AFTER_UNCALLED_RETURN"


class OddChipOrderPolicy(str, Enum):
    FIRST_ACTIVE_LEFT_OF_BUTTON = "FIRST_ACTIVE_LEFT_OF_BUTTON"


class SiteRuleContractError(ValueError):
    pass


@dataclass(frozen=True)
class RuleFact(Generic[T]):
    status: EvidenceStatus
    value: T | None
    source: str | None
    note: str

    def __post_init__(self) -> None:
        if self.status == EvidenceStatus.CONFIRMED:
            if self.value is None or not self.source:
                raise ValueError("confirmed rule facts require both value and source")
        elif self.value is not None:
            raise ValueError("unresolved rule facts cannot carry a value")

    def require(self, name: str) -> T:
        if self.status != EvidenceStatus.CONFIRMED or self.value is None:
            raise SiteRuleContractError(f"{name} is unresolved: {self.note}")
        return self.value


@dataclass(frozen=True)
class RakeScheduleRow:
    small_blind_usd: Fraction
    big_blind_usd: Fraction
    rate: Fraction
    cap_2_players_bb: Fraction
    cap_3_players_bb: Fraction
    cap_4_players_bb: Fraction
    cap_5_plus_players_bb: Fraction

    def __post_init__(self) -> None:
        if self.small_blind_usd <= 0 or self.big_blind_usd <= self.small_blind_usd:
            raise ValueError("invalid blind row")
        if not Fraction(0, 1) <= self.rate <= Fraction(1, 1):
            raise ValueError("rake rate must be within [0, 1]")
        if min(
            self.cap_2_players_bb,
            self.cap_3_players_bb,
            self.cap_4_players_bb,
            self.cap_5_plus_players_bb,
        ) < 0:
            raise ValueError("rake caps cannot be negative")

    def cap_bb(self, player_count: int) -> Fraction:
        if not 2 <= player_count <= 6:
            raise ValueError("player_count must be in 2..6")
        if player_count == 2:
            return self.cap_2_players_bb
        if player_count == 3:
            return self.cap_3_players_bb
        if player_count == 4:
            return self.cap_4_players_bb
        return self.cap_5_plus_players_bb


@dataclass(frozen=True)
class SiteRuleContract:
    site_name: str
    variant: str
    checked_on: date
    rake_schedule_source: str
    rake_rows: tuple[RakeScheduleRow, ...]
    rake_eligibility: RuleFact[RakeEligibility]
    rake_rounding: RuleFact[RakeRounding]
    rake_application_timing: RuleFact[RakeApplicationTiming]
    short_all_in_reopen: RuleFact[ShortAllInReopenPolicy]
    odd_chip_order: RuleFact[OddChipOrderPolicy]
    optional_straddle_supported: RuleFact[bool]

    def __post_init__(self) -> None:
        if not self.site_name or not self.variant:
            raise ValueError("site_name and variant are required")
        keys = {(row.small_blind_usd, row.big_blind_usd) for row in self.rake_rows}
        if len(keys) != len(self.rake_rows):
            raise ValueError("duplicate blind rows")

    def unresolved_critical_rules(self) -> tuple[str, ...]:
        checks = (
            ("rake_rounding", self.rake_rounding),
            ("rake_application_timing", self.rake_application_timing),
            ("short_all_in_reopen", self.short_all_in_reopen),
            ("odd_chip_order", self.odd_chip_order),
        )
        return tuple(name for name, fact in checks if fact.status != EvidenceStatus.CONFIRMED)

    def require_critical_rules(self) -> None:
        unresolved = self.unresolved_critical_rules()
        if unresolved:
            raise SiteRuleContractError(
                "site contract is not production-ready; unresolved=" + ",".join(unresolved)
            )

    def betting_config(self) -> BettingConfig:
        policy = self.short_all_in_reopen.require("short_all_in_reopen")
        return BettingConfig(short_all_in_reopen=policy)

    def rake_row(self, *, small_blind_usd: Fraction, big_blind_usd: Fraction) -> RakeScheduleRow:
        key = (Fraction(small_blind_usd), Fraction(big_blind_usd))
        for row in self.rake_rows:
            if (row.small_blind_usd, row.big_blind_usd) == key:
                return row
        raise SiteRuleContractError(f"no confirmed rake row for blinds={key}")

    def rake_policy(
        self,
        *,
        small_blind_usd: Fraction,
        big_blind_usd: Fraction,
        player_count: int,
        big_blind_chips: int,
    ) -> RakePolicy:
        if big_blind_chips <= 0:
            raise ValueError("big_blind_chips must be positive")
        rounding = self.rake_rounding.require("rake_rounding")
        self.rake_eligibility.require("rake_eligibility")
        self.rake_application_timing.require("rake_application_timing")
        row = self.rake_row(
            small_blind_usd=small_blind_usd,
            big_blind_usd=big_blind_usd,
        )
        cap_chips = row.cap_bb(player_count) * big_blind_chips
        if cap_chips.denominator != 1:
            raise SiteRuleContractError(
                "confirmed cap is not integral in the selected engine chip unit"
            )
        return RakePolicy(rate=row.rate, cap=cap_chips.numerator, rounding=rounding)


def _row(sb: str, bb: str, caps_bb: tuple[str, str, str, str]) -> RakeScheduleRow:
    return RakeScheduleRow(
        small_blind_usd=Fraction(sb),
        big_blind_usd=Fraction(bb),
        rate=Fraction(1, 20),
        cap_2_players_bb=Fraction(caps_bb[0]),
        cap_3_players_bb=Fraction(caps_bb[1]),
        cap_4_players_bb=Fraction(caps_bb[2]),
        cap_5_plus_players_bb=Fraction(caps_bb[3]),
    )


_GGPOKER_HOLDEM = "https://ggpoker.com/poker-games/texas-holdem/"
_GGPOKER_CASH_FAQ = "https://help.ggpoker.com/article/Cash-Games---Frequently-Asked-Questions"
_GGPOKER_STRADDLE = "https://ggpoker.com/poker-games/straddle/"


GGPOKER_6MAX_REFERENCE = SiteRuleContract(
    site_name="GGPoker",
    variant="classic 6-max no-limit Texas Hold'em cash",
    checked_on=date(2026, 8, 17),
    rake_schedule_source=_GGPOKER_HOLDEM,
    rake_rows=(
        _row("0.01", "0.02", ("2.5", "5", "7.5", "10")),
        _row("0.02", "0.05", ("2.6", "5", "7.6", "10")),
        _row("0.05", "0.10", ("2.5", "5", "7.5", "10")),
        _row("0.10", "0.25", ("2", "4", "6", "8")),
        _row("0.25", "0.50", ("2", "4", "6", "8")),
        _row("0.50", "1", ("1.25", "2.5", "3.75", "5")),
        _row("1", "2", ("0.75", "1.5", "2.25", "3")),
        _row("2", "5", ("0.4", "0.8", "1.2", "1.6")),
        _row("5", "10", ("0.25", "0.5", "0.75", "1")),
        _row("10", "20", ("0.188", "0.375", "0.563", "0.75")),
    ),
    rake_eligibility=RuleFact(
        status=EvidenceStatus.CONFIRMED,
        value=RakeEligibility.POSTFLOP_OR_PREFLOP_THREE_BET_PLUS,
        source=_GGPOKER_CASH_FAQ,
        note="GGPoker states that pre-flop rake applies only to pots with a 3-bet or higher.",
    ),
    rake_rounding=RuleFact(
        status=EvidenceStatus.UNRESOLVED,
        value=None,
        source=None,
        note="Official public pages do not specify the chip rounding rule or side-pot timing.",
    ),
    rake_application_timing=RuleFact(
        status=EvidenceStatus.UNRESOLVED,
        value=None,
        source=None,
        note=(
            "Official public pages do not fully specify whether caps and rounding "
            "apply per main/side pot after uncalled returns."
        ),
    ),
    short_all_in_reopen=RuleFact(
        status=EvidenceStatus.UNRESOLVED,
        value=None,
        source=None,
        note=(
            "The official Hold'em page defines a minimum full raise and permits a smaller "
            "all-in, but does not define whether one or cumulative short all-ins reopen "
            "raise rights for a player who already acted."
        ),
    ),
    odd_chip_order=RuleFact(
        status=EvidenceStatus.UNRESOLVED,
        value=None,
        source=None,
        note="No authoritative public GGPoker source for tied-pot odd-chip order was found.",
    ),
    optional_straddle_supported=RuleFact(
        status=EvidenceStatus.CONFIRMED,
        value=True,
        source=_GGPOKER_STRADDLE,
        note=(
            "GGPoker documents an optional pre-deal straddle auction; the baseline "
            "classic-cash profile keeps it disabled unless table metadata enables it."
        ),
    ),
)
