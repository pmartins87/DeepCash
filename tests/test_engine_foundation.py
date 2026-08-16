from fractions import Fraction

import pytest

from deepcash_core.cards import card_from_str, card_to_str, full_deck
from deepcash_core.evaluator import evaluate_best, evaluate_five
from deepcash_core.pots import award_side_pots, build_side_pots, normalize_uncalled
from deepcash_core.rake import RakePolicy, RakeRounding
from deepcash_core.seating import build_seat_plan


def cards(text: str):
    return [card_from_str(x) for x in text.split()]


def test_card_codec_is_bijective_over_52_cards():
    deck = full_deck()
    assert len(deck) == len(set(deck)) == 52
    assert [card_from_str(card_to_str(c)) for c in deck] == list(deck)


def test_standard_holdem_hand_order_and_wheel():
    straight_flush = evaluate_five(cards("As Ks Qs Js Ts"))
    quads = evaluate_five(cards("Ah Ad Ac As Kd"))
    full_house = evaluate_five(cards("Kh Kd Kc 2s 2d"))
    flush = evaluate_five(cards("As Js 9s 6s 3s"))
    straight = evaluate_five(cards("9c 8d 7s 6h 5c"))
    trips = evaluate_five(cards("Qc Qd Qs 8h 2c"))
    two_pair = evaluate_five(cards("Jc Jd 4s 4h Ac"))
    pair = evaluate_five(cards("Tc Td As 7h 3c"))
    high = evaluate_five(cards("As Jd 9c 6h 3s"))
    assert straight_flush > quads > full_house > flush > straight > trips > two_pair > pair > high
    assert evaluate_five(cards("As 2d 3c 4h 5s")) == (4, 5)


def test_best_of_seven_selects_true_best_five():
    assert evaluate_best(cards("As Ad Ac Kc Kd 2h 3s")) == (6, 14, 13)


def test_seat_plan_six_max_and_heads_up_orders():
    six = build_seat_plan((0, 1, 2, 3, 4, 5), button=3)
    assert (six.small_blind, six.big_blind) == (4, 5)
    assert six.preflop_order == (0, 1, 2, 3, 4, 5)
    assert six.postflop_order == (4, 5, 0, 1, 2, 3)

    hu = build_seat_plan((2, 5), button=2)
    assert (hu.small_blind, hu.big_blind) == (2, 5)
    assert hu.preflop_order == (2, 5)
    assert hu.postflop_order == (5, 2)


def test_uncalled_excess_is_removed_before_side_pots():
    normalized, ret = normalize_uncalled({0: 100, 1: 300})
    assert normalized == {0: 100, 1: 100}
    assert ret is not None and (ret.seat, ret.amount) == (1, 200)
    assert build_side_pots(normalized, {1})[0].amount == 200


def test_multiway_side_pots_and_odd_chip_award():
    normalized, ret = normalize_uncalled({0: 100, 1: 250, 2: 250})
    assert ret is None
    pots = build_side_pots(normalized, {0, 1, 2})
    assert [p.amount for p in pots] == [300, 300]
    payouts = award_side_pots(
        pots,
        {0: (8, 14), 1: (5, 14, 12, 9, 8, 7), 2: (5, 14, 12, 9, 8, 7)},
        odd_chip_order=(2, 0, 1),
    )
    assert payouts == {0: 300, 2: 150, 1: 150}
    assert sum(payouts.values()) == 600


def test_rake_never_silently_rounds_unknown_client_rule():
    policy = RakePolicy(Fraction(1, 20))
    assert policy.exact(101) == Fraction(101, 20)
    with pytest.raises(ValueError, match="rounding is unspecified"):
        policy.charged(101)
    assert RakePolicy(Fraction(1, 20), rounding=RakeRounding.FLOOR).charged(101) == 5
    assert RakePolicy(Fraction(1, 20), cap=4, rounding=RakeRounding.CEIL).charged(101) == 4
