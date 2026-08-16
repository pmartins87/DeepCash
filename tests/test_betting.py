import pytest

from deepcash_core.betting import BettingRoundState, StreetAction, StreetActionKind


def act(kind, raise_to=None):
    return StreetAction(StreetActionKind(kind), raise_to)


def test_preflop_full_raise_updates_minimum_and_round_closes_after_calls():
    st = BettingRoundState.create(
        order=(0, 1, 2),
        stacks={0: 1000, 1: 950, 2: 900},
        committed={1: 50, 2: 100},
        min_bet=100,
    )
    assert st.actor == 0
    assert st.legal_actions().to_call == 100
    st = st.apply(act("RAISE_TO", 300))
    assert st.current_bet == 300
    assert st.last_full_raise == 200
    assert st.actor == 1
    assert st.legal_actions().min_full_raise_to == 500
    st = st.apply(act("CALL"))
    st = st.apply(act("CALL"))
    assert st.complete


def test_single_short_allin_does_not_reopen_prior_bettor():
    st = BettingRoundState.create(order=(0, 1), stacks={0: 1000, 1: 150}, min_bet=100)
    st = st.apply(act("RAISE_TO", 100))
    st = st.apply(act("RAISE_TO", 150))
    assert st.actor == 0
    legal = st.legal_actions()
    assert legal.to_call == 50
    assert legal.can_raise is False
    st = st.apply(act("CALL"))
    assert st.complete


def test_cumulative_short_allins_can_reopen_when_full_increment_is_reached():
    # Seat 0 bets 100. Two all-ins add 50 each. Neither is a full raise by
    # itself, but seat 0 now faces a cumulative 100 increase, which reopens.
    st = BettingRoundState.create(order=(0, 1, 2), stacks={0: 1000, 1: 150, 2: 200}, min_bet=100)
    st = st.apply(act("RAISE_TO", 100))
    st = st.apply(act("RAISE_TO", 150))
    assert st.last_full_raise == 100
    st = st.apply(act("RAISE_TO", 200))
    assert st.actor == 0
    legal = st.legal_actions()
    assert legal.to_call == 100
    assert legal.can_raise is True
    assert legal.min_full_raise_to == 300


def test_subminimum_non_allin_raise_is_rejected():
    st = BettingRoundState.create(order=(0, 1), stacks={0: 1000, 1: 1000}, min_bet=100)
    with pytest.raises(ValueError):
        st.apply(act("RAISE_TO", 50))
