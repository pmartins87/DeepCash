import pytest

from deepcash_core.betting import (
    BettingConfig,
    BettingRoundState,
    ShortAllInReopenPolicy,
    StreetAction,
    StreetActionKind,
)
from deepcash_core.cards import card_from_str
from deepcash_core.hand import HandSetup, HandState, Street
from deepcash_core.pots import SidePot, award_side_pots


def A(kind: str, raise_to: int | None = None) -> StreetAction:
    return StreetAction(StreetActionKind(kind), raise_to)


def c(text: str) -> int:
    return card_from_str(text)


def test_cumulative_short_raises_just_below_full_raise_do_not_reopen_prior_actor():
    # Player 0 bets 100. Two all-in raises move the price to 180, only +80 total
    # from the price P0 last faced. Under cumulative-full-raise semantics P0 may
    # call/fold but may not raise when action returns.
    st = BettingRoundState.create(
        order=(0, 1, 2, 3),
        stacks={0: 1000, 1: 140, 2: 180, 3: 1000},
        min_bet=100,
        config=BettingConfig(
            short_all_in_reopen=ShortAllInReopenPolicy.CUMULATIVE_FULL_RAISE
        ),
    )
    st = st.apply(A("RAISE_TO", 100))
    st = st.apply(A("RAISE_TO", 140))
    st = st.apply(A("RAISE_TO", 180))
    st = st.apply(A("CALL"))
    assert st.actor == 0
    legal = st.legal_actions()
    assert legal.to_call == 80
    assert legal.raise_right_open is False
    assert legal.can_raise is False


def test_cumulative_short_raises_exactly_full_raise_reopen_prior_actor():
    # Same geometry, but the aggregate short-raise increase reaches exactly 100.
    st = BettingRoundState.create(
        order=(0, 1, 2, 3),
        stacks={0: 1000, 1: 150, 2: 200, 3: 1000},
        min_bet=100,
        config=BettingConfig(
            short_all_in_reopen=ShortAllInReopenPolicy.CUMULATIVE_FULL_RAISE
        ),
    )
    st = st.apply(A("RAISE_TO", 100))
    st = st.apply(A("RAISE_TO", 150))
    st = st.apply(A("RAISE_TO", 200))
    st = st.apply(A("CALL"))
    assert st.actor == 0
    legal = st.legal_actions()
    assert legal.to_call == 100
    assert legal.raise_right_open is True
    assert legal.can_raise is True
    assert legal.min_full_raise_to == 300


def test_any_increase_policy_and_never_policy_are_materially_distinct():
    base = dict(order=(0, 1, 2), stacks={0: 1000, 1: 150, 2: 1000}, min_bet=100)

    any_inc = BettingRoundState.create(
        **base,
        config=BettingConfig(short_all_in_reopen=ShortAllInReopenPolicy.ANY_INCREASE),
    )
    any_inc = any_inc.apply(A("RAISE_TO", 100))
    any_inc = any_inc.apply(A("RAISE_TO", 150))
    any_inc = any_inc.apply(A("CALL"))
    assert any_inc.actor == 0
    assert any_inc.legal_actions().raise_right_open is True
    assert any_inc.legal_actions().can_raise is True

    never = BettingRoundState.create(
        **base,
        config=BettingConfig(short_all_in_reopen=ShortAllInReopenPolicy.NEVER),
    )
    never = never.apply(A("RAISE_TO", 100))
    never = never.apply(A("RAISE_TO", 150))
    never = never.apply(A("CALL"))
    assert never.actor == 0
    assert never.legal_actions().raise_right_open is False
    assert never.legal_actions().can_raise is False


def test_four_way_nested_preflop_sidepots_settle_each_eligibility_layer_exactly():
    # Four players, button=0 => preflop action order 3,0,1,2.
    # Contributions end at 300/500/800/800, yielding:
    # main 1200 (all four), side1 600 (0/1/2), side2 600 (1/2).
    # AA / KK / QQ are deliberately arranged to win one layer each.
    setup = HandSetup(
        occupied_clockwise=(0, 1, 2, 3),
        button=0,
        stacks={0: 500, 1: 800, 2: 1000, 3: 300},
        small_blind=50,
        big_blind=100,
        hole_cards={
            0: (c("Ks"), c("Kd")),
            1: (c("Qs"), c("Qd")),
            2: (c("Js"), c("Jd")),
            3: (c("As"), c("Ad")),
        },
        board=(c("2c"), c("3h"), c("6c"), c("8h"), c("9s")),
    )
    state = HandState.new(setup)
    assert state.actor == 3
    state = state.apply(A("RAISE_TO", 300))
    state = state.apply(A("RAISE_TO", 500))
    state = state.apply(A("RAISE_TO", 800))
    state = state.apply(A("CALL"))

    assert state.street == Street.SHOWDOWN
    assert state.total_contributed == {0: 500, 1: 800, 2: 800, 3: 300}
    assert state.remaining == {0: 0, 1: 0, 2: 200, 3: 0}
    assert state.gross_settlement() == {3: 1200, 0: 600, 1: 600}
    assert sum(state.remaining.values()) + sum(state.gross_settlement().values()) == 2600


def test_odd_chip_order_is_explicit_not_implicitly_seat_sorted():
    pot = SidePot(amount=5, contributors=(2, 7), eligible=(2, 7))
    hand_values = {2: (1, 14, 13, 12, 11), 7: (1, 14, 13, 12, 11)}
    assert award_side_pots((pot,), hand_values, odd_chip_order=(7, 2)) == {2: 2, 7: 3}
    assert award_side_pots((pot,), hand_values, odd_chip_order=(2, 7)) == {2: 3, 7: 2}


def test_odd_chip_order_must_cover_winners():
    pot = SidePot(amount=5, contributors=(2, 7), eligible=(2, 7))
    hand_values = {2: (1, 14), 7: (1, 14)}
    with pytest.raises(ValueError):
        award_side_pots((pot,), hand_values, odd_chip_order=(2,))


def test_odd_chip_order_rejects_duplicate_seats():
    pot = SidePot(amount=5, contributors=(2, 7), eligible=(2, 7))
    hand_values = {2: (1, 14), 7: (1, 14)}
    with pytest.raises(ValueError):
        award_side_pots((pot,), hand_values, odd_chip_order=(2, 7, 2))
