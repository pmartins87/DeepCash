from __future__ import annotations

import json

import pytest

from deepcash_core.site_rule_evidence import (
    CumulativeShortAllInFixture,
    EvidenceScenario,
    EvidenceSourceKind,
    OddChipSplitFixture,
    ObservedStreet,
    RakeSettlementFixture,
    SiteRuleEvidenceEnvelope,
    SiteRuleEvidenceError,
    evidence_envelope_from_dict,
)


def envelope(payload, scenario):
    return SiteRuleEvidenceEnvelope(
        scenario=scenario,
        source_kind=EvidenceSourceKind.OBSERVED_HAND_HISTORY,
        source_locator="anonymized/fixture.json",
        source_sha256="0" * 64,
        captured_at_utc="2026-08-17T00:00:00Z",
        site_name="GGPoker",
        client_build="desktop-observed-build",
        personal_data_removed=True,
        payload=payload,
        notes="deterministic test fixture",
    )


def test_cumulative_short_all_in_fixture_is_discriminating():
    fixture = CumulativeShortAllInFixture(
        prior_actor_faced_bet=100,
        last_full_raise_increment=100,
        short_all_in_targets=(150, 200),
        observed_raise_reopened=True,
    )
    assert fixture.short_all_in_targets[-1] - fixture.prior_actor_faced_bet == 100

    with pytest.raises(SiteRuleEvidenceError, match="at least two"):
        CumulativeShortAllInFixture(100, 100, (150,), False)
    with pytest.raises(SiteRuleEvidenceError, match="smaller than a full raise"):
        CumulativeShortAllInFixture(100, 100, (150, 250), False)
    with pytest.raises(SiteRuleEvidenceError, match="not discriminating"):
        CumulativeShortAllInFixture(100, 100, (130, 180), False)


def test_odd_chip_fixture_requires_exact_remainder_and_winner():
    fixture = OddChipSplitFixture(
        button_position="BTN",
        clockwise_live_positions=("BTN", "SB", "BB"),
        tied_winners=("BTN", "BB"),
        pot_amount_chips=101,
        odd_chip_recipients=("BTN",),
    )
    assert fixture.odd_chip_recipients == ("BTN",)

    with pytest.raises(SiteRuleEvidenceError, match="exact split remainder"):
        OddChipSplitFixture(
            "BTN", ("BTN", "SB", "BB"), ("BTN", "BB"), 101, ()
        )
    with pytest.raises(SiteRuleEvidenceError, match="only to tied winners"):
        OddChipSplitFixture(
            "BTN", ("BTN", "SB", "BB"), ("BTN", "BB"), 101, ("SB",)
        )


def test_rake_fixture_enforces_chip_conservation():
    fixture = RakeSettlementFixture(
        player_count=6,
        small_blind_chips=50,
        big_blind_chips=100,
        street_reached=ObservedStreet.FLOP,
        preflop_raise_count=1,
        observed_total_contributions=1000,
        contested_pots_before_rake=(900,),
        uncalled_return_chips=100,
        rake_charged_chips=45,
        net_payouts_total_chips=855,
    )
    assert sum(fixture.contested_pots_before_rake) == 900

    with pytest.raises(SiteRuleEvidenceError, match="contributions must equal"):
        RakeSettlementFixture(
            6, 50, 100, ObservedStreet.FLOP, 1, 1001, (900,), 100, 45, 855
        )
    with pytest.raises(SiteRuleEvidenceError, match="rake plus net payouts"):
        RakeSettlementFixture(
            6, 50, 100, ObservedStreet.FLOP, 1, 1000, (900,), 100, 44, 855
        )


def test_envelope_rejects_personal_data_bad_hash_and_non_utc_time():
    payload = CumulativeShortAllInFixture(100, 100, (150, 200), True)
    common = dict(
        scenario=EvidenceScenario.CUMULATIVE_SHORT_ALL_IN_REOPEN,
        source_kind=EvidenceSourceKind.OBSERVED_HAND_HISTORY,
        source_locator="fixture.json",
        source_sha256="0" * 64,
        captured_at_utc="2026-08-17T00:00:00Z",
        site_name="GGPoker",
        client_build="known",
        personal_data_removed=True,
        payload=payload,
    )
    with pytest.raises(SiteRuleEvidenceError, match="personal"):
        SiteRuleEvidenceEnvelope(**{**common, "personal_data_removed": False})
    with pytest.raises(SiteRuleEvidenceError, match="SHA-256"):
        SiteRuleEvidenceEnvelope(**{**common, "source_sha256": "BAD"})
    with pytest.raises(SiteRuleEvidenceError, match="UTC"):
        SiteRuleEvidenceEnvelope(
            **{**common, "captured_at_utc": "2026-08-17T01:00:00+01:00"}
        )


def test_canonical_fingerprint_is_stable_across_json_roundtrip():
    original = envelope(
        OddChipSplitFixture(
            "BTN", ("BTN", "SB", "BB"), ("BTN", "BB"), 101, ("BTN",)
        ),
        EvidenceScenario.ODD_CHIP_SPLIT,
    )
    raw = json.loads(original.canonical_json())
    reordered = {key: raw[key] for key in reversed(tuple(raw))}
    restored = evidence_envelope_from_dict(reordered)

    assert restored.canonical_json() == original.canonical_json()
    assert restored.fingerprint_sha256() == original.fingerprint_sha256()


def test_parser_is_strict_and_scenario_payload_must_match():
    original = envelope(
        RakeSettlementFixture(
            6, 50, 100, ObservedStreet.FLOP, 1, 1000, (900,), 100, 45, 855
        ),
        EvidenceScenario.RAKE_SETTLEMENT,
    )
    raw = json.loads(original.canonical_json())
    raw["extra"] = "rejected"
    with pytest.raises(SiteRuleEvidenceError, match="extra"):
        evidence_envelope_from_dict(raw)

    raw = json.loads(original.canonical_json())
    raw["scenario"] = EvidenceScenario.ODD_CHIP_SPLIT.value
    with pytest.raises(SiteRuleEvidenceError, match="keys mismatch"):
        evidence_envelope_from_dict(raw)
