"""Focused diagnostic for the first sub-BB board-sync oracle failure.

Replays the exact deterministic RNG path used by crosscheck_pokerkit_fullgame
through 3-handed case 004, then prints both engines around every action/street
transition. This file is temporary engineering evidence; it deliberately does
not change either engine or relax the oracle.
"""

from __future__ import annotations

import random

import crosscheck_pokerkit_fullgame as x
from deepcash_core.cards import card_to_str, full_deck

TARGET_PLAYERS = 3
TARGET_CASE = 4


def materialize_target():
    rng = random.Random(x.RANDOM_SEED)
    deck = list(full_deck())
    for player_count in range(2, TARGET_PLAYERS + 1):
        for case in range(x.RANDOM_CASES_PER_PLAYER_COUNT):
            sample = rng.sample(deck, 2 * player_count + 5)
            holes = tuple(
                tuple(card_to_str(sample[2 * i + j]) for j in range(2))
                for i in range(player_count)
            )
            board = tuple(
                card_to_str(v)
                for v in sample[2 * player_count:2 * player_count + 5]
            )
            stacks = x._stack_fixture(player_count, case, rng)
            if player_count == TARGET_PLAYERS and case == TARGET_CASE:
                return rng, stacks, holes, board
    raise AssertionError("target deterministic case not reached")


def main() -> None:
    rng, stacks, holes, board = materialize_target()
    ours = x.setup_ours(stacks, holes, board)
    oracle = x.setup_oracle(stacks, holes)
    dealt = 0
    history: list[str] = []

    print(f"TARGET players={TARGET_PLAYERS} case={TARGET_CASE}")
    print(f"stacks={stacks}")
    print(f"holes={holes}")
    print(f"board={board}")
    print(f"deepcash_initial={x._deepcash_betting_debug(ours)}")
    print(f"oracle_initial={x._oracle_debug(oracle)}")

    try:
        dealt = x.sync_oracle_board(oracle, ours, board, dealt)
    except Exception as exc:
        print(
            "INITIAL_SYNC_FAILURE "
            f"type={type(exc).__name__} msg={exc} dealt={dealt} "
            f"visible={len(ours.visible_board)} deepcash={x._deepcash_betting_debug(ours)} "
            f"oracle={x._oracle_debug(oracle)}"
        )
        raise

    action_count = 0
    while not ours.terminal:
        chosen = x.choose_random_action(ours, rng)
        before_dc = x._deepcash_betting_debug(ours)
        before_oracle = x._oracle_debug(oracle)
        print(
            f"ACTION {action_count} chosen={x._action_text(chosen)} "
            f"deepcash_before={before_dc} oracle_before={before_oracle}"
        )
        ours = ours.apply(chosen)
        history.append(x._action_text(chosen))
        x.apply_oracle_action(oracle, chosen)
        print(
            f"AFTER_ACTION {action_count} history={history} "
            f"deepcash={x._deepcash_betting_debug(ours)} oracle={x._oracle_debug(oracle)}"
        )
        try:
            dealt = x.sync_oracle_board(oracle, ours, board, dealt)
        except Exception as exc:
            print(
                "SYNC_FAILURE "
                f"type={type(exc).__name__} msg={exc} dealt={dealt} "
                f"visible={len(ours.visible_board)} history={history} "
                f"deepcash={x._deepcash_betting_debug(ours)} "
                f"oracle={x._oracle_debug(oracle)}"
            )
            raise
        action_count += 1

    print(f"TERMINAL history={history} dealt={dealt}")
    print(f"deepcash_final={x.final_ours(ours)}")
    print(f"oracle_final={x.final_oracle(oracle)}")


if __name__ == "__main__":
    main()
