from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Mapping, Sequence


class ShortAllInReopenPolicy(str, Enum):
    """How a prior actor regains raise rights after sub-minimum all-in raises."""

    NEVER = "NEVER"
    ANY_INCREASE = "ANY_INCREASE"
    CUMULATIVE_FULL_RAISE = "CUMULATIVE_FULL_RAISE"


@dataclass(frozen=True)
class BettingConfig:
    # Conventional cash behavior is the default research hypothesis, but the
    # rule remains explicit/configurable until target-site evidence freezes it.
    short_all_in_reopen: ShortAllInReopenPolicy = ShortAllInReopenPolicy.CUMULATIVE_FULL_RAISE
    allow_short_all_in_raise: bool = True


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
    # None means no prior action in the current full-raise epoch. Otherwise this
    # is the price faced at the player's most recent action in that epoch.
    last_faced_bet: int | None = None

    def __post_init__(self) -> None:
        if self.committed < 0 or self.stack < 0:
            raise ValueError("chips cannot be negative")
        if self.folded and self.all_in:
            raise ValueError("player cannot be folded and all-in")
        if self.stack == 0 and not self.folded and not self.all_in:
            object.__setattr__(self, "all_in", True)
        if self.all_in and self.stack != 0:
            raise ValueError("all-in player must have zero stack")
        if self.last_faced_bet is not None and self.last_faced_bet < 0:
            raise ValueError("last_faced_bet cannot be negative")


@dataclass(frozen=True)
class LegalActions:
    actor: int
    to_call: int
    call_amount: int
    can_fold: bool
    can_check: bool
    can_call: bool
    can_raise: bool
    min_full_raise_to: int | None
    max_raise_to: int | None
    short_all_in_only: bool = False
    raise_right_open: bool = False


def _normalize_pending_static(
    players: Mapping[int, StreetPlayer],
    current_bet: int,
    pending: set[int],
) -> set[int]:
    """Remove impossible dry-side-pot checks while preserving call/fold duties."""
    actionable = [
        (seat, p)
        for seat, p in players.items()
        if not p.folded and not p.all_in and p.stack > 0
    ]
    if len(actionable) == 1:
        seat, p = actionable[0]
        if p.committed >= current_bet:
            pending.discard(seat)
    return pending


@dataclass(frozen=True)
class BettingRoundState:
    """Pure one-street no-limit state machine with explicit reopen semantics."""

    order: tuple[int, ...]
    players: Mapping[int, StreetPlayer]
    min_bet: int
    current_bet: int
    last_full_raise: int
    pending: frozenset[int]
    next_index: int = 0
    config: BettingConfig = BettingConfig()

    @classmethod
    def create(
        cls,
        *,
        order: Sequence[int],
        stacks: Mapping[int, int],
        committed: Mapping[int, int] | None = None,
        min_bet: int,
        config: BettingConfig | None = None,
    ) -> "BettingRoundState":
        order_t = tuple(int(s) for s in order)
        if not 2 <= len(order_t) <= 6 or len(set(order_t)) != len(order_t):
            raise ValueError("order must contain 2..6 unique seats")
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
        pending = {
            seat for seat, p in players.items()
            if not p.folded and not p.all_in and p.stack > 0
        }
        pending = _normalize_pending_static(players, current_bet, pending)
        state = cls(
            order=order_t,
            players=players,
            min_bet=int(min_bet),
            current_bet=current_bet,
            last_full_raise=int(min_bet),
            pending=frozenset(pending),
            next_index=0,
            config=config or BettingConfig(),
        )
        state.validate()
        return state

    def validate(self) -> None:
        if not 2 <= len(self.order) <= 6 or len(set(self.order)) != len(self.order):
            raise ValueError("invalid action order")
        if set(self.order) != set(self.players):
            raise ValueError("players must exactly match action order")
        if self.min_bet <= 0 or self.last_full_raise <= 0 or self.current_bet < 0:
            raise ValueError("invalid betting geometry")
        for p in self.players.values():
            if p.committed > self.current_bet:
                raise ValueError("player commitment exceeds current bet")
        if max((p.committed for p in self.players.values()), default=0) != self.current_bet:
            raise ValueError("current_bet must equal maximum street commitment")
        eligible = {
            seat for seat, p in self.players.items()
            if not p.folded and not p.all_in and p.stack > 0
        }
        if not self.pending.issubset(eligible):
            raise ValueError("pending contains ineligible seat")
        expected = _normalize_pending_static(self.players, self.current_bet, set(self.pending))
        if expected != set(self.pending):
            raise ValueError("pending contains redundant dry-side-pot action")

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
        increase = self.current_bet - p.last_faced_bet
        policy = self.config.short_all_in_reopen
        if policy == ShortAllInReopenPolicy.NEVER:
            return False
        if policy == ShortAllInReopenPolicy.ANY_INCREASE:
            return increase > 0
        if policy == ShortAllInReopenPolicy.CUMULATIVE_FULL_RAISE:
            return increase >= self.last_full_raise
        raise AssertionError(policy)

    def legal_actions(self) -> LegalActions:
        self.validate()
        actor = self.actor
        if actor is None:
            raise ValueError("betting round is complete")
        p = self.players[actor]
        to_call = max(0, self.current_bet - p.committed)
        call_amount = min(to_call, p.stack)
        max_to = p.committed + p.stack
        raise_right_open = self._raise_reopened(actor)
        # A nominally non-all-in opponent is not enough to justify a raise. If
        # that opponent's entire remaining stack cannot exceed the current bet,
        # they can only fold or call all-in to the existing price; they cannot
        # contest any additional side-pot tranche. Raising would merely create
        # an immediately uncalled excess. PokerKit independently exposed this
        # corner case in a 4-handed randomized trace.
        opponent_can_respond = any(
            seat != actor
            and not q.folded
            and not q.all_in
            and q.stack > 0
            and q.committed + q.stack > self.current_bet
            for seat, q in self.players.items()
        )
        can_raise = raise_right_open and opponent_can_respond and max_to > self.current_bet
        min_full = self.current_bet + self.last_full_raise if self.current_bet > 0 else self.min_bet
        short_only = can_raise and max_to < min_full
        if short_only and not self.config.allow_short_all_in_raise:
            can_raise = False
            short_only = False
        return LegalActions(
            actor=actor,
            to_call=to_call,
            call_amount=call_amount,
            can_fold=to_call > 0,
            can_check=to_call == 0,
            can_call=to_call > 0 and p.stack > 0,
            can_raise=can_raise,
            min_full_raise_to=min_full if can_raise else None,
            max_raise_to=max_to if can_raise else None,
            short_all_in_only=short_only,
            raise_right_open=raise_right_open,
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
            paid = legal.call_amount
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
            if target < legal.min_full_raise_to:
                if not legal.short_all_in_only or target != legal.max_raise_to:
                    raise ValueError("sub-minimum raise is legal only as exact all-in")

            paid = target - p.committed
            if paid <= 0 or paid > p.stack:
                raise ValueError("raise payment outside stack")
            old_bet = current_bet
            increment = target - old_bet
            is_full_raise = increment >= last_full_raise
            updated = replace(
                p,
                committed=target,
                stack=p.stack - paid,
                all_in=(p.stack - paid == 0),
                last_faced_bet=target,
            )
            if not is_full_raise and not updated.all_in:
                raise ValueError("sub-minimum raise must be all-in")
            players[actor] = updated
            current_bet = target

            if is_full_raise:
                last_full_raise = increment
                # A full raise creates a new epoch and reopens every other live
                # player's raise rights. Their prior faced-price is no longer the
                # relevant threshold.
                for seat, q in tuple(players.items()):
                    if seat != actor and not q.folded and not q.all_in:
                        players[seat] = replace(q, last_faced_bet=None)
                pending = {
                    seat for seat, q in players.items()
                    if seat != actor and not q.folded and not q.all_in and q.stack > 0
                }
            else:
                # A short all-in changes the price but does not reset the epoch.
                # Everyone live below the new price must respond; whether prior
                # actors may reraise is decided by the explicit reopen policy.
                pending = {
                    seat for seat, q in players.items()
                    if seat != actor and not q.folded and not q.all_in and q.stack > 0
                    and q.committed < current_bet
                }
        else:  # pragma: no cover
            raise AssertionError(action.kind)

        if len([q for q in players.values() if not q.folded]) <= 1:
            pending.clear()
        else:
            eligible = {
                seat for seat, q in players.items()
                if not q.folded and not q.all_in and q.stack > 0
            }
            pending &= eligible
            pending = _normalize_pending_static(players, current_bet, pending)

        actor_idx = self.order.index(actor)
        next_index = (actor_idx + 1) % len(self.order)
        result = BettingRoundState(
            order=self.order,
            players=players,
            min_bet=self.min_bet,
            current_bet=current_bet,
            last_full_raise=last_full_raise,
            pending=frozenset(pending),
            next_index=next_index,
            config=self.config,
        )
        result.validate()
        return result
