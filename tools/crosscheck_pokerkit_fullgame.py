"""Independent deterministic full-game traces against pinned PokerKit NLHE.

This is deliberately separate from evaluator parity. It checks blind posting,
action order, raise-to semantics, fold terminals, all-in runout, side pots and
final stack accounting on exact fixtures plus deterministic randomized 2-to-6
handed trace batteries, including sub-BB forced-blind stacks.

Expected dependency:
    pip install git+https://github.com/uoftcprg/pokerkit.git@5841c0afe4d6eb71ae5db0f8a6a376ee3e329afb
"""

from __future__ import annotations

import random

from pokerkit import Automation, NoLimitTexasHoldem

from deepcash_core.betting import StreetAction, StreetActionKind
from deepcash_core.cards import card_from_str, card_to_str, full_deck
from deepcash_core.hand import HandSetup, HandState, Street

PINNED_POKERKIT = "5841c0afe4d6eb71ae5db0f8a6a376ee3e329afb"
SB = 50
BB = 100
RANDOM_SEED = 0xD33FC451
RANDOM_CASES_PER_PLAYER_COUNT = 40


def card(text: str) -> int:
    return card_from_str(text)


def action(kind: str, raise_to: int | None = None) -> StreetAction:
    return StreetAction(StreetActionKind(kind), raise_to)


def button_for_count(player_count: int) -> int:
    # PokerKit indexes the conventional first two blind positions as players
    # 0/1. In its heads-up example player 1 acts first preflop, so player 1 is
    # Button/SB and player 0 is BB. Therefore the final player is the Button for
    # every supported 2..6 handed count.
    if not 2 <= player_count <= 6:
        raise ValueError("player_count must be 2..6")
    return player_count - 1


def setup_ours(stacks, holes, board) -> HandState:
    player_count = len(stacks)
    if len(holes) != player_count:
        raise ValueError("holes/stacks player count mismatch")
    setup = HandSetup(
        occupied_clockwise=tuple(range(player_count)),
        button=button_for_count(player_count),
        stacks={i: int(stacks[i]) for i in range(player_count)},
        small_blind=SB,
        big_blind=BB,
        hole_cards={i: tuple(card(x) for x in holes[i]) for i in range(player_count)},
        board=tuple(card(x) for x in board),
    )
    return HandState.new(setup)


def setup_oracle(stacks, holes):
    player_count = len(stacks)
    if len(holes) != player_count:
        raise ValueError("holes/stacks player count mismatch")
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
        player_count,
    )
    for pair in holes:
        state.deal_hole("".join(pair))
    return state


def deal_street(state, cards):
    state.burn_card("??")
    state.deal_board("".join(cards))


def sync_oracle_board(state, ours: HandState, board, dealt: int) -> int:
    if ours.street == Street.TERMINAL_FOLD:
        return dealt
    target = len(ours.visible_board)
    while dealt < target:
        if dealt == 0:
            deal_street(state, board[:3])
            dealt = 3
        elif dealt == 3:
            deal_street(state, board[3:4])
            dealt = 4
        elif dealt == 4:
            deal_street(state, board[4:5])
            dealt = 5
        else:  # pragma: no cover
            raise AssertionError(f"unsupported board count {dealt}")
    return dealt


def final_ours(state: HandState) -> tuple[int, ...]:
    payouts = state.gross_settlement()
    return tuple(
        int(state.remaining[i]) + int(payouts.get(i, 0))
        for i in range(len(state.plan.occupied))
    )


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


def apply_oracle_action(state, chosen: StreetAction) -> None:
    if chosen.kind == StreetActionKind.FOLD:
        state.fold()
    elif chosen.kind in (StreetActionKind.CHECK, StreetActionKind.CALL):
        state.check_or_call()
    elif chosen.kind == StreetActionKind.RAISE_TO:
        assert chosen.raise_to is not None
        state.complete_bet_or_raise_to(chosen.raise_to)
    else:  # pragma: no cover
        raise AssertionError(chosen.kind)


def choose_random_action(state: HandState, rng: random.Random) -> StreetAction:
    assert state.betting is not None
    legal = state.betting.legal_actions()
    choices: list[StreetAction] = []
    if legal.can_check:
        choices.append(action("CHECK"))
    if legal.can_call:
        choices.append(action("CALL"))
    if legal.can_fold:
        choices.append(action("FOLD"))
    if legal.can_raise:
        assert legal.max_raise_to is not None and legal.min_full_raise_to is not None
        if legal.short_all_in_only:
            choices.append(action("RAISE_TO", legal.max_raise_to))
        else:
            choices.append(action("RAISE_TO", legal.min_full_raise_to))
            if legal.max_raise_to != legal.min_full_raise_to:
                choices.append(action("RAISE_TO", legal.max_raise_to))
    if not choices:
        raise AssertionError("non-terminal DeepCash state has no legal action")
    return rng.choice(choices)


def _action_text(chosen: StreetAction) -> str:
    if chosen.kind == StreetActionKind.RAISE_TO:
        return f"RAISE_TO({chosen.raise_to})"
    return chosen.kind.value


def _deepcash_betting_debug(state: HandState) -> dict:
    if state.betting is None:
        return {"betting": None, "street": state.street.value}
    b = state.betting
    return {
        "street": state.street.value,
        "actor": b.actor,
        "current_bet": b.current_bet,
        "last_full_raise": b.last_full_raise,
        "pending": sorted(b.pending),
        "players": {
            seat: {
                "committed": p.committed,
                "stack": p.stack,
                "folded": p.folded,
                "all_in": p.all_in,
                "last_faced_bet": p.last_faced_bet,
            }
            for seat, p in b.players.items()
        },
    }


def _oracle_debug(state) -> dict:
    return {
        "actor_index": getattr(state, "actor_index", None),
        "stacks": list(getattr(state, "stacks", ())),
        "bets": list(getattr(state, "bets", ())),
        "statuses": list(getattr(state, "statuses", ())),
        "all_in_status": getattr(state, "all_in_status", None),
        "folded_status": getattr(state, "folded_status", None),
        "street_index": getattr(state, "street_index", None),
    }


def trace_three_way_checkdown() -> None:
    stacks = (1000, 1000, 1000)
    holes = (("As", "Ad"), ("Ks", "Kd"), ("Qs", "Qd"))
    board = ("2c", "3c", "4h", "8h", "9s")
    ours = setup_ours(stacks, holes, board)
    oracle = setup_oracle(stacks, holes)

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


def _stack_fixture(player_count: int, case: int, rng: random.Random) -> tuple[int, ...]:
    """Deterministic adversarial forced-blind cases followed by broad random stacks."""
    if player_count == 2:
        fixtures = (
            (60, 1000),   # short BB; Button/SB has only a 10-chip call
            (1000, 20),   # short SB; BB excess is uncalled
            (60, 20),     # both forced blinds all-in/short
            (1000, 70),   # Button/SB can call all-in for less
            (120, 80),    # shallow but both begin with chips after/blind
        )
        if case < len(fixtures):
            return fixtures[case]
    else:
        fixtures: list[tuple[int, ...]] = []
        base = [1000] * player_count
        x = base.copy(); x[1] = 60; fixtures.append(tuple(x))  # short BB
        x = base.copy(); x[0] = 20; fixtures.append(tuple(x))  # short SB
        x = base.copy(); x[0] = 20; x[1] = 60; fixtures.append(tuple(x))
        x = base.copy(); x[-1] = 70; fixtures.append(tuple(x))  # short BTN
        x = base.copy(); x[2] = 80; fixtures.append(tuple(x))  # short early actor
        if case < len(fixtures):
            return fixtures[case]

    # Twenty-chip granularity deliberately samples below and around both blinds,
    # while still reaching 15BB. This keeps rare forced-blind geometries in the
    # independent oracle instead of relying on chance to hit them.
    return tuple(rng.randrange(1, 76) * 20 for _ in range(player_count))


def randomized_trace_battery() -> None:
    rng = random.Random(RANDOM_SEED)
    deck = list(full_deck())
    total_cases = 0
    for player_count in range(2, 7):
        for case in range(RANDOM_CASES_PER_PLAYER_COUNT):
            sample = rng.sample(deck, 2 * player_count + 5)
            holes = tuple(
                tuple(card_to_str(sample[2 * i + j]) for j in range(2))
                for i in range(player_count)
            )
            board = tuple(
                card_to_str(x)
                for x in sample[2 * player_count:2 * player_count + 5]
            )
            stacks = _stack_fixture(player_count, case, rng)

            ours = setup_ours(stacks, holes, board)
            oracle = setup_oracle(stacks, holes)
            dealt = 0
            # Important for forced-blind cases that are automatically terminal
            # before any voluntary action (for example HU with a short SB).
            dealt = sync_oracle_board(oracle, ours, board, dealt)
            action_count = 0
            history: list[str] = []
            while not ours.terminal:
                if action_count >= 300:
                    raise AssertionError(
                        f"random n={player_count} case={case}: action loop exceeded 300"
                    )
                chosen = choose_random_action(ours, rng)
                before = _deepcash_betting_debug(ours)
                ours = ours.apply(chosen)
                history.append(_action_text(chosen))
                try:
                    apply_oracle_action(oracle, chosen)
                except Exception as exc:
                    raise AssertionError(
                        "oracle rejected DeepCash-legal action; "
                        f"players={player_count} case={case} stacks={stacks} "
                        f"holes={holes} board={board} action={_action_text(chosen)} "
                        f"history={history} deepcash_before={before} "
                        f"oracle_before={_oracle_debug(oracle)}"
                    ) from exc
                dealt = sync_oracle_board(oracle, ours, board, dealt)
                action_count += 1

            check_trace(f"random_{player_count}p_{case:03d}", ours, oracle)
            total_cases += 1

    print(
        "PASS randomized 2-to-6 handed trace battery with sub-BB stacks: "
        f"cases={total_cases} ({RANDOM_CASES_PER_PLAYER_COUNT}/player-count) seed={RANDOM_SEED}"
    )


def main() -> None:
    trace_three_way_checkdown()
    trace_raise_then_folds()
    trace_preflop_multiway_sidepot()
    randomized_trace_battery()
    print(f"PokerKit full-game trace cross-check PASS; pin={PINNED_POKERKIT}")


if __name__ == "__main__":
    main()
