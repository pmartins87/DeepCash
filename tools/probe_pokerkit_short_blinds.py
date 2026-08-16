"""Independent PokerKit probe for short-stack forced-blind semantics.

This is a research fixture, not a DeepCash rule implementation. It records how
the pinned conventional NLHE oracle treats stacks that cannot cover their
nominal blind or the full preflop bring-in. R1 will use this evidence before
changing HandSetup/BettingRoundState rather than guessing the semantics.

Expected dependency:
    pip install git+https://github.com/uoftcprg/pokerkit.git@5841c0afe4d6eb71ae5db0f8a6a376ee3e329afb
"""

from __future__ import annotations

from pokerkit import Automation, NoLimitTexasHoldem

PINNED_POKERKIT = "5841c0afe4d6eb71ae5db0f8a6a376ee3e329afb"
SB = 50
BB = 100


def make_state(stacks: tuple[int, ...]):
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
        stacks,
        len(stacks),
    )
    cards = ("AsAd", "KsKd", "QsQd", "JsJd", "TsTd", "9s9d")
    for i in range(len(stacks)):
        state.deal_hole(cards[i])
    return state


def snapshot(state) -> dict:
    names = (
        "actor_index",
        "street_index",
        "all_in_status",
        "folded_status",
        "completion_betting_or_raising_amount",
        "bring_in",
    )
    out = {
        "stacks": tuple(int(x) for x in state.stacks),
        "bets": tuple(int(x) for x in state.bets),
        "statuses": tuple(bool(x) for x in state.statuses),
    }
    for name in names:
        if hasattr(state, name):
            value = getattr(state, name)
            try:
                out[name] = int(value) if value is not None else None
            except (TypeError, ValueError):
                out[name] = value
    return out


def run_calls(state, limit: int = 4):
    ops = []
    for _ in range(limit):
        actor = getattr(state, "actor_index", None)
        if actor is None:
            break
        try:
            op = state.check_or_call()
        except Exception as exc:
            ops.append({"stopped": type(exc).__name__, "message": str(exc)})
            break
        ops.append(
            {
                "actor": getattr(op, "player_index", actor),
                "amount": int(getattr(op, "amount", 0)),
                "after": snapshot(state),
            }
        )
    return ops


def probe(name: str, stacks: tuple[int, ...]) -> None:
    state = make_state(stacks)
    print(f"CASE {name}")
    print(f"  starting={stacks}")
    print(f"  after_blinds={snapshot(state)}")
    for idx, op in enumerate(run_calls(state)):
        print(f"  call_{idx + 1}={op}")
    print()


def probe_raise_boundaries(
    name: str,
    stacks: tuple[int, ...],
    targets: tuple[int, ...],
) -> None:
    """Try candidate first-action raise-to targets on fresh identical states."""
    print(f"RAISE_BOUNDARIES {name} starting={stacks}")
    for target in targets:
        state = make_state(stacks)
        before = snapshot(state)
        actor = getattr(state, "actor_index", None)
        try:
            op = state.complete_bet_or_raise_to(target)
            print(
                f"  target={target}: ACCEPT actor={getattr(op, 'player_index', actor)} "
                f"amount={int(getattr(op, 'amount', 0))} before={before} after={snapshot(state)}"
            )
        except Exception as exc:
            print(
                f"  target={target}: REJECT {type(exc).__name__}: {exc} "
                f"before={before}"
            )
    print()


def main() -> None:
    # 3+ handed PokerKit convention maps player 0=SB, 1=BB, final player=BTN.
    probe("3p_short_BB_60", (1000, 60, 1000))
    probe("3p_short_SB_20", (20, 1000, 1000))
    probe("3p_both_blinds_short", (20, 60, 1000))
    probe("3p_short_BTN_70", (1000, 1000, 70))

    # Calling a short BB clearly matches the actually posted amount. Probe the
    # aggressive boundary separately before encoding it in DeepCash.
    probe_raise_boundaries(
        "3p_short_BB_60_first_actor",
        (1000, 60, 1000),
        (61, 80, 99, 100, 119, 120, 159, 160, 200),
    )
    probe_raise_boundaries(
        "3p_normal_BB_100_control",
        (1000, 1000, 1000),
        (101, 150, 199, 200, 250),
    )

    # Heads-up convention is the known exception used by the full-game oracle:
    # player 1 is Button/SB and player 0 is BB.
    probe("HU_short_BB_60", (60, 1000))
    probe("HU_short_SB_20", (1000, 20))
    probe_raise_boundaries(
        "HU_short_BB_60_first_actor",
        (60, 1000),
        (61, 80, 99, 100, 119, 120, 159, 160, 200),
    )

    print(f"PokerKit short-blind probe complete; pin={PINNED_POKERKIT}")


if __name__ == "__main__":
    main()
