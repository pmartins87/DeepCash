from deepcash_core.betting import StreetAction, StreetActionKind
from deepcash_core.cards import card_from_str
from deepcash_core.hand import HandSetup, HandState, Street


def c(text: str) -> int:
    return card_from_str(text)


def action(kind: str, raise_to: int | None = None) -> StreetAction:
    return StreetAction(StreetActionKind(kind), raise_to)


def three_way_setup() -> HandSetup:
    # BTN=0, SB=1, BB=2. Stack sizes deliberately create one main pot and
    # one side pot after the preflop all-ins.
    return HandSetup(
        occupied_clockwise=(0, 1, 2),
        button=0,
        stacks={0: 300, 1: 600, 2: 1000},
        small_blind=50,
        big_blind=100,
        hole_cards={
            0: (c("As"), c("Ad")),
            1: (c("Ks"), c("Kd")),
            2: (c("Qs"), c("Qd")),
        },
        board=(c("2c"), c("3c"), c("4h"), c("8h"), c("9s")),
    )


def test_preflop_multiway_allins_build_main_and_side_pot_and_conserve_chips():
    setup = three_way_setup()
    state = HandState.new(setup)
    initial = sum(setup.stacks.values())

    state = state.apply(action("RAISE_TO", 300))  # BTN all-in
    state = state.apply(action("RAISE_TO", 600))  # SB all-in, full raise
    state = state.apply(action("CALL"))            # BB calls 600 total

    assert state.street == Street.SHOWDOWN
    assert state.total_contributed == {0: 300, 1: 600, 2: 600}
    assert state.remaining == {0: 0, 1: 0, 2: 400}

    payouts = state.gross_settlement()
    # AA wins the 900 main pot; KK beats QQ for the 600 side pot.
    assert payouts == {0: 900, 1: 600}
    assert sum(state.remaining.values()) + sum(payouts.values()) == initial


def test_short_stack_main_pot_winner_does_not_receive_side_pot():
    state = HandState.new(three_way_setup())
    state = state.apply(action("RAISE_TO", 300))
    state = state.apply(action("RAISE_TO", 600))
    state = state.apply(action("CALL"))
    payouts = state.gross_settlement()

    assert payouts[0] == 900
    assert payouts[1] == 600
    assert 2 not in payouts
