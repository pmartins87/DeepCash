"""Bidirectional legal-action boundary parity against pinned PokerKit NLHE.

The full-game oracle proves every chosen DeepCash action is accepted by PokerKit
and final stacks match. That direction alone can miss an under-permissive bug:
DeepCash might silently omit a legal action and therefore never choose it.

This gate compares the *offered action boundary* before every randomized action:
actor, amount to call, check/call availability, fold while facing a bet, raise
availability and (when exposed by the pinned PokerKit API) min/max raise-to.
It reuses the sub-BB forced-noop synchronizer but never relaxes a chip-moving
mismatch.
"""

from __future__ import annotations

import random

import crosscheck_pokerkit_fullgame as x
from crosscheck_pokerkit_fullgame_subbb import sync_with_forced_noops
from deepcash_core.cards import card_to_str, full_deck

SEED = 0x1E6A1A57
CASES_PER_PLAYER_COUNT = 24


def _call_bool(state, name: str) -> bool:
    value = getattr(state, name, None)
    if value is None:
        candidates = sorted(n for n in dir(state) if any(k in n.lower() for k in ("fold", "check", "call", "raise")))
        raise AssertionError(f"pinned PokerKit missing expected legality API {name!r}; candidates={candidates}")
    return bool(value() if callable(value) else value)


def _numeric_attr(state, name: str):
    if not hasattr(state, name):
        return None
    value = getattr(state, name)
    if callable(value):
        try:
            value = value()
        except TypeError:
            return None
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_oracle_noops(oracle, ours, board, dealt: int) -> int:
    return sync_with_forced_noops(oracle, ours, board, dealt)


def assert_legal_parity(ours, oracle, *, context: str) -> None:
    if ours.terminal:
        return
    if ours.betting is None or ours.actor is None:
        raise AssertionError(f"{context}: non-terminal DeepCash state has no actor")

    legal = ours.betting.legal_actions()
    oracle_actor = getattr(oracle, "actor_index", None)
    if oracle_actor is None:
        raise AssertionError(f"{context}: PokerKit has no actor while DeepCash actor={legal.actor}")
    if int(oracle_actor) != int(legal.actor):
        raise AssertionError(
            f"{context}: actor mismatch DeepCash={legal.actor} PokerKit={oracle_actor}; "
            f"dc={x._deepcash_betting_debug(ours)} pk={x._oracle_debug(oracle)}"
        )

    bets = tuple(int(v) for v in oracle.bets)
    stacks = tuple(int(v) for v in oracle.stacks)
    oracle_to_call = max(bets, default=0) - bets[int(oracle_actor)]
    oracle_call_amount = min(oracle_to_call, stacks[int(oracle_actor)])
    if legal.to_call != oracle_to_call or legal.call_amount != oracle_call_amount:
        raise AssertionError(
            f"{context}: call geometry mismatch DeepCash to_call/call={legal.to_call}/{legal.call_amount} "
            f"PokerKit={oracle_to_call}/{oracle_call_amount}; bets={bets} stacks={stacks}"
        )

    pk_check_call = _call_bool(oracle, "can_check_or_call")
    dc_check_call = legal.can_check or legal.can_call
    if pk_check_call != dc_check_call:
        raise AssertionError(
            f"{context}: check/call availability mismatch DeepCash={dc_check_call} PokerKit={pk_check_call}"
        )

    # Folding while facing no bet is strategically dominated/no-op and engines
    # differ on whether they expose it. While facing a positive price, it is a
    # real branch and must agree exactly.
    if legal.to_call > 0:
        pk_fold = _call_bool(oracle, "can_fold")
        if pk_fold != legal.can_fold:
            raise AssertionError(
                f"{context}: fold availability mismatch DeepCash={legal.can_fold} PokerKit={pk_fold}"
            )

    pk_raise = _call_bool(oracle, "can_complete_bet_or_raise_to")
    if pk_raise != legal.can_raise:
        raise AssertionError(
            f"{context}: raise availability mismatch DeepCash={legal.can_raise} PokerKit={pk_raise}; "
            f"dc={x._deepcash_betting_debug(ours)} pk={x._oracle_debug(oracle)}"
        )

    if legal.can_raise:
        # Pinned PokerKit exposes these values as properties. Keep the fallback
        # explicit so an API rename does not masquerade as semantic parity.
        pk_min = _numeric_attr(oracle, "min_completion_betting_or_raising_to_amount")
        pk_max = _numeric_attr(oracle, "max_completion_betting_or_raising_to_amount")
        if pk_min is None or pk_max is None:
            candidates = sorted(n for n in dir(oracle) if "completion" in n.lower() or "raising" in n.lower())
            raise AssertionError(
                f"{context}: pinned PokerKit raise-boundary attributes unavailable; candidates={candidates}"
            )
        if legal.min_full_raise_to != pk_min or legal.max_raise_to != pk_max:
            raise AssertionError(
                f"{context}: raise boundary mismatch DeepCash min/max={legal.min_full_raise_to}/{legal.max_raise_to} "
                f"PokerKit={pk_min}/{pk_max}; dc={x._deepcash_betting_debug(ours)} pk={x._oracle_debug(oracle)}"
            )


def main() -> None:
    rng = random.Random(SEED)
    deck = list(full_deck())
    states_checked = 0
    hands_checked = 0

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
            dealt = _normalize_oracle_noops(oracle, ours, board, 0)
            history: list[str] = []

            actions = 0
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
                        f"{context}: PokerKit rejected chosen parity-checked action {x._action_text(chosen)}"
                    ) from exc
                dealt = _normalize_oracle_noops(oracle, ours, board, dealt)
                actions += 1
                if actions > 300:
                    raise AssertionError(f"{context}: action loop exceeded 300")

            x.check_trace(f"legal_parity_{player_count}p_{case:03d}", ours, oracle)
            hands_checked += 1

    print(
        "PokerKit bidirectional legal-action parity PASS; "
        f"hands={hands_checked} states={states_checked} "
        f"cases_per_player_count={CASES_PER_PLAYER_COUNT} seed={SEED} pin={x.PINNED_POKERKIT}"
    )


if __name__ == "__main__":
    main()
