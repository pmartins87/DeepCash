"""Bidirectional legal-action parity against pinned PokerKit, API-robust v2.

This catches the omission direction that the full-game mirror cannot: if
PokerKit offers a strategically real action that DeepCash silently omits, the
normal randomized harness would never choose it. v2 compares the live boundary
before every action and probes actual raise-to acceptance rather than assuming
PokerKit's internal min/max property names or their short-all-in conventions.
"""

from __future__ import annotations

import random

import crosscheck_pokerkit_fullgame as x
from crosscheck_pokerkit_fullgame_subbb import sync_with_forced_noops
from deepcash_core.cards import card_to_str, full_deck

SEED = 0x1E6A1A57
CASES_PER_PLAYER_COUNT = 24


def _call_bool_noarg(state, name: str) -> bool:
    value = getattr(state, name, None)
    if value is None:
        candidates = sorted(
            n for n in dir(state)
            if any(k in n.lower() for k in ("fold", "check", "call", "raise"))
        )
        raise AssertionError(
            f"pinned PokerKit missing expected legality API {name!r}; candidates={candidates}"
        )
    return bool(value() if callable(value) else value)


def _pk_can_raise_to(state, target: int) -> bool:
    fn = getattr(state, "can_complete_bet_or_raise_to", None)
    if not callable(fn):
        raise AssertionError("pinned PokerKit lacks can_complete_bet_or_raise_to")
    try:
        return bool(fn(int(target)))
    except (ValueError, TypeError):
        # Some legality helpers reject out-of-domain arguments instead of
        # returning False. For a boundary probe that is semantically equivalent
        # to "not legal"; unexpected engine exceptions still surface elsewhere.
        return False


def _assert_raise_boundary(ours, oracle, *, context: str) -> None:
    legal = ours.betting.legal_actions()
    pk_raise = _call_bool_noarg(oracle, "can_complete_bet_or_raise_to")
    if pk_raise != legal.can_raise:
        raise AssertionError(
            f"{context}: raise availability mismatch DeepCash={legal.can_raise} PokerKit={pk_raise}; "
            f"dc={x._deepcash_betting_debug(ours)} pk={x._oracle_debug(oracle)}"
        )
    if not legal.can_raise:
        return

    assert legal.max_raise_to is not None and legal.min_full_raise_to is not None
    lower = legal.max_raise_to if legal.short_all_in_only else legal.min_full_raise_to
    upper = legal.max_raise_to
    if lower > upper:
        raise AssertionError(f"{context}: DeepCash legal raise interval inverted: {lower}>{upper}")

    if not _pk_can_raise_to(oracle, lower):
        raise AssertionError(
            f"{context}: PokerKit rejects DeepCash minimum legal raise target {lower}; "
            f"dc={x._deepcash_betting_debug(ours)} pk={x._oracle_debug(oracle)}"
        )
    if not _pk_can_raise_to(oracle, upper):
        raise AssertionError(
            f"{context}: PokerKit rejects DeepCash maximum legal raise target {upper}"
        )

    # A no-limit full-raise interval is contiguous. For a short-all-in-only
    # branch, `lower == upper` and the immediately smaller target must be
    # illegal. This one-step lower-bound probe therefore detects an
    # under-permissive DeepCash minimum without enumerating every chip value.
    current_bet = ours.betting.current_bet
    below = lower - 1
    if below > current_bet and _pk_can_raise_to(oracle, below):
        raise AssertionError(
            f"{context}: PokerKit accepts raise target {below} below DeepCash lower boundary {lower}; "
            f"DeepCash may be omitting legal raises"
        )

    # DeepCash max is actor's all-in contribution. PokerKit must not accept one
    # chip above it.
    if _pk_can_raise_to(oracle, upper + 1):
        raise AssertionError(
            f"{context}: PokerKit accepts target {upper + 1} above DeepCash actor max {upper}"
        )


def assert_legal_parity(ours, oracle, *, context: str) -> None:
    if ours.terminal:
        return
    if ours.betting is None or ours.actor is None:
        raise AssertionError(f"{context}: non-terminal DeepCash state has no actor")

    legal = ours.betting.legal_actions()
    oracle_actor = getattr(oracle, "actor_index", None)
    if oracle_actor is None or int(oracle_actor) != int(legal.actor):
        raise AssertionError(
            f"{context}: actor mismatch DeepCash={legal.actor} PokerKit={oracle_actor}; "
            f"dc={x._deepcash_betting_debug(ours)} pk={x._oracle_debug(oracle)}"
        )

    bets = tuple(int(v) for v in oracle.bets)
    stacks = tuple(int(v) for v in oracle.stacks)
    actor = int(oracle_actor)
    pk_to_call = max(bets, default=0) - bets[actor]
    pk_call_amount = min(pk_to_call, stacks[actor])
    if (legal.to_call, legal.call_amount) != (pk_to_call, pk_call_amount):
        raise AssertionError(
            f"{context}: call geometry mismatch DeepCash={legal.to_call}/{legal.call_amount} "
            f"PokerKit={pk_to_call}/{pk_call_amount}; bets={bets} stacks={stacks}"
        )

    pk_check_call = _call_bool_noarg(oracle, "can_check_or_call")
    dc_check_call = legal.can_check or legal.can_call
    if pk_check_call != dc_check_call:
        raise AssertionError(
            f"{context}: check/call availability mismatch DeepCash={dc_check_call} PokerKit={pk_check_call}"
        )

    # Engines may differ on exposing a dominated fold when checking is free.
    # When chips are actually faced, fold is a real strategic branch and must
    # agree exactly.
    if legal.to_call > 0:
        pk_fold = _call_bool_noarg(oracle, "can_fold")
        if pk_fold != legal.can_fold:
            raise AssertionError(
                f"{context}: fold availability mismatch DeepCash={legal.can_fold} PokerKit={pk_fold}"
            )

    _assert_raise_boundary(ours, oracle, context=context)


def main() -> None:
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
                assert_legal_parity(ours, oracle, context=context)
                states_checked += 1

                chosen = x.choose_random_action(ours, rng)
                ours = ours.apply(chosen)
                history.append(x._action_text(chosen))
                try:
                    x.apply_oracle_action(oracle, chosen)
                except Exception as exc:
                    raise AssertionError(
                        f"{context}: PokerKit rejected parity-checked action {x._action_text(chosen)}"
                    ) from exc
                dealt = sync_with_forced_noops(oracle, ours, board, dealt)
                action_count += 1
                if action_count > 300:
                    raise AssertionError(f"{context}: action loop exceeded 300")

            x.check_trace(f"legal_parity_v2_{player_count}p_{case:03d}", ours, oracle)
            hands_checked += 1

    print(
        "PokerKit bidirectional legal-action parity v2 PASS; "
        f"hands={hands_checked} states={states_checked} "
        f"cases_per_player_count={CASES_PER_PLAYER_COUNT} seed={SEED} pin={x.PINNED_POKERKIT}"
    )


if __name__ == "__main__":
    main()
