import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import RangeCombo, RiverGameSpec, solve_river_cfr_plus
from deepcash_core.river_reference_lab import (
    AsymmetricRiverGameSpec,
    evaluate_restriction_loss,
    solve_asymmetric_river_cfr_plus,
)


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str) -> RangeCombo:
    return RangeCombo((c(a), c(b)))


def ranges():
    p0 = (
        combo("Qs", "Qh"),
        combo("Jc", "Js"),
        combo("Tc", "Ts"),
        combo("Ac", "Qc"),
    )
    p1 = (
        combo("Qd", "Jh"),
        combo("Jd", "Th"),
        combo("9d", "8h"),
        combo("Ad", "Td"),
    )
    return p0, p1


def board():
    return (c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h"))


def test_symmetric_reference_solver_matches_legacy_one_bet_game_numerically():
    p0, p1 = ranges()
    legacy = solve_river_cfr_plus(
        RiverGameSpec(board(), p0, p1, pot=100, bet_sizes=(33, 100)),
        iterations=200,
    )
    reference = solve_asymmetric_river_cfr_plus(
        AsymmetricRiverGameSpec(
            board(), p0, p1, pot=100,
            p0_bet_sizes=(33, 100), p1_bet_sizes=(33, 100),
        ),
        iterations=200,
    )
    assert reference.policy_ev == legacy.policy_ev
    assert reference.br0_value == legacy.br0_value
    assert reference.br1_value == legacy.br1_value
    assert reference.exploitability == legacy.exploitability
    assert reference.infosets == legacy.infosets
    assert reference.action_slots == legacy.action_slots


def test_reference_candidate_has_only_solver_uncertainty_as_restriction_upper_bound():
    p0, p1 = ranges()
    result = evaluate_restriction_loss(
        board=board(),
        p0_range=p0,
        p1_range=p1,
        pot=100,
        reference_sizes=(25, 75, 150),
        candidate_sizes=(25, 75, 150),
        iterations=150,
    )
    expected = result.reference.br0_value - result.reference.br1_value
    assert result.worst_loss_upper == pytest.approx(expected)
    assert result.worst_loss_upper_per_pot == pytest.approx(expected / 100.0)


def test_subset_restriction_reports_separate_p0_and_p1_value_loss_bounds():
    p0, p1 = ranges()
    result = evaluate_restriction_loss(
        board=board(),
        p0_range=p0,
        p1_range=p1,
        pot=100,
        reference_sizes=(25, 75, 150),
        candidate_sizes=(75,),
        iterations=250,
    )
    assert result.p0_loss_lower <= result.p0_loss_upper
    assert result.p1_loss_lower <= result.p1_loss_upper
    assert result.worst_loss_upper >= 0.0
    assert result.worst_loss_upper_per_pot == pytest.approx(result.worst_loss_upper / 100.0)
    # The two restricted games are genuinely asymmetric structural controls.
    assert result.p0_restricted.infosets != result.reference.infosets
    assert result.p1_restricted.infosets != result.reference.infosets


def test_candidate_actions_must_be_contained_in_reference_game():
    p0, p1 = ranges()
    with pytest.raises(ValueError, match="subset"):
        evaluate_restriction_loss(
            board=board(),
            p0_range=p0,
            p1_range=p1,
            pot=100,
            reference_sizes=(25, 75),
            candidate_sizes=(25, 100),
            iterations=20,
        )
