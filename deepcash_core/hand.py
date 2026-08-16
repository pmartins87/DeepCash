from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .betting import BettingConfig, BettingRoundState, StreetAction
from .cards import require_distinct
from .evaluator import evaluate_best
from .pots import award_side_pots, build_side_pots, normalize_uncalled
from .seating import SeatPlan, build_seat_plan


class Street(str, Enum):
    PREFLOP = "PREFLOP"
    FLOP = "FLOP"
    TURN = "TURN"
    RIVER = "RIVER"
    TERMINAL_FOLD = "TERMINAL_FOLD"
    SHOWDOWN = "SHOWDOWN"


@dataclass(frozen=True)
class HandSetup:
    occupied_clockwise: tuple[int, ...]
    button: int
    stacks: Mapping[int, int]
    small_blind: int
    big_blind: int
    hole_cards: Mapping[int, tuple[int, int]]
    board: tuple[int, int, int, int, int]
    betting_config: BettingConfig = BettingConfig()

    def __post_init__(self) -> None:
        plan = build_seat_plan(self.occupied_clockwise, self.button)
        seats = set(plan.occupied)
        if set(self.stacks) != seats:
            raise ValueError("stacks must match occupied seats")
        if set(self.hole_cards) != seats:
            raise ValueError("hole cards must match occupied seats")
        if self.small_blind <= 0 or self.big_blind <= self.small_blind:
            raise ValueError("invalid blind structure")
        if any(int(v) < self.big_blind for v in self.stacks.values()):
            raise ValueError("v1 requires every dealt stack to cover a full big blind")
        if len(self.board) != 5:
            raise ValueError("board must contain five cards")
        all_cards: list[int] = list(self.board)
        for seat in plan.occupied:
            hole = tuple(self.hole_cards[seat])
            if len(hole) != 2:
                raise ValueError("each player must have exactly two hole cards")
            all_cards.extend(hole)
        require_distinct(all_cards)


@dataclass(frozen=True)
class HandActionRecord:
    street: Street
    actor: int
    action: StreetAction


@dataclass(frozen=True)
class HandState:
    setup: HandSetup
    plan: SeatPlan
    street: Street
    visible_board: tuple[int, ...]
    remaining: Mapping[int, int]
    total_contributed: Mapping[int, int]
    folded: frozenset[int]
    betting: BettingRoundState | None
    actions: tuple[HandActionRecord, ...] = ()

    @classmethod
    def new(cls, setup: HandSetup) -> "HandState":
        plan = build_seat_plan(setup.occupied_clockwise, setup.button)
        remaining = {s: int(setup.stacks[s]) for s in plan.occupied}
        contributed = {s: 0 for s in plan.occupied}

        sb = plan.small_blind
        bb = plan.big_blind
        remaining[sb] -= setup.small_blind
        contributed[sb] += setup.small_blind
        remaining[bb] -= setup.big_blind
        contributed[bb] += setup.big_blind

        betting = BettingRoundState.create(
            order=plan.preflop_order,
            stacks=remaining,
            committed={sb: setup.small_blind, bb: setup.big_blind},
            min_bet=setup.big_blind,
            config=setup.betting_config,
        )
        state = cls(
            setup=setup,
            plan=plan,
            street=Street.PREFLOP,
            visible_board=(),
            remaining=remaining,
            total_contributed=contributed,
            folded=frozenset(),
            betting=betting,
        )
        return state._advance_automatic()

    @property
    def terminal(self) -> bool:
        return self.street in (Street.TERMINAL_FOLD, Street.SHOWDOWN)

    @property
    def actor(self) -> int | None:
        return None if self.betting is None else self.betting.actor

    @property
    def live_seats(self) -> tuple[int, ...]:
        return tuple(s for s in self.plan.occupied if s not in self.folded)

    def apply(self, action: StreetAction) -> "HandState":
        if self.terminal or self.betting is None:
            raise ValueError("hand has no betting action")
        actor = self.betting.actor
        if actor is None:
            raise ValueError("betting round is complete")

        old_player = self.betting.players[actor]
        next_betting = self.betting.apply(action)
        new_player = next_betting.players[actor]
        paid = old_player.stack - new_player.stack
        if paid < 0:
            raise AssertionError("stack increased during action")

        remaining = dict(self.remaining)
        remaining[actor] -= paid
        if remaining[actor] != new_player.stack:
            raise AssertionError("full-hand and street stacks diverged")
        contributed = dict(self.total_contributed)
        contributed[actor] += paid
        folded = set(self.folded)
        if new_player.folded:
            folded.add(actor)

        state = HandState(
            setup=self.setup,
            plan=self.plan,
            street=self.street,
            visible_board=self.visible_board,
            remaining=remaining,
            total_contributed=contributed,
            folded=frozenset(folded),
            betting=next_betting,
            actions=self.actions + (HandActionRecord(self.street, actor, action),),
        )
        return state._advance_automatic()

    def _advance_automatic(self) -> "HandState":
        state = self
        while True:
            live = state.live_seats
            if len(live) == 1:
                return HandState(
                    setup=state.setup,
                    plan=state.plan,
                    street=Street.TERMINAL_FOLD,
                    visible_board=state.visible_board,
                    remaining=state.remaining,
                    total_contributed=state.total_contributed,
                    folded=state.folded,
                    betting=None,
                    actions=state.actions,
                )

            if state.betting is not None and not state.betting.complete:
                return state

            # If at most one live player has chips, no further betting decision is
            # possible; deterministic simulation can run the supplied board out.
            actionable = [s for s in live if state.remaining[s] > 0]
            if len(actionable) <= 1 or state.street == Street.RIVER:
                return HandState(
                    setup=state.setup,
                    plan=state.plan,
                    street=Street.SHOWDOWN,
                    visible_board=state.setup.board,
                    remaining=state.remaining,
                    total_contributed=state.total_contributed,
                    folded=state.folded,
                    betting=None,
                    actions=state.actions,
                )

            next_street, board_count = {
                Street.PREFLOP: (Street.FLOP, 3),
                Street.FLOP: (Street.TURN, 4),
                Street.TURN: (Street.RIVER, 5),
            }[state.street]
            order = tuple(s for s in state.plan.postflop_order if s in live)
            betting = BettingRoundState.create(
                order=order,
                stacks={s: state.remaining[s] for s in order},
                committed={},
                min_bet=state.setup.big_blind,
                config=state.setup.betting_config,
            )
            state = HandState(
                setup=state.setup,
                plan=state.plan,
                street=next_street,
                visible_board=state.setup.board[:board_count],
                remaining=state.remaining,
                total_contributed=state.total_contributed,
                folded=state.folded,
                betting=betting,
                actions=state.actions,
            )

    def gross_settlement(self) -> dict[int, int]:
        """Return contested-pot payouts plus uncalled return, before rake."""
        if not self.terminal:
            raise ValueError("hand is not terminal")

        normalized, uncalled = normalize_uncalled(self.total_contributed)
        payouts: dict[int, int] = {}
        if uncalled is not None:
            payouts[uncalled.seat] = uncalled.amount

        live = self.live_seats
        pots = build_side_pots(normalized, live)
        if self.street == Street.TERMINAL_FOLD:
            winner = live[0]
            payouts[winner] = payouts.get(winner, 0) + sum(p.amount for p in pots)
            return payouts

        values = {
            seat: evaluate_best((*self.setup.hole_cards[seat], *self.setup.board))
            for seat in live
        }
        odd_order = tuple(s for s in self.plan.postflop_order if s in live)
        won = award_side_pots(pots, values, odd_chip_order=odd_order)
        for seat, amount in won.items():
            payouts[seat] = payouts.get(seat, 0) + amount
        return payouts

    def chip_conservation_total(self) -> int:
        return sum(self.remaining.values()) + sum(self.total_contributed.values())
