from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class EvidenceScenario(str, Enum):
    CUMULATIVE_SHORT_ALL_IN_REOPEN = "CUMULATIVE_SHORT_ALL_IN_REOPEN"
    ODD_CHIP_SPLIT = "ODD_CHIP_SPLIT"
    RAKE_SETTLEMENT = "RAKE_SETTLEMENT"


class EvidenceSourceKind(str, Enum):
    OFFICIAL_RULE = "OFFICIAL_RULE"
    OFFICIAL_SUPPORT_REPLY = "OFFICIAL_SUPPORT_REPLY"
    OBSERVED_HAND_HISTORY = "OBSERVED_HAND_HISTORY"


class ObservedStreet(str, Enum):
    PREFLOP = "PREFLOP"
    FLOP = "FLOP"
    TURN = "TURN"
    RIVER = "RIVER"


class SiteRuleEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class CumulativeShortAllInFixture:
    prior_actor_faced_bet: int
    last_full_raise_increment: int
    short_all_in_targets: tuple[int, ...]
    observed_raise_reopened: bool

    def __post_init__(self) -> None:
        if self.prior_actor_faced_bet < 0 or self.last_full_raise_increment <= 0:
            raise SiteRuleEvidenceError("invalid starting betting geometry")
        if len(self.short_all_in_targets) < 2:
            raise SiteRuleEvidenceError(
                "cumulative reopen evidence requires at least two short all-ins"
            )
        previous = self.prior_actor_faced_bet
        for target in self.short_all_in_targets:
            if target <= previous:
                raise SiteRuleEvidenceError("short all-in targets must strictly increase")
            if target - previous >= self.last_full_raise_increment:
                raise SiteRuleEvidenceError(
                    "every intervening increase must be smaller than a full raise"
                )
            previous = target
        if previous - self.prior_actor_faced_bet < self.last_full_raise_increment:
            raise SiteRuleEvidenceError(
                "fixture is not discriminating: cumulative increase never reaches a full raise"
            )


@dataclass(frozen=True)
class OddChipSplitFixture:
    button_position: str
    clockwise_live_positions: tuple[str, ...]
    tied_winners: tuple[str, ...]
    pot_amount_chips: int
    odd_chip_recipients: tuple[str, ...]

    def __post_init__(self) -> None:
        live = self.clockwise_live_positions
        winners = self.tied_winners
        recipients = self.odd_chip_recipients
        if len(live) < 2 or len(set(live)) != len(live):
            raise SiteRuleEvidenceError("live positions must be unique and contain 2+ seats")
        if self.button_position not in live:
            raise SiteRuleEvidenceError("button position must be live")
        if len(winners) < 2 or len(set(winners)) != len(winners):
            raise SiteRuleEvidenceError("odd-chip fixture requires 2+ unique tied winners")
        if not set(winners).issubset(live):
            raise SiteRuleEvidenceError("every tied winner must be live")
        if self.pot_amount_chips <= 0:
            raise SiteRuleEvidenceError("pot must be positive")
        remainder = self.pot_amount_chips % len(winners)
        if len(recipients) != remainder or len(set(recipients)) != len(recipients):
            raise SiteRuleEvidenceError(
                "odd-chip recipients must match the exact split remainder"
            )
        if not set(recipients).issubset(winners):
            raise SiteRuleEvidenceError("odd chips may be awarded only to tied winners")


@dataclass(frozen=True)
class RakeSettlementFixture:
    player_count: int
    small_blind_chips: int
    big_blind_chips: int
    street_reached: ObservedStreet
    preflop_raise_count: int
    observed_total_contributions: int
    contested_pots_before_rake: tuple[int, ...]
    uncalled_return_chips: int
    rake_charged_chips: int
    net_payouts_total_chips: int

    def __post_init__(self) -> None:
        if not 2 <= self.player_count <= 6:
            raise SiteRuleEvidenceError("player_count must be in 2..6")
        if self.small_blind_chips <= 0 or self.big_blind_chips <= self.small_blind_chips:
            raise SiteRuleEvidenceError("invalid blind structure")
        if self.preflop_raise_count < 0:
            raise SiteRuleEvidenceError("preflop_raise_count cannot be negative")
        if not self.contested_pots_before_rake or any(
            pot <= 0 for pot in self.contested_pots_before_rake
        ):
            raise SiteRuleEvidenceError("one or more positive contested pots are required")
        values = (
            self.observed_total_contributions,
            self.uncalled_return_chips,
            self.rake_charged_chips,
            self.net_payouts_total_chips,
        )
        if any(value < 0 for value in values):
            raise SiteRuleEvidenceError("chip observations cannot be negative")
        contested = sum(self.contested_pots_before_rake)
        if contested + self.uncalled_return_chips != self.observed_total_contributions:
            raise SiteRuleEvidenceError(
                "contributions must equal contested pots plus uncalled return"
            )
        if self.rake_charged_chips + self.net_payouts_total_chips != contested:
            raise SiteRuleEvidenceError(
                "contested pots must equal rake plus net payouts"
            )


EvidencePayload = (
    CumulativeShortAllInFixture | OddChipSplitFixture | RakeSettlementFixture
)


@dataclass(frozen=True)
class SiteRuleEvidenceEnvelope:
    scenario: EvidenceScenario
    source_kind: EvidenceSourceKind
    source_locator: str
    source_sha256: str
    captured_at_utc: str
    site_name: str
    client_build: str
    personal_data_removed: bool
    payload: EvidencePayload
    notes: str = ""
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise SiteRuleEvidenceError("unsupported evidence schema version")
        if not self.source_locator.strip() or not self.site_name.strip():
            raise SiteRuleEvidenceError("source_locator and site_name are required")
        if not self.client_build.strip():
            raise SiteRuleEvidenceError("client_build is required")
        if not _SHA256_RE.fullmatch(self.source_sha256):
            raise SiteRuleEvidenceError("source_sha256 must be lowercase SHA-256 hex")
        if not self.personal_data_removed:
            raise SiteRuleEvidenceError(
                "evidence containing player names/account/table identifiers is rejected"
            )
        try:
            captured = datetime.fromisoformat(self.captured_at_utc.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SiteRuleEvidenceError("captured_at_utc must be ISO-8601") from exc
        if captured.tzinfo is None or captured.utcoffset() != timezone.utc.utcoffset(captured):
            raise SiteRuleEvidenceError("captured_at_utc must include a UTC offset")
        expected = {
            EvidenceScenario.CUMULATIVE_SHORT_ALL_IN_REOPEN: CumulativeShortAllInFixture,
            EvidenceScenario.ODD_CHIP_SPLIT: OddChipSplitFixture,
            EvidenceScenario.RAKE_SETTLEMENT: RakeSettlementFixture,
        }[self.scenario]
        if not isinstance(self.payload, expected):
            raise SiteRuleEvidenceError(
                f"payload type does not match scenario {self.scenario.value}"
            )

    def canonical_json(self) -> str:
        return json.dumps(
            _jsonable(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def fingerprint_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _strict_keys(
    data: Mapping[str, Any],
    cls: type[Any],
    *,
    optional: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    allowed = {field.name for field in fields(cls)}
    supplied = set(data)
    extra = supplied - allowed
    missing = allowed - supplied - set(optional)
    if extra or missing:
        raise SiteRuleEvidenceError(
            f"{cls.__name__} keys mismatch; missing={sorted(missing)} extra={sorted(extra)}"
        )
    return dict(data)


def _payload_from_dict(
    scenario: EvidenceScenario,
    data: Mapping[str, Any],
) -> EvidencePayload:
    if scenario == EvidenceScenario.CUMULATIVE_SHORT_ALL_IN_REOPEN:
        values = _strict_keys(data, CumulativeShortAllInFixture)
        values["short_all_in_targets"] = tuple(values["short_all_in_targets"])
        return CumulativeShortAllInFixture(**values)
    if scenario == EvidenceScenario.ODD_CHIP_SPLIT:
        values = _strict_keys(data, OddChipSplitFixture)
        for key in ("clockwise_live_positions", "tied_winners", "odd_chip_recipients"):
            values[key] = tuple(values[key])
        return OddChipSplitFixture(**values)
    if scenario == EvidenceScenario.RAKE_SETTLEMENT:
        values = _strict_keys(data, RakeSettlementFixture)
        values["street_reached"] = ObservedStreet(values["street_reached"])
        values["contested_pots_before_rake"] = tuple(
            values["contested_pots_before_rake"]
        )
        return RakeSettlementFixture(**values)
    raise AssertionError(scenario)


def evidence_envelope_from_dict(
    data: Mapping[str, Any],
) -> SiteRuleEvidenceEnvelope:
    values = _strict_keys(
        data,
        SiteRuleEvidenceEnvelope,
        optional=frozenset({"notes", "schema_version"}),
    )
    scenario = EvidenceScenario(values["scenario"])
    payload_data = values["payload"]
    if not isinstance(payload_data, Mapping):
        raise SiteRuleEvidenceError("payload must be a JSON object")
    values["scenario"] = scenario
    values["source_kind"] = EvidenceSourceKind(values["source_kind"])
    values["payload"] = _payload_from_dict(scenario, payload_data)
    values.setdefault("notes", "")
    values.setdefault("schema_version", 1)
    return SiteRuleEvidenceEnvelope(**values)


def load_evidence_file(path: str | Path) -> SiteRuleEvidenceEnvelope:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SiteRuleEvidenceError(f"cannot read evidence file {source}") from exc
    if not isinstance(data, Mapping):
        raise SiteRuleEvidenceError("evidence file root must be a JSON object")
    return evidence_envelope_from_dict(data)
