"""Independent deterministic full-game traces against pinned PokerKit NLHE.

This is deliberately separate from evaluator parity. It checks blind posting,
action order, raise-to semantics, fold terminals, all-in runout, side pots and
final stack accounting on a small set of exact traces.

Expected dependency:
    pip install git+https://github.com/uoftcprg/pokerkit.git@5841c0afe4d6eb71ae5db0f8a6a376ee3e329afb
"""

from __future__ import annotations

from pokerkit import Automation, NoLimitTexasHoldem

from deepcash_core.betting import StreetAction, StreetActionKind
from deepcash_core.cards import card_from_str
from deepcash_core.hand import HandSetup, HandState

PINNED_POKERKIT = "5841c0afe4d6eb71ae5db0f8a6a376ee3e329afb"
SB = 50
BB = 100


def card(text: str) -> int:
    return card_from_str(text)


def action(kind: str, raise_to: int | None = None) -> StreetAction:
    return StreetAction(StreetActionKind(kind), raise_to)


def setup_ours(stacks, holes, board) -> HandState:
    # PokerKit's 3-player positional convention maps player 2 to BTN,
    # player 0 to SB and player 1 to BB. Use the same physical mapping here.
    setup = HandSetup(
        occupied_clockwise=(0, 1, 2),
        button=2,
        stacks={i: int(stacks[i]) for i in range(3)},
        small_blind=SB,
        big_blind=BB,
        hole_cards={i: tuple(card(x) for x in holes[i]) for i in range(3)},
        board=tuple(card(x) for x in board),
    )
    return HandState.new(setup)


def setup_oracle(stacks, holes):
    state = NoLimitTexasHoldem.create_state(
        (
            Automation.ANTE_POSTING,
            Automation.BET_COLLECTION,
            Automation.BLIND_OR_STRADDLE_POSTING,
            Automation.RUNOUT_COUNT_SELECTION,
            Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
            Automation.HAND_KILLING,
            Automation.CHIPS_PUSHING,
            Automation.CHIPS_PULLING,
        ),
        True,
        0,
        (SB, BB),
        BB,
        tuple(stacks),
        3,
    )
    for pair in holes:
        state.deal_hole("".join(pair))
    return state


def deal_street(state, cards):
    state.burn_card("??")
    state.deal_board("".join(cards))


def final_ours(state: HandState) -> tuple[int, ...]:
    payouts = state.gross_settlement()
    return tuple(int(state.remaining[i]) + int(payouts.get(i, 0)) for i in range(3))


def final_oracle(state) -> tuple[int, ...]:
    return tuple(int(x) for x in state.stacks)


def check_trace(name: str, ours: HandState, oracle) -> None:
    a = final_ours(ours)
    b = final_oracle(oracle)
    if a != b:
        raise AssertionError(f"{name}: final stacks differ: DeepCash={a}, PokerKit={b}")
    if sum(a) != sum(b):
        raise AssertionError(f"{name}: chip total mismatch")
    print(f"PASS {name}: final_stacks={a}")


def trace_three_way_checkdown() -> None:
    stacks = (1000, 1000, 1000)
    holes = (("As", "Ad"), ("Ks", "Kd"), ("Qs", "Qd"))
    board = ("2c", "3c", "4h", "8h", "9s")
    ours = setup_ours(stacks, holes, board)
    oracle = setup_oracle(stacks, holes)

    # BTN call, SB call, BB check.
    for _ in range(2):
        ours = ours.apply(action("CALL"))
        oracle.check_or_call()
    ours = ours.apply(action("CHECK"))
    oracle.check_or_call()

    deal_street(oracle, board[:3])
    for _ in range(3):
        ours = ours.apply(action("CHECK"))
        oracle.check_or_call()

    deal_street(oracle, board[3:4])
    for _ in range(3):
        ours = ours.apply(action("CHECK"))
        oracle.check_or_call()

    deal_street(oracle, board[4:5])
    for _ in range(3):
        ours = ours.apply(action("CHECK"))
        oracle.check_or_call()

    check_trace("three_way_checkdown", ours, oracle)


def trace_raise_then_folds() -> None:
    stacks = (1000, 1000, 1000)
    holes = (("Ks", "Kd"), ("Qs", "Qd"), ("As", "Ad"))
    board = ("2c", "3c", "4h", "8h", "9s")
    ours = setup_ours(stacks, holes, board)
    oracle = setup_oracle(stacks, holes)

    ours = ours.apply(action("RAISE_TO", 300))
    oracle.complete_bet_or_raise_to(300)
    ours = ours.apply(action("FOLD"))
    oracle.fold()
    ours = ours.apply(action("FOLD"))
    oracle.fold()

    check_trace("raise_then_folds_uncalled_return", ours, oracle)


def trace_preflop_multiway_sidepot() -> None:
    # Player 2/BTN is short and wins only the main pot with AA. Player 0/SB
    # wins the side pot with KK over player 1/BB's QQ.
    stacks = (600, 1000, 300)
    holes = (("Ks", "Kd"), ("Qs", "Qd"), ("As", "Ad"))
    board = ("2c", "3c", "4h", "8h", "9s")
    ours = setup_ours(stacks, holes, board)
    oracle = setup_oracle(stacks, holes)

    ours = ours.apply(action("RAISE_TO", 300))
    oracle.complete_bet_or_raise_to(300)
    ours = ours.apply(action("RAISE_TO", 600))
    oracle.complete_bet_or_raise_to(600)
    ours = ours.apply(action("CALL"))
    oracle.check_or_call()

    deal_street(oracle, board[:3])
    deal_street(oracle, board[3:4])
    deal_street(oracle, board[4:5])

    check_trace("preflop_multiway_sidepot", ours, oracle)


def main() -> None:
    trace_three_way_checkdown()
    trace_raise_then_folds()
    trace_preflop_multiway_sidepot()
    print(f"PokerKit full-game trace cross-check PASS; pin={PINNED_POKERKIT}")


if __name__ == "__main__":
    main()
