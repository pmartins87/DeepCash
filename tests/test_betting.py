import pytest

from deepcash_core.betting import (
    BettingConfig,
    BettingRoundState,
    ShortAllInReopenPolicy,
    StreetAction,
    StreetActionKind,
)


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


def test_single_short_allin_does_not_reopen_prior_bettor_or_allow_dry_raise():
    st = BettingRoundState.create(order=(0, 1), stacks={0: 1000, 1: 150}, min_bet=100)
    st = st.apply(act("RAISE_TO", 100))
    st = st.apply(act("RAISE_TO", 150))
    assert st.actor == 0
    legal = st.legal_actions()
    assert legal.to_call == 50
    assert legal.raise_right_open is False
    assert legal.can_raise is False
    st = st.apply(act("CALL"))
    assert st.complete


def test_cumulative_short_allins_reopen_right_but_not_dry_side_raise():
    st = BettingRoundState.create(order=(0, 1, 2), stacks={0: 1000, 1: 150, 2: 200}, min_bet=100)
    st = st.apply(act("RAISE_TO", 100))
    st = st.apply(act("RAISE_TO", 150))
    st = st.apply(act("RAISE_TO", 200))
    assert st.actor == 0
    legal = st.legal_actions()
    assert legal.to_call == 100
    assert legal.raise_right_open is True
    assert legal.can_raise is False  # both opponents are now all-in


def test_cumulative_short_allins_can_reopen_actual_raise_with_live_opponent():
    st = BettingRoundState.create(
        order=(0, 1, 2, 3),
        stacks={0: 1000, 1: 150, 2: 200, 3: 1000},
        min_bet=100,
    )
    st = st.apply(act("RAISE_TO", 100))
    st = st.apply(act("RAISE_TO", 150))
    st = st.apply(act("RAISE_TO", 200))
    st = st.apply(act("CALL"))
    assert st.actor == 0
    legal = st.legal_actions()
    assert legal.to_call == 100
    assert legal.raise_right_open is True
    assert legal.can_raise is True
    assert legal.min_full_raise_to == 300


def test_never_reopen_policy_blocks_prior_actor_after_short_increase():
    st = BettingRoundState.create(
        order=(0, 1, 2),
        stacks={0: 1000, 1: 150, 2: 1000},
        min_bet=100,
        config=BettingConfig(short_all_in_reopen=ShortAllInReopenPolicy.NEVER),
    )
    st = st.apply(act("RAISE_TO", 100))
    st = st.apply(act("RAISE_TO", 150))
    st = st.apply(act("CALL"))
    assert st.actor == 0
    legal = st.legal_actions()
    assert legal.to_call == 50
    assert legal.raise_right_open is False
    assert legal.can_raise is False


def test_dry_side_pot_cannot_be_raised_into_allin_opponents():
    st = BettingRoundState.create(order=(0, 1), stacks={0: 1000, 1: 100}, min_bet=100)
    st = st.apply(act("CHECK"))
    st = st.apply(act("RAISE_TO", 100))
    assert st.actor == 0
    legal = st.legal_actions()
    assert legal.to_call == 100
    assert legal.can_raise is False
    st = st.apply(act("CALL"))
    assert st.complete


def test_raise_is_blocked_when_only_live_opponent_cannot_exceed_current_price():
    # Regression from the independent PokerKit 4-handed randomized oracle.
    # Seat 0 is all-in to 1200, seat 1 folded. Seat 2 still has raise rights and
    # chips, but seat 3 can contribute only 950 total. Because current price is
    # already 1200, no opponent can contest any tranche above 1200; seat 2 may
    # only call/fold rather than create an immediately uncalled side-pot excess.
    st = BettingRoundState.create(
        order=(2, 3, 0, 1),
        stacks={2: 1200, 3: 650, 0: 0, 1: 1300},
        committed={2: 200, 3: 300, 0: 1200, 1: 100},
        min_bet=100,
    )
    # create() cannot encode a historical fold, so reproduce the exact legal
    # geometry directly after folding seat 1 from a live state.
    players = dict(st.players)
    from dataclasses import replace
    players[1] = replace(players[1], folded=True)
    st = BettingRoundState(
        order=st.order,
        players=players,
        min_bet=100,
        current_bet=1200,
        last_full_raise=900,
        pending=frozenset({2, 3}),
        next_index=0,
        config=st.config,
    )
    legal = st.legal_actions()
    assert legal.actor == 2
    assert legal.to_call == 1000
    assert legal.raise_right_open is True
    assert legal.can_raise is False
    assert legal.max_raise_to is None


def test_subminimum_non_allin_raise_is_rejected():
    st = BettingRoundState.create(order=(0, 1), stacks={0: 1000, 1: 1000}, min_bet=100)
    with pytest.raises(ValueError):
        st.apply(act("RAISE_TO", 50))
