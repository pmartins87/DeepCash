from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Iterable, Mapping, Sequence

from .canonical import RANK_VALUE, SUITS, SUIT_VALUE
from .cards import card_to_str
from .hand import HandState, Street


@dataclass(frozen=True)
class PlayerSnapshot:
    seat: int
    stack: int
    committed_total: int
    committed_street: int
    folded: bool = False
    all_in: bool = False

    def __post_init__(self) -> None:
        if self.stack < 0 or self.committed_total < 0 or self.committed_street < 0:
            raise ValueError("chip fields cannot be negative")
        if self.committed_street > self.committed_total:
            raise ValueError("street commitment cannot exceed total commitment")
        if self.folded and self.all_in:
            raise ValueError("player cannot be folded and all-in")


@dataclass(frozen=True)
class ActionSnapshot:
    street: str
    actor: int
    kind: str
    raise_to: int | None = None
    paid: int = 0
    pot_before: int = 0
    to_call_before: int = 0
    current_bet_before: int = 0
    actor_committed_before: int = 0
    min_full_raise_to_before: int | None = None

    def __post_init__(self) -> None:
        if not self.street:
            raise ValueError("street is required")
        if self.kind not in {"FOLD", "CHECK", "CALL", "RAISE_TO"}:
            raise ValueError(f"unsupported action kind: {self.kind}")
        if self.kind == "RAISE_TO":
            if self.raise_to is None or self.raise_to <= 0:
                raise ValueError("RAISE_TO requires positive raise_to")
        elif self.raise_to is not None:
            raise ValueError("only RAISE_TO carries raise_to")
        for value in (
            self.paid,
            self.pot_before,
            self.to_call_before,
            self.current_bet_before,
            self.actor_committed_before,
        ):
            if value < 0:
                raise ValueError("action geometry cannot be negative")
        if self.min_full_raise_to_before is not None and self.min_full_raise_to_before <= 0:
            raise ValueError("min_full_raise_to_before must be positive")


@dataclass(frozen=True)
class DecisionSnapshot:
    """Exact solver/encoder boundary before any lossy abstraction.

    Physical seat labels and absolute suit names are representational noise.
    Pot/call/stack/commitment geometry and ordered action semantics are not.
    """

    occupied_clockwise: tuple[int, ...]
    button: int
    actor: int
    hero_hole: tuple[str, str]
    flop: tuple[str, ...]
    turn: str | None
    river: str | None
    players: tuple[PlayerSnapshot, ...]
    pot: int
    to_call: int
    min_raise_to: int | None
    action_history: tuple[ActionSnapshot, ...] = ()

    def __post_init__(self) -> None:
        occupied = self.occupied_clockwise
        if not 2 <= len(occupied) <= 6 or len(set(occupied)) != len(occupied):
            raise ValueError("occupied_clockwise must contain 2..6 unique seats")
        if self.button not in occupied or self.actor not in occupied:
            raise ValueError("button and actor must be occupied")
        if len(self.hero_hole) != 2:
            raise ValueError("hero_hole must contain exactly two cards")
        if len(self.flop) not in (0, 3):
            raise ValueError("flop must contain zero or three cards")
        if self.turn is not None and len(self.flop) != 3:
            raise ValueError("turn cannot exist without flop")
        if self.river is not None and self.turn is None:
            raise ValueError("river cannot exist without turn")
        if self.pot < 0 or self.to_call < 0:
            raise ValueError("pot/to_call cannot be negative")
        if self.min_raise_to is not None and self.min_raise_to <= 0:
            raise ValueError("min_raise_to must be positive when present")

        by_seat = {p.seat: p for p in self.players}
        if len(by_seat) != len(self.players) or set(by_seat) != set(occupied):
            raise ValueError("players must cover occupied seats exactly once")
        if any(a.actor not in by_seat for a in self.action_history):
            raise ValueError("action actor is not occupied")
        _validate_distinct_cards(self.all_cards())

    def all_cards(self) -> tuple[str, ...]:
        cards: list[str] = list(self.hero_hole) + list(self.flop)
        if self.turn is not None:
            cards.append(self.turn)
        if self.river is not None:
            cards.append(self.river)
        return tuple(cards)


def _validate_card(card: str) -> str:
    if not isinstance(card, str) or len(card) != 2:
        raise ValueError(f"invalid card: {card!r}")
    if card[0] not in RANK_VALUE or card[1] not in SUIT_VALUE:
        raise ValueError(f"invalid card: {card!r}")
    return card


def _validate_distinct_cards(cards: Iterable[str]) -> None:
    vals = tuple(_validate_card(c) for c in cards)
    if len(set(vals)) != len(vals):
        raise ValueError("duplicate known card")


def _card_key(card: str) -> tuple[int, int]:
    return (RANK_VALUE[card[0]], SUIT_VALUE[card[1]])


def _rename(card: str, mapping: Mapping[str, str]) -> str:
    _validate_card(card)
    return card[0] + mapping[card[1]]


def _relative_seat_map(occupied_clockwise: Sequence[int], button: int) -> dict[int, int]:
    occupied = tuple(occupied_clockwise)
    idx = occupied.index(button)
    from_button = occupied[idx:] + occupied[:idx]
    return {seat: rel for rel, seat in enumerate(from_button)}


def _canonical_cards(snapshot: DecisionSnapshot, mapping: Mapping[str, str]) -> tuple:
    hole = tuple(
        sorted((_rename(c, mapping) for c in snapshot.hero_hole), key=_card_key, reverse=True)
    )
    flop = tuple(
        sorted((_rename(c, mapping) for c in snapshot.flop), key=_card_key, reverse=True)
    )
    turn = None if snapshot.turn is None else _rename(snapshot.turn, mapping)
    river = None if snapshot.river is None else _rename(snapshot.river, mapping)
    return hole, flop, turn, river


def canonical_decision_key(snapshot: DecisionSnapshot) -> tuple:
    """Return an immutable exact canonical key for a decision state.

    Invariances guaranteed by construction:
    - private-card order;
    - simultaneous flop order;
    - all 24 global suit permutations;
    - rotation/renaming of physical chairs while preserving clockwise order and
      the Button-relative strategic geometry.

    No bucketing is performed here. Every chip amount and historical action
    geometry is exact so later abstractions can be audited against this lossless
    boundary.
    """
    rel = _relative_seat_map(snapshot.occupied_clockwise, snapshot.button)
    players_by_seat = {p.seat: p for p in snapshot.players}
    players = tuple(
        (
            rel[seat],
            players_by_seat[seat].stack,
            players_by_seat[seat].committed_total,
            players_by_seat[seat].committed_street,
            players_by_seat[seat].folded,
            players_by_seat[seat].all_in,
        )
        for seat in sorted(snapshot.occupied_clockwise, key=rel.__getitem__)
    )
    actions = tuple(
        (
            a.street,
            rel[a.actor],
            a.kind,
            a.raise_to,
            a.paid,
            a.pot_before,
            a.to_call_before,
            a.current_bet_before,
            a.actor_committed_before,
            a.min_full_raise_to_before,
        )
        for a in snapshot.action_history
    )
    noncard = (
        len(snapshot.occupied_clockwise),
        rel[snapshot.actor],
        players,
        snapshot.pot,
        snapshot.to_call,
        snapshot.min_raise_to,
        actions,
    )

    card_candidates = []
    for perm in permutations(SUITS):
        mapping = dict(zip(SUITS, perm))
        card_candidates.append(_canonical_cards(snapshot, mapping))
    cards = min(card_candidates)
    return noncard + cards


def rotate_physical_seats(snapshot: DecisionSnapshot, mapping: Mapping[int, int]) -> DecisionSnapshot:
    """Metamorphic-test helper: rename every physical chair consistently."""
    if set(mapping) != set(snapshot.occupied_clockwise):
        raise ValueError("physical-seat mapping must cover every occupied seat")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("physical-seat mapping must be one-to-one")
    occupied = tuple(mapping[s] for s in snapshot.occupied_clockwise)
    players = tuple(
        PlayerSnapshot(
            seat=mapping[p.seat],
            stack=p.stack,
            committed_total=p.committed_total,
            committed_street=p.committed_street,
            folded=p.folded,
            all_in=p.all_in,
        )
        for p in snapshot.players
    )
    actions = tuple(
        ActionSnapshot(
            street=a.street,
            actor=mapping[a.actor],
            kind=a.kind,
            raise_to=a.raise_to,
            paid=a.paid,
            pot_before=a.pot_before,
            to_call_before=a.to_call_before,
            current_bet_before=a.current_bet_before,
            actor_committed_before=a.actor_committed_before,
            min_full_raise_to_before=a.min_full_raise_to_before,
        )
        for a in snapshot.action_history
    )
    return DecisionSnapshot(
        occupied_clockwise=occupied,
        button=mapping[snapshot.button],
        actor=mapping[snapshot.actor],
        hero_hole=snapshot.hero_hole,
        flop=snapshot.flop,
        turn=snapshot.turn,
        river=snapshot.river,
        players=players,
        pot=snapshot.pot,
        to_call=snapshot.to_call,
        min_raise_to=snapshot.min_raise_to,
        action_history=actions,
    )


def decision_snapshot_from_hand_state(state: HandState) -> DecisionSnapshot:
    """Project an exact non-terminal engine state into the canonical boundary.

    Only the current actor's private cards are exposed. Opponent hole cards that
    exist inside the simulator's ``HandSetup`` are deliberately not leaked into
    the decision representation.
    """
    if state.terminal or state.betting is None or state.actor is None:
        raise ValueError("a decision snapshot requires a non-terminal actor")

    actor = state.actor
    legal = state.betting.legal_actions()
    visible = tuple(card_to_str(c) for c in state.visible_board)
    flop: tuple[str, ...] = () if len(visible) == 0 else visible[:3]
    turn = visible[3] if len(visible) >= 4 else None
    river = visible[4] if len(visible) >= 5 else None

    players: list[PlayerSnapshot] = []
    for seat in state.plan.occupied:
        street_player = state.betting.players.get(seat)
        committed_street = 0 if street_player is None else street_player.committed
        folded = seat in state.folded
        all_in = (not folded) and state.remaining[seat] == 0
        players.append(
            PlayerSnapshot(
                seat=seat,
                stack=int(state.remaining[seat]),
                committed_total=int(state.total_contributed[seat]),
                committed_street=int(committed_street),
                folded=folded,
                all_in=all_in,
            )
        )

    history = tuple(
        ActionSnapshot(
            street=record.street.value,
            actor=record.actor,
            kind=record.action.kind.value,
            raise_to=record.action.raise_to,
            paid=record.paid,
            pot_before=record.pot_before,
            to_call_before=record.to_call_before,
            current_bet_before=record.current_bet_before,
            actor_committed_before=record.actor_committed_before,
            min_full_raise_to_before=record.min_full_raise_to_before,
        )
        for record in state.actions
    )

    return DecisionSnapshot(
        occupied_clockwise=state.plan.occupied,
        button=state.plan.button,
        actor=actor,
        hero_hole=tuple(card_to_str(c) for c in state.setup.hole_cards[actor]),  # type: ignore[arg-type]
        flop=flop,
        turn=turn,
        river=river,
        players=tuple(players),
        pot=sum(int(v) for v in state.total_contributed.values()),
        to_call=legal.to_call,
        min_raise_to=legal.min_full_raise_to if legal.can_raise else None,
        action_history=history,
    )
