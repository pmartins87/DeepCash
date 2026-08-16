import random

import pytest

from deepcash_core.betting import StreetAction, StreetActionKind
from deepcash_core.cards import card_from_str, full_deck
from deepcash_core.hand import HandActionRecord, HandSetup, HandState, Street
from deepcash_core.replay import replay_hand, state_fingerprint


def c(text):
    return card_from_str(text)


def setup_three_way():
    return HandSetup(
        occupied_clockwise=(0, 1, 2),
        button=0,
        stacks={0: 1000, 1: 1000, 2: 1000},
        small_blind=50,
        big_blind=100,
        hole_cards={0: (c("As"), c("Ad")), 1: (c("Ks"), c("Kd")), 2: (c("Qs"), c("Qd"))},
        board=(c("2c"), c("3c"), c("4h"), c("5h"), c("9s")),
    )


def A(kind, raise_to=None):
    return StreetAction(StreetActionKind(kind), raise_to)


def test_full_hand_checkdown_reaches_showdown_and_conserves_chips():
    st = HandState.new(setup_three_way())
    initial = sum(st.setup.stacks.values())
    st = st.apply(A("CALL")); st = st.apply(A("CALL")); st = st.apply(A("CHECK"))
    assert st.street == Street.FLOP
    for _street in range(3):
        st = st.apply(A("CHECK")); st = st.apply(A("CHECK")); st = st.apply(A("CHECK"))
    assert st.street == Street.SHOWDOWN
    payouts = st.gross_settlement()
    assert sum(st.remaining.values()) + sum(payouts.values()) == initial
    assert payouts[0] == 300


def test_fold_terminal_returns_uncalled_raise_excess():
    st = HandState.new(setup_three_way())
    initial = sum(st.setup.stacks.values())
    st = st.apply(A("RAISE_TO", 300))
    st = st.apply(A("FOLD"))
    st = st.apply(A("FOLD"))
    assert st.street == Street.TERMINAL_FOLD
    payouts = st.gross_settlement()
    assert sum(st.remaining.values()) + sum(payouts.values()) == initial
    assert payouts[0] == 450


def test_action_log_preserves_exact_monetary_context():
    st = HandState.new(setup_three_way())
    st = st.apply(A("RAISE_TO", 300))
    first = st.actions[0]
    assert first.paid == 300
    assert first.pot_before == 150
    assert first.to_call_before == 100
    assert first.current_bet_before == 100
    assert first.actor_committed_before == 0
    assert first.min_full_raise_to_before == 200

    st = st.apply(A("CALL"))
    second = st.actions[1]
    assert second.paid == 250
    assert second.pot_before == 450
    assert second.to_call_before == 250
    assert second.actor_committed_before == 50


def test_action_log_replays_to_identical_fingerprint():
    st = HandState.new(setup_three_way())
    st = st.apply(A("CALL")); st = st.apply(A("CALL")); st = st.apply(A("CHECK"))
    st = st.apply(A("RAISE_TO", 100)); st = st.apply(A("FOLD")); st = st.apply(A("CALL"))
    replayed = replay_hand(st.setup, st.actions)
    assert state_fingerprint(replayed) == state_fingerprint(st)


def test_replay_detects_corrupted_action_geometry_even_when_action_label_is_legal():
    st = HandState.new(setup_three_way()).apply(A("CALL"))
    record = st.actions[0]
    corrupt = HandActionRecord(
        street=record.street,
        actor=record.actor,
        action=record.action,
        paid=record.paid + 1,
        pot_before=record.pot_before,
        to_call_before=record.to_call_before,
        current_bet_before=record.current_bet_before,
        actor_committed_before=record.actor_committed_before,
        min_full_raise_to_before=record.min_full_raise_to_before,
    )
    with pytest.raises(ValueError, match="geometry mismatch"):
        replay_hand(st.setup, (corrupt,))


def random_setup(seed: int) -> HandSetup:
    rng = random.Random(seed)
    deck = list(full_deck()); rng.shuffle(deck)
    seats = (0, 1, 2, 3, 4, 5)
    holes = {s: (deck[2*s], deck[2*s+1]) for s in seats}
    board = tuple(deck[12:17])
    return HandSetup(
        occupied_clockwise=seats,
        button=seed % 6,
        stacks={s: 500 + rng.randrange(0, 1501, 50) for s in seats},
        small_blind=25,
        big_blind=50,
        hole_cards=holes,
        board=board,
    )


def choose_random_action(st: HandState, rng: random.Random) -> StreetAction:
    legal = st.betting.legal_actions()  # type: ignore[union-attr]
    choices = []
    if legal.can_check: choices.append(A("CHECK"))
    if legal.can_call: choices.append(A("CALL"))
    if legal.can_fold: choices.append(A("FOLD"))
    if legal.can_raise:
        assert legal.max_raise_to is not None and legal.min_full_raise_to is not None
        if legal.short_all_in_only:
            choices.append(A("RAISE_TO", legal.max_raise_to))
        else:
            choices.append(A("RAISE_TO", min(legal.min_full_raise_to, legal.max_raise_to)))
            if legal.max_raise_to > legal.min_full_raise_to:
                choices.append(A("RAISE_TO", legal.max_raise_to))
    return rng.choice(choices)


def test_random_legal_hands_preserve_chips_and_replay_exactly():
    for seed in range(40):
        setup = random_setup(seed)
        st = HandState.new(setup)
        initial = sum(setup.stacks.values())
        rng = random.Random(seed * 1009 + 7)
        for _ in range(120):
            if st.terminal:
                break
            st = st.apply(choose_random_action(st, rng))
        assert st.terminal, seed
        payouts = st.gross_settlement()
        assert sum(st.remaining.values()) + sum(payouts.values()) == initial, seed
        replayed = replay_hand(setup, st.actions)
        assert state_fingerprint(replayed) == state_fingerprint(st), seed
