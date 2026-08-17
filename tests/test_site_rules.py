from dataclasses import replace
from fractions import Fraction

import pytest

from deepcash_core.betting import ShortAllInReopenPolicy
from deepcash_core.rake import RakeRounding
from deepcash_core.site_rules import (
    EvidenceStatus,
    GGPOKER_6MAX_REFERENCE,
    RakeApplicationTiming,
    RuleFact,
    SiteRuleContractError,
)


def confirmed(value):
    return RuleFact(
        status=EvidenceStatus.CONFIRMED,
        value=value,
        source="https://example.invalid/observed-fixture",
        note="test fixture",
    )


def test_ggpoker_reference_contains_published_6max_rake_grid():
    contract = GGPOKER_6MAX_REFERENCE
    assert contract.site_name == "GGPoker"
    assert len(contract.rake_rows) == 10
    row = contract.rake_row(
        small_blind_usd=Fraction("0.50"),
        big_blind_usd=Fraction("1"),
    )
    assert row.rate == Fraction(1, 20)
    assert row.cap_bb(2) == Fraction("1.25")
    assert row.cap_bb(6) == Fraction(5, 1)


def test_unresolved_rules_fail_closed():
    contract = GGPOKER_6MAX_REFERENCE
    assert contract.unresolved_critical_rules() == (
        "rake_rounding",
        "rake_application_timing",
        "short_all_in_reopen",
        "odd_chip_order",
    )
    with pytest.raises(SiteRuleContractError, match="not production-ready"):
        contract.require_critical_rules()
    with pytest.raises(SiteRuleContractError, match="short_all_in_reopen is unresolved"):
        contract.betting_config()
    with pytest.raises(SiteRuleContractError, match="rake_rounding is unresolved"):
        contract.rake_policy(
            small_blind_usd=Fraction("0.50"),
            big_blind_usd=Fraction("1"),
            player_count=6,
            big_blind_chips=100,
        )


def test_confirmed_adapter_facts_materialize_existing_engine_configs():
    contract = replace(
        GGPOKER_6MAX_REFERENCE,
        rake_rounding=confirmed(RakeRounding.FLOOR),
        rake_application_timing=confirmed(
            RakeApplicationTiming.CONTESTED_POTS_AFTER_UNCALLED_RETURN
        ),
        short_all_in_reopen=confirmed(ShortAllInReopenPolicy.CUMULATIVE_FULL_RAISE),
    )
    betting = contract.betting_config()
    assert betting.short_all_in_reopen == ShortAllInReopenPolicy.CUMULATIVE_FULL_RAISE

    rake = contract.rake_policy(
        small_blind_usd=Fraction("0.50"),
        big_blind_usd=Fraction("1"),
        player_count=6,
        big_blind_chips=100,
    )
    assert rake.rate == Fraction(1, 20)
    assert rake.cap == 500
    assert rake.rounding == RakeRounding.FLOOR


def test_unknown_stake_and_fractional_engine_chip_cap_are_rejected():
    contract = replace(
        GGPOKER_6MAX_REFERENCE,
        rake_rounding=confirmed(RakeRounding.FLOOR),
        rake_application_timing=confirmed(
            RakeApplicationTiming.CONTESTED_POTS_AFTER_UNCALLED_RETURN
        ),
    )
    with pytest.raises(SiteRuleContractError, match="no confirmed rake row"):
        contract.rake_policy(
            small_blind_usd=Fraction("25"),
            big_blind_usd=Fraction("50"),
            player_count=6,
            big_blind_chips=100,
        )
    with pytest.raises(SiteRuleContractError, match="not integral"):
        contract.rake_policy(
            small_blind_usd=Fraction("0.02"),
            big_blind_usd=Fraction("0.05"),
            player_count=2,
            big_blind_chips=1,
        )


def test_rule_fact_never_hides_assumptions():
    with pytest.raises(ValueError, match="require both value and source"):
        RuleFact(
            status=EvidenceStatus.CONFIRMED,
            value=RakeRounding.FLOOR,
            source=None,
            note="missing evidence",
        )
    with pytest.raises(ValueError, match="cannot carry a value"):
        RuleFact(
            status=EvidenceStatus.UNRESOLVED,
            value=RakeRounding.FLOOR,
            source=None,
            note="contradictory state",
        )
