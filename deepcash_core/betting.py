from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Mapping, Sequence


class StreetActionKind(str, Enum):
    FOLD = "FOLD"
    CHECK = "CHECK"
    CALL = "CALL"
    RAISE_TO = "RAISE_TO"


@dataclass(frozen=True)
class StreetAction:
    kind: StreetActionKind
    raise_to: int | None = None

    def __post_init__(self) -> None:
        if self.kind == StreetActionKind.RAISE_TO:
            if self.raise_to is None or self.raise_to <= 0:
                raise ValueError("RAISE_TO requires a positive target")
        elif self.raise_to is not None:
            raise ValueError("only RAISE_TO may carry raise_to")


@dataclass(frozen=True)
class StreetPlayer:
    """Street-local chip state; ``stack`` is remaining stack after committed chips."""

    committed: int
    stack: int
    folded: bool = False
    all_in: bool = False
    last_faced_bet: int | None = None

    def __post_init__(self) -> None:
        if self.committed < 0 or self.stack < 0:
            raise ValueError("chips cannot be negative")
        if self.stack == 0 and not self.folded and not self.all_in:
            object.__setattr__(self, "all_in", True)


@dataclass(frozen=True)
class LegalActions:
    actor: int
    to_call: int
    can_fold: bool
    can_check: bool
    can_call: bool
    can_raise: bool
    min_full_raise_to: int | None
    max_raise_to: int | None
    short_all_in_only: bool = False


@dataclass(frozen=True)
class BettingRoundState:
    """Pure one-street no-limit state machine with short-all-in reopen tracking."""

    order: tuple[int, ...]
    players: Mapping[int, StreetPlayer]
    min_bet: int
    current_bet: int
    last_full_raise: int
    pending: frozenset[int]
    next_index: int = 0

    @classmethod
    def create(
        cls,
        *,
        order: Sequence[int],
        stacks: Mapping[int, int],
        committed: Mapping[int, int] | None = None,
        min_bet: int,
    ) -> "BettingRoundState":
        order_t = tuple(int(s) for s in order)
        if len(order_t) < 2 or len(set(order_t)) != len(order_t):
            raise ValueError("order must contain unique seats")
        if min_bet <= 0:
            raise ValueError("min_bet must be positive")
        if set(order_t) != set(stacks):
            raise ValueError("stacks must match order seats exactly")
        committed = {} if committed is None else committed
        if not set(committed).issubset(stacks):
            raise ValueError("committed contains unknown seat")

        players: dict[int, StreetPlayer] = {}
        for seat in order_t:
            stack = int(stacks[seat])
            com = int(committed.get(seat, 0))
            if stack < 0 or com < 0:
                raise ValueError("chips cannot be negative")
            players[seat] = StreetPlayer(com, stack, all_in=(stack == 0))
        current_bet = max((p.committed for p in players.values()), default=0)
        pending = frozenset(seat for seat, p in players.items() if not p.folded and not p.all_in)
        return cls(order_t, players, int(min_bet), current_bet, int(min_bet), pending, 0)

    @property
    def complete(self) -> bool:
        return not self.pending or len([p for p in self.players.values() if not p.folded]) <= 1

    @property
    def actor(self) -> int | None:
        if self.complete:
            return None
        n = len(self.order)
        for offset in range(n):
            idx = (self.next_index + offset) % n
            seat = self.order[idx]
            if seat in self.pending:
                return seat
        raise RuntimeError("pending seats are not present in action order")

    def _raise_reopened(self, seat: int) -> bool:
        p = self.players[seat]
        if p.last_faced_bet is None:
            return True
        return self.current_bet - p.last_faced_bet >= self.last_full_raise

    def legal_actions(self) -> LegalActions:
        actor = self.actor
        if actor is None:
            raise ValueError("betting round is complete")
        p = self.players[actor]
        to_call = max(0, self.current_bet - p.committed)
        max_to = p.committed + p.stack
        can_raise = self._raise_reopened(actor) and max_to > self.current_bet
        min_full = (self.current_bet + self.last_full_raise) if self.current_bet > 0 else self.min_bet
        short_only = can_raise and max_to < min_full
        return LegalActions(
            actor=actor,
            to_call=to_call,
            can_fold=to_call > 0,
            can_check=to_call == 0,
            can_call=to_call > 0 and p.stack > 0,
            can_raise=can_raise,
            min_full_raise_to=min_full if can_raise else None,
            max_raise_to=max_to if can_raise else None,
            short_all_in_only=short_only,
        )

    def apply(self, action: StreetAction) -> "BettingRoundState":
        legal = self.legal_actions()
        actor = legal.actor
        players = dict(self.players)
        p = players[actor]
        pending = set(self.pending)
        pending.discard(actor)
        current_bet = self.current_bet
        last_full_raise = self.last_full_raise

        if action.kind == StreetActionKind.FOLD:
            if not legal.can_fold:
                raise ValueError("FOLD is not legal")
            players[actor] = replace(p, folded=True, last_faced_bet=current_bet)

        elif action.kind == StreetActionKind.CHECK:
            if not legal.can_check:
                raise ValueError("CHECK is not legal")
            players[actor] = replace(p, last_faced_bet=current_bet)

        elif action.kind == StreetActionKind.CALL:
            if not legal.can_call:
                raise ValueError("CALL is not legal")
            paid = min(legal.to_call, p.stack)
            players[actor] = replace(
                p,
                committed=p.committed + paid,
                stack=p.stack - paid,
                all_in=(p.stack - paid == 0),
                last_faced_bet=current_bet,
            )

        elif action.kind == StreetActionKind.RAISE_TO:
            if not legal.can_raise or action.raise_to is None:
                raise ValueError("RAISE_TO is not legal")
            target = int(action.raise_to)
            assert legal.max_raise_to is not None and legal.min_full_raise_to is not None
            if target <= current_bet or target > legal.max_raise_to:
                raise ValueError("raise target outside legal interval")
            if target < legal.min_full_raise_to and target != legal.max_raise_to:
                raise ValueError("sub-minimum raise is legal only as all-in")

            paid = target - p.committed
            old_bet = current_bet
            increment = target - old_bet
            is_full_raise = increment >= last_full_raise
            players[actor] = replace(
                p,
                committed=target,
                stack=p.stack - paid,
                all_in=(p.stack - paid == 0),
                last_faced_bet=target,
            )
            current_bet = target
            if is_full_raise:
                last_full_raise = increment
                pending = {
                    seat for seat, q in players.items()
                    if seat != actor and not q.folded and not q.all_in
                }
            else:
                # A short all-in does not automatically reopen betting, but every
                # live player now below the price must respond. Reopening is per
                # player and cumulative since that player's previous action.
                pending |= {
                    seat for seat, q in players.items()
                    if seat != actor and not q.folded and not q.all_in and q.committed < current_bet
                }
        else:  # pragma: no cover
            raise AssertionError(action.kind)

        actor_idx = self.order.index(actor)
        next_index = (actor_idx + 1) % len(self.order)
        return BettingRoundState(
            order=self.order,
            players=players,
            min_bet=self.min_bet,
            current_bet=current_bet,
            last_full_raise=last_full_raise,
            pending=frozenset(pending),
            next_index=next_index,
        )
