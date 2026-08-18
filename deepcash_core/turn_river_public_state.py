from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations

from .cards import card_from_str, full_deck, require_distinct
from .evaluator import evaluate_best
from .river_lab import RangeCombo, RiverGameSpec, _valid_deals, materialize_bet_sizes
from .river_representation_gen2 import GEN2_REFERENCE_FRACTIONS


@dataclass(frozen=True)
class TurnPublicState:
    board: tuple[int, int, int, int]
    p0_range: tuple[RangeCombo, ...]
    p1_range: tuple[RangeCombo, ...]
    pot: int
    stack: int
    min_bet: int

    def validate(self) -> None:
        require_distinct(self.board)
        if len(self.board) != 4:
            raise ValueError("turn public state requires exactly four board cards")
        if self.pot <= 0 or self.stack <= 0 or self.min_bet <= 0:
            raise ValueError("pot/stack/min_bet must be positive")
        board_set = set(self.board)
        for rng in (self.p0_range, self.p1_range):
            if not rng:
                raise ValueError("turn ranges must be non-empty")
            for combo in rng:
                require_distinct(combo.hole)
                if board_set.intersection(combo.hole):
                    raise ValueError("range combo overlaps turn board")
                if float(combo.weight) <= 0.0:
                    raise ValueError("range weights must be positive")
        if not _compatible_turn_deals(self):
            raise ValueError("turn state has no compatible private deal")


@dataclass(frozen=True)
class RiverPublicChild:
    river_card: int
    spec: RiverGameSpec
    chance_mass: float
    chance_probability: float


def _compatible_turn_deals(state: TurnPublicState) -> tuple[tuple[int, int, float], ...]:
    deals = []
    for i, p0 in enumerate(state.p0_range):
        p0_cards = set(p0.hole)
        for j, p1 in enumerate(state.p1_range):
            if p0_cards.intersection(p1.hole):
                continue
            deals.append((i, j, float(p0.weight) * float(p1.weight)))
    return tuple(deals)


def parse_turn_board(text: str) -> tuple[int, int, int, int]:
    cards = tuple(card_from_str(token) for token in text.split())
    if len(cards) != 4:
        raise ValueError("turn board text must contain exactly four cards")
    require_distinct(cards)
    return cards  # type: ignore[return-value]


def turn_quantile_range(
    board: tuple[int, int, int, int], count: int, phase: float
) -> tuple[RangeCombo, ...]:
    """Deterministic small support selected from exact turn hand strength.

    This mirrors the river laboratory's quantile fixture generator but evaluates
    the six-card turn state. It is a test/compatibility support generator, not a
    production range model.
    """
    require_distinct(board)
    if len(board) != 4:
        raise ValueError("turn quantile range requires four board cards")
    if count <= 0:
        raise ValueError("range combo count must be positive")
    remaining = [card for card in full_deck() if card not in set(board)]
    combos = list(combinations(remaining, 2))
    combos.sort(key=lambda hole: (evaluate_best((*hole, *board)), hole))
    selected: list[RangeCombo] = []
    used: set[tuple[int, int]] = set()
    for k in range(count):
        q = min(0.999999, max(0.000001, (k + 0.5 + phase) / count))
        index = round(q * (len(combos) - 1))
        while combos[index] in used:
            index = min(len(combos) - 1, index + 1)
        used.add(combos[index])
        selected.append(RangeCombo(tuple(combos[index])))
    return tuple(selected)


def build_turn_public_state(
    *,
    board_text: str,
    p0_phase: float,
    p1_phase: float,
    range_combos: int,
    pot: int,
    stack: int,
    min_bet: int,
) -> TurnPublicState:
    board = parse_turn_board(board_text)
    state = TurnPublicState(
        board=board,
        p0_range=turn_quantile_range(board, range_combos, p0_phase),
        p1_range=turn_quantile_range(board, range_combos, p1_phase),
        pot=int(pot),
        stack=int(stack),
        min_bet=int(min_bet),
    )
    state.validate()
    return state


def river_child_spec(
    state: TurnPublicState,
    river_card: int,
    *,
    fractions: tuple[Fraction, ...] = GEN2_REFERENCE_FRACTIONS,
) -> RiverGameSpec:
    state.validate()
    if river_card in state.board:
        raise ValueError("river card already appears on turn board")
    p0 = tuple(combo for combo in state.p0_range if river_card not in combo.hole)
    p1 = tuple(combo for combo in state.p1_range if river_card not in combo.hole)
    if not p0 or not p1:
        raise ValueError("river card eliminates an entire private range")
    bets = materialize_bet_sizes(
        pot=state.pot,
        stack=state.stack,
        min_bet=state.min_bet,
        fractions=fractions,
    )
    spec = RiverGameSpec((*state.board, river_card), p0, p1, state.pot, bets)
    if not _valid_deals(spec):
        raise ValueError("river child has no compatible private deals")
    return spec


def enumerate_river_children(
    state: TurnPublicState,
    *,
    fractions: tuple[Fraction, ...] = GEN2_REFERENCE_FRACTIONS,
) -> tuple[RiverPublicChild, ...]:
    """Enumerate exact public river chance with card-removal range conditioning.

    For each legal public river card, chance mass equals the total compatible
    private-deal weight after that card is removed. Every exact private deal has
    the same number of possible river cards, so normalizing these masses yields
    the exact marginal public-card distribution induced by the supplied ranges.
    """
    state.validate()
    raw: list[tuple[int, RiverGameSpec, float]] = []
    for river_card in full_deck():
        if river_card in state.board:
            continue
        try:
            spec = river_child_spec(state, river_card, fractions=fractions)
        except ValueError:
            continue
        mass = sum(weight for _, _, weight in _valid_deals(spec))
        if mass > 0.0:
            raw.append((river_card, spec, float(mass)))
    total = sum(mass for _, _, mass in raw)
    if total <= 0.0:
        raise ValueError("turn state has no legal river public chance support")
    return tuple(
        RiverPublicChild(
            river_card=card,
            spec=spec,
            chance_mass=mass,
            chance_probability=mass / total,
        )
        for card, spec, mass in raw
    )
