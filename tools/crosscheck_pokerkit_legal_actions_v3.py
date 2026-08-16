"""Bidirectional legal-action oracle v3 with an explicit PokerKit divergence overlay.

v2 deliberately failed on a preflop blind-epoch corner case: after players had
called a live 100 BB, the first voluntary raise was an all-in to only 180.
DeepCash correctly kept the raise right closed for prior callers (+80 < the
full +100 raise required), while pinned PokerKit offered a reraise.

PokerKit's pinned implementation initializes its internal
`completion_betting_or_raising_amount` to zero at betting-round start. When the
first voluntary raise is a sub-BB short all-in, that 80 increment becomes both
the tracked completion/raise amount and the sole consecutive-all-in amount, so
PokerKit does not classify it as non-full for reopening. DeepCash intentionally
does not copy that behavior.

This v3 gate preserves all v2 bidirectional probes and accepts ONLY that
structurally identified blind-epoch discrepancy. Everything else remains a hard
failure. The generic DeepCash contract follows cumulative-full-raise semantics;
target-site confirmation remains a separate R1 release gate.
"""

from __future__ import annotations

import random

import crosscheck_pokerkit_fullgame as x
import crosscheck_pokerkit_legal_actions_v2 as v2
from crosscheck_pokerkit_fullgame_subbb import sync_with_forced_noops
from deepcash_core.cards import card_to_str, full_deck
from deepcash_core.hand import Street

SEED = v2.SEED
CASES_PER_PLAYER_COUNT = v2.CASES_PER_PLAYER_COUNT
_V2_ASSERT_RAISE_BOUNDARY = v2._assert_raise_boundary

_expected_blind_epoch_divergences = 0


def _documented_pokerkit_blind_epoch_divergence(ours, oracle) -> bool:
    """Recognize only the pinned PokerKit first-short-raise blind-epoch case."""
    if ours.street != Street.PREFLOP or ours.betting is None:
        return False
    legal = ours.betting.legal_actions()
    if legal.can_raise or legal.raise_right_open:
        return False
    if not v2._call_bool_noarg(oracle, "can_complete_bet_or_raise_to"):
        return False

    actor = legal.actor
    player = ours.betting.players[actor]
    if player.last_faced_bet is None:
        return False
    faced_increase = ours.betting.current_bet - player.last_faced_bet
    if not (0 < faced_increase < ours.betting.last_full_raise):
        return False

    # The observed upstream divergence occurs before a full minimum raise above
    # the live BB has ever materialized: a first short all-in sits between one
    # BB and two BB. This prevents the overlay from masking later-street or
    # genuinely cumulative-short-raise bugs.
    if player.last_faced_bet != ours.betting.min_bet:
        return False
    if not (
        ours.betting.min_bet
        < ours.betting.current_bet
        < 2 * ours.betting.min_bet
    ):
        return False

    consecutive = tuple(
        int(v)
        for v in getattr(
            oracle,
            "consecutive_all_in_completion_betting_or_raising_amounts",
            (),
        )
    )
    pk_completion = int(
        getattr(oracle, "completion_betting_or_raising_amount", -1)
    )
    acted = set(int(v) for v in getattr(oracle, "acted_player_indices", ()))
    oracle_actor = getattr(oracle, "actor_index", None)
    if oracle_actor is None or int(oracle_actor) != actor:
        return False

    # Pin the exact upstream mechanism, not just its surface symptom. The first
    # short all-in becomes PokerKit's own completion baseline, and the prior
    # caller has been removed from its acted set even though DeepCash remembers
    # the 100 price that player already faced.
    if not consecutive:
        return False
    if sum(consecutive) != pk_completion:
        return False
    if not (0 < pk_completion < ours.betting.last_full_raise):
        return False
    if actor in acted:
        return False
    return True


def _assert_raise_boundary_v3(ours, oracle, *, context: str) -> None:
    global _expected_blind_epoch_divergences
    legal = ours.betting.legal_actions()
    pk_raise = v2._call_bool_noarg(oracle, "can_complete_bet_or_raise_to")
    if pk_raise != legal.can_raise:
        if _documented_pokerkit_blind_epoch_divergence(ours, oracle):
            _expected_blind_epoch_divergences += 1
            print(
                "EXPECTED_POKERKIT_BLIND_EPOCH_DIVERGENCE "
                f"{context}; DeepCash_can_raise={legal.can_raise} "
                f"PokerKit_can_raise={pk_raise}; dc={x._deepcash_betting_debug(ours)} "
                f"pk={x._oracle_debug(oracle)}"
            )
            return
        raise AssertionError(
            f"{context}: raise availability mismatch DeepCash={legal.can_raise} "
            f"PokerKit={pk_raise}; dc={x._deepcash_betting_debug(ours)} "
            f"pk={x._oracle_debug(oracle)}"
        )

    # Reuse every lower/upper-bound and one-chip probe from the immutable v2
    # helper when availability agrees. Only the structurally recognized mismatch
    # above is exempted.
    _V2_ASSERT_RAISE_BOUNDARY(ours, oracle, context=context)


def main() -> None:
    # v2.assert_legal_parity resolves its module-global raise helper at call time,
    # so replace only that hook for the duration of this deterministic run.
    original = v2._assert_raise_boundary
    v2._assert_raise_boundary = _assert_raise_boundary_v3
    try:
        rng = random.Random(SEED)
        deck = list(full_deck())
        hands_checked = 0
        states_checked = 0

        for player_count in range(2, 7):
            for case in range(CASES_PER_PLAYER_COUNT):
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
                ours = x.setup_ours(stacks, holes, board)
                oracle = x.setup_oracle(stacks, holes)
                dealt = sync_with_forced_noops(oracle, ours, board, 0)
                history: list[str] = []
                action_count = 0

                while not ours.terminal:
                    context = (
                        f"players={player_count} case={case} stacks={stacks} "
                        f"history={history} street={ours.street.value}"
                    )
                    v2.assert_legal_parity(ours, oracle, context=context)
                    states_checked += 1

                    chosen = x.choose_random_action(ours, rng)
                    ours = ours.apply(chosen)
                    history.append(x._action_text(chosen))
                    try:
                        x.apply_oracle_action(oracle, chosen)
                    except Exception as exc:
                        raise AssertionError(
                            f"{context}: PokerKit rejected parity-checked action "
                            f"{x._action_text(chosen)}"
                        ) from exc
                    dealt = sync_with_forced_noops(oracle, ours, board, dealt)
                    action_count += 1
                    if action_count > 300:
                        raise AssertionError(f"{context}: action loop exceeded 300")

                x.check_trace(
                    f"legal_parity_v3_{player_count}p_{case:03d}", ours, oracle
                )
                hands_checked += 1

        if _expected_blind_epoch_divergences <= 0:
            raise AssertionError(
                "v3 overlay was not exercised; deterministic fixture path changed"
            )
        print(
            "PokerKit/TDA bidirectional legal-action oracle v3 PASS; "
            f"hands={hands_checked} states={states_checked} "
            f"expected_blind_epoch_divergences={_expected_blind_epoch_divergences} "
            f"cases_per_player_count={CASES_PER_PLAYER_COUNT} seed={SEED} "
            f"pin={x.PINNED_POKERKIT}"
        )
    finally:
        v2._assert_raise_boundary = original


if __name__ == "__main__":
    main()
