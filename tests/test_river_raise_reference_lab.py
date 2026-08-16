import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import RangeCombo
from deepcash_core.river_raise_lab import RiverRaiseGameSpec, solve_river_raise_cfr_plus
from deepcash_core.river_raise_reference_lab import (
    AsymmetricRiverRaiseGameSpec,
    evaluate_opening_restriction_loss_with_raises,
    solve_asymmetric_river_raise_cfr_plus,
)


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str) -> RangeCombo:
    return RangeCombo((c(a), c(b)))


def board():
    return (c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h"))


def ranges():
    return (
        (combo("Qs", "Qh"), combo("Ac", "Qc")),
        (combo("Qd", "Jh"), combo("Ad", "Td")),
    )


def test_symmetric_asymmetric_one_raise_solver_matches_original_control():
    p0, p1 = ranges()
    old = solve_river_raise_cfr_plus(
        RiverRaiseGameSpec(
            board(), p0, p1, pot=100,
            bet_sizes=(50,),
            raise_targets=((50, (150,)),),
        ),
        iterations=180,
    )
    new = solve_asymmetric_river_raise_cfr_plus(
        AsymmetricRiverRaiseGameSpec(
            board(), p0, p1, pot=100,
            p0_bet_sizes=(50,),
            p1_bet_sizes=(50,),
            p1_raise_targets_vs_p0=((50, (150,)),),
            p0_raise_targets_vs_p1=((50, (150,)),),
        ),
        iterations=180,
    )
    assert new.policy_ev == old.policy_ev
    assert new.br0_value == old.br0_value
    assert new.br1_value == old.br1_value
    assert new.exploitability == old.exploitability
    assert new.infosets == old.infosets
    assert new.action_slots == old.action_slots


def test_equal_candidate_reference_has_only_solver_interval_as_upper_bound():
    p0, p1 = ranges()
    result = evaluate_opening_restriction_loss_with_raises(
        board=board(),
        p0_range=p0,
        p1_range=p1,
        pot=100,
        reference_sizes=(50,),
        candidate_sizes=(50,),
        reference_raise_targets=((50, (150,)),),
        iterations=140,
    )
    expected = result.reference.br0_value - result.reference.br1_value
    assert result.worst_loss_upper == pytest.approx(expected)
    assert result.worst_loss_upper_per_pot == pytest.approx(expected / 100.0)


def test_opening_restriction_keeps_reference_raise_responses_and_produces_valid_bounds():
    p0, p1 = ranges()
    result = evaluate_opening_restriction_loss_with_raises(
        board=board(),
        p0_range=p0,
        p1_range=p1,
        pot=100,
        reference_sizes=(25, 75),
        candidate_sizes=(75,),
        reference_raise_targets=((25, (100,)), (75, (200,))),
        iterations=180,
    )
    assert result.p0_loss_lower <= result.p0_loss_upper
    assert result.p1_loss_lower <= result.p1_loss_upper
    assert result.worst_loss_upper >= 0.0
    assert result.p0_restricted.infosets < result.reference.infosets
    assert result.p1_restricted.infosets < result.reference.infosets


def test_candidate_must_be_subset_of_reference_opening_sizes():
    p0, p1 = ranges()
    with pytest.raises(ValueError, match="subset"):
        evaluate_opening_restriction_loss_with_raises(
            board=board(),
            p0_range=p0,
            p1_range=p1,
            pot=100,
            reference_sizes=(25, 75),
            candidate_sizes=(25, 100),
            reference_raise_targets=((25, (100,)), (75, (200,))),
            iterations=20,
        )


def test_raise_map_must_cover_every_faced_bet():
    p0, p1 = ranges()
    with pytest.raises(ValueError, match="cover every faced opening bet"):
        AsymmetricRiverRaiseGameSpec(
            board(), p0, p1, pot=100,
            p0_bet_sizes=(25, 75),
            p1_bet_sizes=(25,),
            p1_raise_targets_vs_p0=((25, (100,)),),
            p0_raise_targets_vs_p1=((25, (100,)),),
        )
