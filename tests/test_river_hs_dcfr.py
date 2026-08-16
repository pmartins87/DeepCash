import json

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_hs_dcfr import (
    PaperDCFRVariant,
    _discount_old_then_add_regrets,
    _discount_then_add_player_average,
    advance_paper_dcfr,
    init_paper_dcfr,
    paper_dcfr_result,
    paper_dcfr_state_from_dict,
    paper_dcfr_state_to_dict,
    parameters_for,
    regret_discount_factor,
)
from deepcash_core.river_lab import P1_AFTER_CHECK, RangeCombo, RiverGameSpec, _actions, _all_infosets, _regret_strategy


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str) -> RangeCombo:
    return RangeCombo((c(a), c(b)))


def fixture_spec() -> RiverGameSpec:
    return RiverGameSpec(
        board=(c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h")),
        p0_range=(combo("Qs", "Qh"), combo("Jc", "Js"), combo("8c", "8d")),
        p1_range=(combo("Qd", "Jh"), combo("Jd", "Th"), combo("6c", "6d")),
        pot=100,
        bet_sizes=(25, 50, 100),
    )


def test_paper_regret_recurrence_discounts_old_before_adding_instantaneous():
    spec = fixture_spec()
    state = init_paper_dcfr(spec, PaperDCFRVariant.PAPER_DCFR_150_0_2, horizon=10)
    key = next(key for key in state.regrets if key[0] == 0 and len(state.regrets[key]) >= 2)
    state.regrets[key][0] = 8.0
    state.regrets[key][1] = -8.0
    delta = {k: [0.0] * len(v) for k, v in state.regrets.items()}
    delta[key][0] = -3.0
    delta[key][1] = 3.0

    _discount_old_then_add_regrets(
        state,
        delta,
        player=0,
        iteration=4,
        alpha=1.5,
        beta=0.0,
    )
    pos_factor = regret_discount_factor(4, 1.5)
    neg_factor = regret_discount_factor(4, 0.0)
    assert state.regrets[key][0] == pytest.approx(8.0 * pos_factor - 3.0)
    assert state.regrets[key][1] == pytest.approx(-8.0 * neg_factor + 3.0)
    # Explicitly distinguish from the historical post-update-discount variant.
    assert state.regrets[key][0] != pytest.approx((8.0 - 3.0) * pos_factor)


def test_paper_average_recurrence_discounts_old_then_adds_current_policy():
    spec = fixture_spec()
    state = init_paper_dcfr(spec, PaperDCFRVariant.PAPER_DCFR_150_0_2, horizon=10)
    infosets = _all_infosets(spec)
    strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
    key = (1, P1_AFTER_CHECK, 0)
    state.strategy_sum[key] = [2.0] * len(state.strategy_sum[key])

    _discount_then_add_player_average(
        spec,
        state,
        strategies,
        player=1,
        iteration=3,
        gamma=2.0,
    )
    factor = (3.0 / 4.0) ** 2
    assert state.strategy_sum[key] == pytest.approx(
        [2.0 * factor + p for p in strategies[key]]
    )


def test_hs_schedule_coordinates_are_exact():
    n = 1200
    p1 = parameters_for(PaperDCFRVariant.HS_DCFR_30, iteration=1, horizon=n)
    assert p1.alpha == pytest.approx(1.0 + 3.0 / n)
    assert p1.beta == pytest.approx(-1.0 - 2.0 / n)
    assert p1.gamma == pytest.approx(30.0 - 5.0 / n)

    pmid = parameters_for(PaperDCFRVariant.HS_DCFR_15, iteration=600, horizon=n)
    assert pmid.alpha == pytest.approx(2.5)
    assert pmid.beta == pytest.approx(-2.0)
    assert pmid.gamma == pytest.approx(12.5)

    pend = parameters_for(PaperDCFRVariant.HS_DCFR_30, iteration=n, horizon=n)
    assert pend.alpha == pytest.approx(4.0)
    assert pend.beta == pytest.approx(-3.0)
    assert pend.gamma == pytest.approx(25.0)


@pytest.mark.parametrize("variant", list(PaperDCFRVariant))
def test_staged_matches_monolithic_for_every_paper_variant(variant):
    spec = fixture_spec()
    staged = init_paper_dcfr(spec, variant, horizon=100)
    advance_paper_dcfr(spec, staged, additional_iterations=35)
    advance_paper_dcfr(spec, staged, additional_iterations=65)

    monolithic = init_paper_dcfr(spec, variant, horizon=100)
    advance_paper_dcfr(spec, monolithic, additional_iterations=100)
    assert staged == monolithic
    assert paper_dcfr_result(spec, staged) == paper_dcfr_result(spec, monolithic)


@pytest.mark.parametrize("variant", list(PaperDCFRVariant))
def test_json_roundtrip_preserves_future_path_and_horizon(variant):
    spec = fixture_spec()
    state = init_paper_dcfr(spec, variant, horizon=100)
    advance_paper_dcfr(spec, state, additional_iterations=40)
    payload = json.loads(json.dumps(paper_dcfr_state_to_dict(state)))
    restored = paper_dcfr_state_from_dict(
        spec,
        payload,
        expected_variant=variant,
        expected_horizon=100,
    )
    assert restored == state

    advance_paper_dcfr(spec, state, additional_iterations=60)
    advance_paper_dcfr(spec, restored, additional_iterations=60)
    assert restored == state


def test_horizon_mismatch_and_overrun_fail_closed():
    spec = fixture_spec()
    state = init_paper_dcfr(spec, PaperDCFRVariant.HS_DCFR_15, horizon=100)
    payload = paper_dcfr_state_to_dict(state)
    with pytest.raises(ValueError, match="horizon"):
        paper_dcfr_state_from_dict(spec, payload, expected_horizon=120)
    with pytest.raises(ValueError, match="exceed"):
        advance_paper_dcfr(spec, state, additional_iterations=101)


def test_player_half_step_does_not_mutate_other_players_regrets_or_average():
    spec = fixture_spec()
    state = init_paper_dcfr(spec, PaperDCFRVariant.PAPER_DCFR_150_0_2, horizon=10)
    infosets = _all_infosets(spec)
    strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
    p1_regrets = {k: tuple(v) for k, v in state.regrets.items() if k[0] == 1}
    p1_average = {k: tuple(v) for k, v in state.strategy_sum.items() if k[0] == 1}

    _discount_then_add_player_average(
        spec, state, strategies, player=0, iteration=1, gamma=2.0
    )
    zero_delta = {k: [0.0] * len(v) for k, v in state.regrets.items()}
    _discount_old_then_add_regrets(
        state, zero_delta, player=0, iteration=1, alpha=1.5, beta=0.0
    )
    assert {k: tuple(v) for k, v in state.regrets.items() if k[0] == 1} == p1_regrets
    assert {k: tuple(v) for k, v in state.strategy_sum.items() if k[0] == 1} == p1_average


def test_nonfinite_checkpoint_fails_closed():
    spec = fixture_spec()
    state = init_paper_dcfr(spec, PaperDCFRVariant.PAPER_DCFR_150_0_2, horizon=10)
    payload = paper_dcfr_state_to_dict(state)
    key = next(iter(payload["regrets"]))
    payload["regrets"][key][0] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        paper_dcfr_state_from_dict(spec, payload)
