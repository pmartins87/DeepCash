"""Expanded 2-to-6 PokerKit full-game oracle with forced-noop sync.

DeepCash automatically runs the board when only one live player still has chips,
because no strategically meaningful betting decision remains. Pinned PokerKit
may still expose a mechanical zero-chip CHECK for that lone stacked player
before it enters card-burning/dealing. This wrapper consumes only those proven
zero-chip no-op checks when DeepCash has already advanced, then delegates every
real action and every final-stack comparison to the original oracle harness.

It intentionally fails closed if PokerKit's pending operation would move chips.
"""

from __future__ import annotations

import crosscheck_pokerkit_fullgame as x

_original_sync = x.sync_oracle_board


def _oracle_to_call(state, actor: int) -> int:
    bets = tuple(int(v) for v in state.bets)
    return max(bets, default=0) - bets[actor]


def sync_with_forced_noops(state, ours, board, dealt: int) -> int:
    target = len(ours.visible_board)
    forced_checks = 0

    # Only normalize when DeepCash has already advanced beyond the amount of
    # board PokerKit has dealt. A pending PokerKit actor at that point can be a
    # harmless bookkeeping CHECK after every opponent is all-in/folded.
    while target > dealt:
        actor = getattr(state, "actor_index", None)
        if actor is None:
            break
        to_call = _oracle_to_call(state, int(actor))
        if to_call != 0:
            raise AssertionError(
                "DeepCash advanced while PokerKit still requires a chip-moving action: "
                f"actor={actor} to_call={to_call} bets={tuple(state.bets)} "
                f"stacks={tuple(state.stacks)} deepcash_street={ours.street.value}"
            )
        op = state.check_or_call()
        amount = int(getattr(op, "amount", 0))
        if amount != 0:
            raise AssertionError(
                f"forced sync check unexpectedly moved chips: actor={actor} amount={amount}"
            )
        forced_checks += 1
        if forced_checks > len(getattr(state, "stacks", ())):
            raise AssertionError("forced no-op sync loop exceeded player count")

    return _original_sync(state, ours, board, dealt)


def main() -> None:
    x.sync_oracle_board = sync_with_forced_noops
    x.main()


if __name__ == "__main__":
    main()
