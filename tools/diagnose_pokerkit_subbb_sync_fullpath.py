"""Replay the exact full randomized RNG path and enrich board-sync failures."""

from __future__ import annotations

import crosscheck_pokerkit_fullgame as x
from deepcash_core.cards import card_to_str

_original_sync = x.sync_oracle_board


def diagnostic_sync(oracle, ours, board, dealt):
    try:
        return _original_sync(oracle, ours, board, dealt)
    except Exception as exc:
        action_history = [
            {
                "street": r.street.value,
                "actor": r.actor,
                "kind": r.action.kind.value,
                "raise_to": r.action.raise_to,
                "paid": r.paid,
                "pot_before": r.pot_before,
                "to_call_before": r.to_call_before,
                "current_bet_before": r.current_bet_before,
            }
            for r in ours.actions
        ]
        holes = {
            seat: tuple(card_to_str(c) for c in cards)
            for seat, cards in ours.setup.hole_cards.items()
        }
        setup_board = tuple(card_to_str(c) for c in ours.setup.board)
        print("ENRICHED_BOARD_SYNC_FAILURE")
        print(f"exception={type(exc).__name__}: {exc}")
        print(f"stacks={dict(ours.setup.stacks)}")
        print(f"holes={holes}")
        print(f"board={setup_board}")
        print(f"actions={action_history}")
        print(f"deepcash_street={ours.street.value} visible={len(ours.visible_board)} dealt={dealt}")
        print(f"deepcash={x._deepcash_betting_debug(ours)}")
        print(f"oracle={x._oracle_debug(oracle)}")
        raise


def main() -> None:
    x.sync_oracle_board = diagnostic_sync
    x.randomized_trace_battery()


if __name__ == "__main__":
    main()
