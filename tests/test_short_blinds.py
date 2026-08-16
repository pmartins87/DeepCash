import pytest

from deepcash_core.betting import StreetAction, StreetActionKind
from deepcash_core.cards import card_from_str
from deepcash_core.hand import HandSetup, HandState, Street


def c(text: str) -> int:
    return card_from_str(text)


def A(kind: str, raise_to: int | None = None) -> StreetAction:
    return StreetAction(StreetActionKind(kind), raise_to)


def setup3(stacks) -> HandSetup:
    # Three-handed physical mapping used by the independent PokerKit gate:
    # player 0=SB, player 1=BB, player 2=BTN.
    return HandSetup(
        occupied_clockwise=(0, 1, 2),
        button=2,
        stacks={i: int(stacks[i]) for i in range(3)},
        small_blind=50,
        big_blind=100,
        hole_cards={
            0: (c("As"), c("Ad")),
            1: (c("Ks"), c("Kd")),
            2: (c("Qs"), c("Qd")),
        },
        board=(c("2c"), c("3h"), c("6c"), c("8h"), c("9s")),
    )


def setup_hu(stacks) -> HandSetup:
    # Heads-up: button=1 is Button/SB; seat 0 is BB.
    return HandSetup(
        occupied_clockwise=(0, 1),
        button=1,
        stacks={0: int(stacks[0]), 1: int(stacks[1])},
        small_blind=50,
        big_blind=100,
        hole_cards={0: (c("As"), c("Ad")), 1: (c("Ks"), c("Kd"))},
        board=(c("2c"), c("3h"), c("6c"), c("8h"), c("9s")),
    )


def test_short_big_blind_posts_actual_stack_but_nominal_bb_remains_full_raise_increment():
    state = HandState.new(setup3((1000, 60, 1000)))
    assert state.street == Street.PREFLOP
    assert state.remaining == {0: 950, 1: 0, 2: 1000}
    assert state.total_contributed == {0: 50, 1: 60, 2: 0}
    assert state.actor == 2
    assert state.betting is not None
    assert state.betting.current_bet == 60
    assert state.betting.last_full_raise == 100
    legal = state.betting.legal_actions()
    assert legal.to_call == 60
    assert legal.min_full_raise_to == 160


def test_short_small_blind_is_allin_and_does_not_change_full_big_blind_price():
    state = HandState.new(setup3((20, 1000, 1000)))
    assert state.remaining == {0: 0, 1: 900, 2: 1000}
    assert state.total_contributed == {0: 20, 1: 100, 2: 0}
    assert state.actor == 2
    assert state.betting is not None
    legal = state.betting.legal_actions()
    assert legal.to_call == 100
    assert legal.min_full_raise_to == 200


def test_both_blinds_short_allow_only_actual_price_and_run_out_after_lone_live_player_calls():
    state = HandState.new(setup3((20, 60, 1000)))
    assert state.actor == 2
    assert state.betting is not None
    legal = state.betting.legal_actions()
    assert legal.to_call == 60
    assert legal.can_raise is False
    state = state.apply(A("CALL"))
    assert state.street == Street.SHOWDOWN
    assert state.remaining == {0: 0, 1: 0, 2: 940}
    assert state.total_contributed == {0: 20, 1: 60, 2: 60}
    assert state.chip_conservation_total() == 1080


def test_short_button_calls_allin_for_less_than_full_big_blind():
    state = HandState.new(setup3((1000, 1000, 70)))
    assert state.actor == 2
    assert state.betting is not None
    assert state.betting.legal_actions().call_amount == 70
    state = state.apply(A("CALL"))
    assert state.remaining[2] == 0
    assert state.total_contributed[2] == 70
    assert state.actor == 0


def test_heads_up_short_big_blind_leaves_only_ten_chip_call_and_no_dry_raise():
    state = HandState.new(setup_hu((60, 1000)))
    assert state.actor == 1
    assert state.betting is not None
    legal = state.betting.legal_actions()
    assert legal.to_call == 10
    assert legal.call_amount == 10
    assert legal.can_raise is False
    state = state.apply(A("CALL"))
    assert state.street == Street.SHOWDOWN
    assert state.remaining == {0: 0, 1: 940}
    assert state.total_contributed == {0: 60, 1: 60}


def test_heads_up_short_small_blind_auto_runs_out_and_uncalled_bb_excess_is_returned_at_settlement():
    state = HandState.new(setup_hu((1000, 20)))
    assert state.street == Street.SHOWDOWN
    # DeepCash keeps the unmatched 80 in contribution accounting until terminal
    # settlement rather than mutating the stack during automatic progression.
    assert state.remaining == {0: 900, 1: 0}
    assert state.total_contributed == {0: 100, 1: 20}
    assert state.gross_settlement() == {0: 120}
    final = {
        seat: state.remaining[seat] + state.gross_settlement().get(seat, 0)
        for seat in (0, 1)
    }
    assert final == {0: 1020, 1: 0}


def test_zero_stack_cannot_be_dealt_into_new_hand():
    with pytest.raises(ValueError, match="positive"):
        setup3((1000, 0, 1000))
