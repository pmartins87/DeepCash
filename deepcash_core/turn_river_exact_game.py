from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping, Sequence

from .cards import full_deck
from .evaluator import evaluate_best
from .river_alternating_dcfr import AlternatingVariant, dcfr_regret_factor
from .river_lab import RangeCombo, _regret_strategy, materialize_bet_sizes
from .river_representation_gen2 import GEN2_REFERENCE_FRACTIONS
from .turn_river_public_state import TurnPublicState


InfoKey = tuple[int, str, int]
Policy = Mapping[InfoKey, tuple[float, ...]]

TURN_ROOT = "TURN_ROOT"
TURN_P1_AFTER_CHECK = "TURN_P1_AFTER_CHECK"


def turn_p1_vs_bet_node(amount: int) -> str:
    return f"TURN_P1_VS_BET_{int(amount)}"


def turn_p0_vs_bet_node(amount: int) -> str:
    return f"TURN_P0_VS_BET_{int(amount)}"


def p0_bet_call_history(amount: int) -> str:
    return f"P0_BET_{int(amount)}_CALL"


def p1_bet_call_history(amount: int) -> str:
    return f"P1_BET_{int(amount)}_CALL"


def river_root_node(history: str, river_card: int) -> str:
    return f"RIVER|{history}|{int(river_card)}|ROOT"


def river_p1_after_check_node(history: str, river_card: int) -> str:
    return f"RIVER|{history}|{int(river_card)}|P1_AFTER_CHECK"


def river_p1_vs_bet_node(history: str, river_card: int, amount: int) -> str:
    return f"RIVER|{history}|{int(river_card)}|P1_VS_BET|{int(amount)}"


def river_p0_vs_bet_node(history: str, river_card: int, amount: int) -> str:
    return f"RIVER|{history}|{int(river_card)}|P0_VS_BET|{int(amount)}"


@dataclass(frozen=True)
class TurnRiverGameSpec:
    """Exact HU turn+river one-bet-per-street control game.

    Player 0 acts first on both streets. A street may contain one bet and one
    fold/call response; raises are intentionally excluded. Public river chance,
    private-card removal, pot/stack transitions and both private ranges remain
    exact. This is an R6 correctness/control microgame, not the final production
    action abstraction.
    """

    turn_state: TurnPublicState
    turn_bet_sizes: tuple[int, ...]
    river_fractions: tuple[Fraction, ...] = GEN2_REFERENCE_FRACTIONS

    def validate(self) -> None:
        self.turn_state.validate()
        if not self.turn_bet_sizes:
            raise ValueError("turn_bet_sizes must be non-empty")
        if tuple(sorted(set(self.turn_bet_sizes))) != self.turn_bet_sizes:
            raise ValueError("turn_bet_sizes must be sorted and unique")
        if any(amount <= 0 or amount > self.turn_state.stack for amount in self.turn_bet_sizes):
            raise ValueError("turn bet sizes must be positive and no larger than stack")
        if not self.river_fractions or any(Fraction(value) <= 0 for value in self.river_fractions):
            raise ValueError("river_fractions must be non-empty and positive")


@dataclass
class TurnRiverSolverState:
    spec_signature: tuple
    variant: AlternatingVariant
    iterations: int
    regrets: dict[InfoKey, list[float]]
    strategy_sum: dict[InfoKey, list[float]]

    def validate(
        self,
        spec: TurnRiverGameSpec,
        *,
        variant: AlternatingVariant | str | None = None,
    ) -> None:
        spec.validate()
        if self.spec_signature != turn_river_spec_signature(spec):
            raise ValueError("turn+river checkpoint belongs to another game")
        if variant is not None and self.variant != AlternatingVariant(variant):
            raise ValueError("turn+river checkpoint variant mismatch")
        if self.iterations < 0:
            raise ValueError("iterations cannot be negative")

        expected = set(all_infosets(spec))
        if set(self.regrets) != expected or set(self.strategy_sum) != expected:
            raise ValueError("turn+river checkpoint infosets do not match game")
        for key in expected:
            n = len(actions_for_infoset(spec, key))
            if len(self.regrets[key]) != n or len(self.strategy_sum[key]) != n:
                raise ValueError(f"turn+river action shape mismatch at {key}")
            values = (*self.regrets[key], *self.strategy_sum[key])
            if any(not math.isfinite(value) for value in values):
                raise ValueError("turn+river checkpoint contains non-finite values")
            if any(value < 0.0 for value in self.strategy_sum[key]):
                raise ValueError("turn+river average-strategy sums cannot be negative")
            if not self.variant.is_dcfr and any(value < 0.0 for value in self.regrets[key]):
                raise ValueError("turn+river CFR+ regrets must remain non-negative")


@dataclass(frozen=True)
class TurnRiverSolveResult:
    """Current exact-control solve output.

    Exact best-response/exploitability is intentionally not claimed at this
    milestone; the next R6 gate adds a two-street BR oracle before numerical
    acceptance.
    """

    iterations: int
    policy: Mapping[InfoKey, tuple[float, ...]]
    policy_ev: float
    infosets: int
    action_slots: int


def build_turn_river_game(
    state: TurnPublicState,
    *,
    turn_fractions: Sequence[Fraction | float] = GEN2_REFERENCE_FRACTIONS,
    river_fractions: Sequence[Fraction | float] = GEN2_REFERENCE_FRACTIONS,
) -> TurnRiverGameSpec:
    state.validate()
    turn_bets = materialize_bet_sizes(
        pot=state.pot,
        stack=state.stack,
        min_bet=state.min_bet,
        fractions=turn_fractions,
    )
    spec = TurnRiverGameSpec(
        turn_state=state,
        turn_bet_sizes=turn_bets,
        river_fractions=tuple(Fraction(value) for value in river_fractions),
    )
    spec.validate()
    return spec


def turn_river_spec_signature(spec: TurnRiverGameSpec) -> tuple:
    spec.validate()
    state = spec.turn_state
    return (
        tuple(state.board),
        tuple((tuple(combo.hole), float(combo.weight)) for combo in state.p0_range),
        tuple((tuple(combo.hole), float(combo.weight)) for combo in state.p1_range),
        int(state.pot),
        int(state.stack),
        int(state.min_bet),
        tuple(spec.turn_bet_sizes),
        tuple((value.numerator, value.denominator) for value in spec.river_fractions),
    )


def valid_turn_deals(spec: TurnRiverGameSpec) -> tuple[tuple[int, int, float], ...]:
    state = spec.turn_state
    out: list[tuple[int, int, float]] = []
    for i, p0 in enumerate(state.p0_range):
        cards0 = set(p0.hole)
        for j, p1 in enumerate(state.p1_range):
            if cards0.intersection(p1.hole):
                continue
            out.append((i, j, float(p0.weight) * float(p1.weight)))
    if not out:
        raise ValueError("turn+river game has no compatible private deals")
    return tuple(out)


def legal_river_cards(spec: TurnRiverGameSpec, i: int, j: int) -> tuple[int, ...]:
    state = spec.turn_state
    blocked = set(state.board)
    blocked.update(state.p0_range[i].hole)
    blocked.update(state.p1_range[j].hole)
    cards = tuple(card for card in full_deck() if card not in blocked)
    if not cards:
        raise ValueError("private deal has no legal river card")
    return cards


def continuation_histories(spec: TurnRiverGameSpec) -> tuple[str, ...]:
    histories = ["CHECK_CHECK"]
    histories.extend(p0_bet_call_history(amount) for amount in spec.turn_bet_sizes)
    histories.extend(p1_bet_call_history(amount) for amount in spec.turn_bet_sizes)
    return tuple(histories)


def _history_turn_bet(spec: TurnRiverGameSpec, history: str) -> int:
    if history == "CHECK_CHECK":
        return 0
    parts = history.split("_")
    if len(parts) != 4 or parts[1] != "BET" or parts[3] != "CALL":
        raise ValueError(f"unknown turn continuation history: {history}")
    amount = int(parts[2])
    if amount not in spec.turn_bet_sizes:
        raise ValueError(f"turn continuation amount is not legal: {history}")
    return amount


def river_geometry(spec: TurnRiverGameSpec, history: str) -> tuple[int, int]:
    amount = _history_turn_bet(spec, history)
    state = spec.turn_state
    return state.pot + 2 * amount, state.stack - amount


def river_bet_sizes(spec: TurnRiverGameSpec, history: str) -> tuple[int, ...]:
    pot, stack = river_geometry(spec, history)
    if stack <= 0:
        return ()
    return materialize_bet_sizes(
        pot=pot,
        stack=stack,
        min_bet=spec.turn_state.min_bet,
        fractions=spec.river_fractions,
    )


def _parse_river_node(node: str) -> tuple[str, int, str, int | None]:
    parts = node.split("|")
    if len(parts) == 4 and parts[0] == "RIVER":
        history, card_text, kind = parts[1], parts[2], parts[3]
        if kind not in {"ROOT", "P1_AFTER_CHECK"}:
            raise ValueError(f"invalid river infoset node: {node}")
        return history, int(card_text), kind, None
    if len(parts) == 5 and parts[0] == "RIVER":
        history, card_text, kind, amount_text = parts[1], parts[2], parts[3], parts[4]
        if kind not in {"P1_VS_BET", "P0_VS_BET"}:
            raise ValueError(f"invalid river response node: {node}")
        return history, int(card_text), kind, int(amount_text)
    raise ValueError(f"invalid river infoset node: {node}")


def actions_for_infoset(spec: TurnRiverGameSpec, key: InfoKey) -> tuple[str, ...]:
    player, node, _ = key
    if player == 0 and node == TURN_ROOT:
        return ("CHECK", *(f"BET_{amount}" for amount in spec.turn_bet_sizes))
    if player == 1 and node == TURN_P1_AFTER_CHECK:
        return ("CHECK", *(f"BET_{amount}" for amount in spec.turn_bet_sizes))
    if (player == 1 and node.startswith("TURN_P1_VS_BET_")) or (
        player == 0 and node.startswith("TURN_P0_VS_BET_")
    ):
        return ("FOLD", "CALL")

    history, _river_card, kind, _amount = _parse_river_node(node)
    bets = river_bet_sizes(spec, history)
    if not bets:
        raise ValueError("all-in turn history has no river decision infosets")
    if player == 0 and kind == "ROOT":
        return ("CHECK", *(f"BET_{amount}" for amount in bets))
    if player == 1 and kind == "P1_AFTER_CHECK":
        return ("CHECK", *(f"BET_{amount}" for amount in bets))
    if (player == 1 and kind == "P1_VS_BET") or (
        player == 0 and kind == "P0_VS_BET"
    ):
        return ("FOLD", "CALL")
    raise ValueError(f"player/node mismatch: player={player} node={node}")


def all_infosets(spec: TurnRiverGameSpec) -> tuple[InfoKey, ...]:
    spec.validate()
    state = spec.turn_state
    keys: list[InfoKey] = []

    for i in range(len(state.p0_range)):
        keys.append((0, TURN_ROOT, i))
        for amount in spec.turn_bet_sizes:
            keys.append((0, turn_p0_vs_bet_node(amount), i))
    for j in range(len(state.p1_range)):
        keys.append((1, TURN_P1_AFTER_CHECK, j))
        for amount in spec.turn_bet_sizes:
            keys.append((1, turn_p1_vs_bet_node(amount), j))

    board = set(state.board)
    for history in continuation_histories(spec):
        _pot, stack = river_geometry(spec, history)
        if stack <= 0:
            continue
        bets = river_bet_sizes(spec, history)
        for river_card in full_deck():
            if river_card in board:
                continue
            for i, combo in enumerate(state.p0_range):
                if river_card in combo.hole:
                    continue
                keys.append((0, river_root_node(history, river_card), i))
                for amount in bets:
                    keys.append((0, river_p0_vs_bet_node(history, river_card, amount), i))
            for j, combo in enumerate(state.p1_range):
                if river_card in combo.hole:
                    continue
                keys.append((1, river_p1_after_check_node(history, river_card), j))
                for amount in bets:
                    keys.append((1, river_p1_vs_bet_node(history, river_card, amount), j))
    if len(keys) != len(set(keys)):
        raise RuntimeError("turn+river infoset enumeration produced duplicate keys")
    return tuple(keys)


def init_turn_river_solver(
    spec: TurnRiverGameSpec,
    variant: AlternatingVariant | str = AlternatingVariant.ALT_DCFR_150_0_2,
) -> TurnRiverSolverState:
    spec.validate()
    variant = AlternatingVariant(variant)
    infosets = all_infosets(spec)
    state = TurnRiverSolverState(
        spec_signature=turn_river_spec_signature(spec),
        variant=variant,
        iterations=0,
        regrets={key: [0.0] * len(actions_for_infoset(spec, key)) for key in infosets},
        strategy_sum={key: [0.0] * len(actions_for_infoset(spec, key)) for key in infosets},
    )
    state.validate(spec, variant=variant)
    return state


def _bet_amount(action: str) -> int:
    if not action.startswith("BET_"):
        raise ValueError(action)
    return int(action.split("_", 1)[1])


def _showdown_sign(spec: TurnRiverGameSpec, i: int, j: int, river_card: int) -> int:
    state = spec.turn_state
    value0 = evaluate_best((*state.p0_range[i].hole, *state.board, river_card))
    value1 = evaluate_best((*state.p1_range[j].hole, *state.board, river_card))
    return int(value0 > value1) - int(value0 < value1)


def _showdown_value(
    spec: TurnRiverGameSpec,
    i: int,
    j: int,
    river_card: int,
    *,
    pot: int,
    matched_bet: int = 0,
) -> float:
    sign = _showdown_sign(spec, i, j, river_card)
    return float(sign) * (float(pot) / 2.0 + float(matched_bet))


def _decision_value(
    *,
    player: int,
    key: InfoKey,
    actions: tuple[str, ...],
    action_values: list[float],
    chance: float,
    reach0: float,
    reach1: float,
    strategies: Policy,
    regret_delta: dict[InfoKey, list[float]],
    strategy_delta: dict[InfoKey, list[float]],
    average_weight: float,
) -> float:
    sigma = strategies[key]
    node_value = sum(probability * value for probability, value in zip(sigma, action_values))
    if player == 0:
        counterfactual_reach = chance * reach1
        average_reach = chance * reach0
        for index, value in enumerate(action_values):
            regret_delta[key][index] += counterfactual_reach * (value - node_value)
    else:
        counterfactual_reach = chance * reach0
        average_reach = chance * reach1
        for index, value in enumerate(action_values):
            regret_delta[key][index] += counterfactual_reach * (node_value - value)

    if average_weight > 0.0:
        for index, probability in enumerate(sigma):
            strategy_delta[key][index] += average_weight * average_reach * probability
    return node_value


def _traverse_river(
    spec: TurnRiverGameSpec,
    *,
    i: int,
    j: int,
    history: str,
    river_card: int,
    pot: int,
    stack: int,
    player: int,
    node_kind: str,
    chance: float,
    strategies: Policy,
    regret_delta: dict[InfoKey, list[float]],
    strategy_delta: dict[InfoKey, list[float]],
    average_weight: float,
    reach0: float,
    reach1: float,
    faced_bet: int | None = None,
) -> float:
    if stack <= 0:
        return _showdown_value(spec, i, j, river_card, pot=pot)

    if player == 0 and node_kind == "ROOT":
        node = river_root_node(history, river_card)
    elif player == 1 and node_kind == "P1_AFTER_CHECK":
        node = river_p1_after_check_node(history, river_card)
    elif player == 1 and node_kind == "P1_VS_BET" and faced_bet is not None:
        node = river_p1_vs_bet_node(history, river_card, faced_bet)
    elif player == 0 and node_kind == "P0_VS_BET" and faced_bet is not None:
        node = river_p0_vs_bet_node(history, river_card, faced_bet)
    else:
        raise AssertionError((player, node_kind, faced_bet))

    key = (player, node, i if player == 0 else j)
    actions = actions_for_infoset(spec, key)
    sigma = strategies[key]
    action_values: list[float] = []

    for action_index, action in enumerate(actions):
        next_reach0 = reach0 * sigma[action_index] if player == 0 else reach0
        next_reach1 = reach1 * sigma[action_index] if player == 1 else reach1

        if player == 0 and node_kind == "ROOT":
            if action == "CHECK":
                value = _traverse_river(
                    spec,
                    i=i,
                    j=j,
                    history=history,
                    river_card=river_card,
                    pot=pot,
                    stack=stack,
                    player=1,
                    node_kind="P1_AFTER_CHECK",
                    chance=chance,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    reach0=next_reach0,
                    reach1=next_reach1,
                )
            else:
                amount = _bet_amount(action)
                value = _traverse_river(
                    spec,
                    i=i,
                    j=j,
                    history=history,
                    river_card=river_card,
                    pot=pot,
                    stack=stack,
                    player=1,
                    node_kind="P1_VS_BET",
                    faced_bet=amount,
                    chance=chance,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    reach0=next_reach0,
                    reach1=next_reach1,
                )
        elif player == 1 and node_kind == "P1_AFTER_CHECK":
            if action == "CHECK":
                value = _showdown_value(spec, i, j, river_card, pot=pot)
            else:
                amount = _bet_amount(action)
                value = _traverse_river(
                    spec,
                    i=i,
                    j=j,
                    history=history,
                    river_card=river_card,
                    pot=pot,
                    stack=stack,
                    player=0,
                    node_kind="P0_VS_BET",
                    faced_bet=amount,
                    chance=chance,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    reach0=next_reach0,
                    reach1=next_reach1,
                )
        elif player == 1 and node_kind == "P1_VS_BET":
            assert faced_bet is not None
            value = (
                float(pot) / 2.0
                if action == "FOLD"
                else _showdown_value(
                    spec, i, j, river_card, pot=pot, matched_bet=faced_bet
                )
            )
        elif player == 0 and node_kind == "P0_VS_BET":
            assert faced_bet is not None
            value = (
                -float(pot) / 2.0
                if action == "FOLD"
                else _showdown_value(
                    spec, i, j, river_card, pot=pot, matched_bet=faced_bet
                )
            )
        else:  # pragma: no cover
            raise AssertionError((player, node_kind, action))
        action_values.append(value)

    return _decision_value(
        player=player,
        key=key,
        actions=actions,
        action_values=action_values,
        chance=chance,
        reach0=reach0,
        reach1=reach1,
        strategies=strategies,
        regret_delta=regret_delta,
        strategy_delta=strategy_delta,
        average_weight=average_weight,
    )


def _traverse_river_chance(
    spec: TurnRiverGameSpec,
    *,
    i: int,
    j: int,
    history: str,
    chance: float,
    strategies: Policy,
    regret_delta: dict[InfoKey, list[float]],
    strategy_delta: dict[InfoKey, list[float]],
    average_weight: float,
    reach0: float,
    reach1: float,
) -> float:
    pot, stack = river_geometry(spec, history)
    cards = legal_river_cards(spec, i, j)
    probability = 1.0 / float(len(cards))
    value = 0.0
    for river_card in cards:
        if stack <= 0:
            child = _showdown_value(spec, i, j, river_card, pot=pot)
        else:
            child = _traverse_river(
                spec,
                i=i,
                j=j,
                history=history,
                river_card=river_card,
                pot=pot,
                stack=stack,
                player=0,
                node_kind="ROOT",
                chance=chance * probability,
                strategies=strategies,
                regret_delta=regret_delta,
                strategy_delta=strategy_delta,
                average_weight=average_weight,
                reach0=reach0,
                reach1=reach1,
            )
        value += probability * child
    return value


def _traverse_turn(
    spec: TurnRiverGameSpec,
    *,
    i: int,
    j: int,
    chance: float,
    strategies: Policy,
    regret_delta: dict[InfoKey, list[float]],
    strategy_delta: dict[InfoKey, list[float]],
    average_weight: float,
    player: int = 0,
    node_kind: str = "ROOT",
    faced_bet: int | None = None,
    reach0: float = 1.0,
    reach1: float = 1.0,
) -> float:
    state = spec.turn_state
    if player == 0 and node_kind == "ROOT":
        node = TURN_ROOT
    elif player == 1 and node_kind == "P1_AFTER_CHECK":
        node = TURN_P1_AFTER_CHECK
    elif player == 1 and node_kind == "P1_VS_BET" and faced_bet is not None:
        node = turn_p1_vs_bet_node(faced_bet)
    elif player == 0 and node_kind == "P0_VS_BET" and faced_bet is not None:
        node = turn_p0_vs_bet_node(faced_bet)
    else:
        raise AssertionError((player, node_kind, faced_bet))

    key = (player, node, i if player == 0 else j)
    actions = actions_for_infoset(spec, key)
    sigma = strategies[key]
    action_values: list[float] = []

    for action_index, action in enumerate(actions):
        next_reach0 = reach0 * sigma[action_index] if player == 0 else reach0
        next_reach1 = reach1 * sigma[action_index] if player == 1 else reach1

        if player == 0 and node_kind == "ROOT":
            if action == "CHECK":
                value = _traverse_turn(
                    spec,
                    i=i,
                    j=j,
                    chance=chance,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    player=1,
                    node_kind="P1_AFTER_CHECK",
                    reach0=next_reach0,
                    reach1=next_reach1,
                )
            else:
                amount = _bet_amount(action)
                value = _traverse_turn(
                    spec,
                    i=i,
                    j=j,
                    chance=chance,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    player=1,
                    node_kind="P1_VS_BET",
                    faced_bet=amount,
                    reach0=next_reach0,
                    reach1=next_reach1,
                )
        elif player == 1 and node_kind == "P1_AFTER_CHECK":
            if action == "CHECK":
                value = _traverse_river_chance(
                    spec,
                    i=i,
                    j=j,
                    history="CHECK_CHECK",
                    chance=chance,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    reach0=next_reach0,
                    reach1=next_reach1,
                )
            else:
                amount = _bet_amount(action)
                value = _traverse_turn(
                    spec,
                    i=i,
                    j=j,
                    chance=chance,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    player=0,
                    node_kind="P0_VS_BET",
                    faced_bet=amount,
                    reach0=next_reach0,
                    reach1=next_reach1,
                )
        elif player == 1 and node_kind == "P1_VS_BET":
            assert faced_bet is not None
            if action == "FOLD":
                value = float(state.pot) / 2.0
            else:
                value = _traverse_river_chance(
                    spec,
                    i=i,
                    j=j,
                    history=p0_bet_call_history(faced_bet),
                    chance=chance,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    reach0=next_reach0,
                    reach1=next_reach1,
                )
        elif player == 0 and node_kind == "P0_VS_BET":
            assert faced_bet is not None
            if action == "FOLD":
                value = -float(state.pot) / 2.0
            else:
                value = _traverse_river_chance(
                    spec,
                    i=i,
                    j=j,
                    history=p1_bet_call_history(faced_bet),
                    chance=chance,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    reach0=next_reach0,
                    reach1=next_reach1,
                )
        else:  # pragma: no cover
            raise AssertionError((player, node_kind, action))
        action_values.append(value)

    return _decision_value(
        player=player,
        key=key,
        actions=actions,
        action_values=action_values,
        chance=chance,
        reach0=reach0,
        reach1=reach1,
        strategies=strategies,
        regret_delta=regret_delta,
        strategy_delta=strategy_delta,
        average_weight=average_weight,
    )


def _full_deltas(
    spec: TurnRiverGameSpec,
    strategies: Policy,
    *,
    average_weight: float,
) -> tuple[dict[InfoKey, list[float]], dict[InfoKey, list[float]]]:
    infosets = all_infosets(spec)
    regret_delta = {
        key: [0.0] * len(actions_for_infoset(spec, key))
        for key in infosets
    }
    strategy_delta = {
        key: [0.0] * len(actions_for_infoset(spec, key))
        for key in infosets
    }
    deals = valid_turn_deals(spec)
    total = sum(weight for _, _, weight in deals)
    for i, j, raw_weight in deals:
        _traverse_turn(
            spec,
            i=i,
            j=j,
            chance=raw_weight / total,
            strategies=strategies,
            regret_delta=regret_delta,
            strategy_delta=strategy_delta,
            average_weight=average_weight,
        )
    return regret_delta, strategy_delta


def _average_iteration_weight(variant: AlternatingVariant, iteration: int) -> float:
    if iteration <= 0:
        raise ValueError("average iteration must be positive")
    if variant == AlternatingVariant.ALT_CFR_PLUS_LINEAR:
        return float(iteration)
    return float(iteration * iteration)


def _apply_player_deltas(
    state: TurnRiverSolverState,
    regret_delta: Mapping[InfoKey, list[float]],
    strategy_delta: Mapping[InfoKey, list[float]],
    *,
    player: int,
    iteration: int,
) -> None:
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    for key, regrets in state.regrets.items():
        if key[0] != player:
            continue
        for index in range(len(regrets)):
            updated = regrets[index] + regret_delta[key][index]
            if state.variant.is_dcfr:
                exponent = 1.5 if updated >= 0.0 else float(state.variant.beta)
                updated *= dcfr_regret_factor(iteration, exponent)
            else:
                updated = max(0.0, updated)
            regrets[index] = updated
            state.strategy_sum[key][index] += strategy_delta[key][index]


def advance_turn_river_solver(
    spec: TurnRiverGameSpec,
    state: TurnRiverSolverState,
    *,
    additional_iterations: int,
) -> TurnRiverSolverState:
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec)
    if additional_iterations == 0:
        return state

    infosets = all_infosets(spec)
    for offset in range(1, additional_iterations + 1):
        iteration = state.iterations + offset
        weight = _average_iteration_weight(state.variant, iteration)

        strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
        regret0, average0 = _full_deltas(spec, strategies, average_weight=weight)
        _apply_player_deltas(
            state,
            regret0,
            average0,
            player=0,
            iteration=iteration,
        )

        strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
        regret1, average1 = _full_deltas(spec, strategies, average_weight=weight)
        _apply_player_deltas(
            state,
            regret1,
            average1,
            player=1,
            iteration=iteration,
        )

    state.iterations += additional_iterations
    state.validate(spec)
    return state


def normalize_policy(
    spec: TurnRiverGameSpec,
    strategy_sum: Mapping[InfoKey, Sequence[float]],
    regrets: Mapping[InfoKey, Sequence[float]],
) -> dict[InfoKey, tuple[float, ...]]:
    out: dict[InfoKey, tuple[float, ...]] = {}
    for key in all_infosets(spec):
        values = strategy_sum[key]
        total = sum(values)
        if total > 0.0:
            out[key] = tuple(value / total for value in values)
        else:
            out[key] = _regret_strategy(regrets[key])
    return out


def _policy_river_value(
    spec: TurnRiverGameSpec,
    policy: Policy,
    *,
    i: int,
    j: int,
    history: str,
    river_card: int,
    pot: int,
    stack: int,
    player: int,
    node_kind: str,
    faced_bet: int | None = None,
) -> float:
    if stack <= 0:
        return _showdown_value(spec, i, j, river_card, pot=pot)

    if player == 0 and node_kind == "ROOT":
        node = river_root_node(history, river_card)
    elif player == 1 and node_kind == "P1_AFTER_CHECK":
        node = river_p1_after_check_node(history, river_card)
    elif player == 1 and node_kind == "P1_VS_BET" and faced_bet is not None:
        node = river_p1_vs_bet_node(history, river_card, faced_bet)
    elif player == 0 and node_kind == "P0_VS_BET" and faced_bet is not None:
        node = river_p0_vs_bet_node(history, river_card, faced_bet)
    else:
        raise AssertionError((player, node_kind, faced_bet))

    key = (player, node, i if player == 0 else j)
    actions = actions_for_infoset(spec, key)
    values: list[float] = []
    for action in actions:
        if player == 0 and node_kind == "ROOT":
            if action == "CHECK":
                value = _policy_river_value(
                    spec,
                    policy,
                    i=i,
                    j=j,
                    history=history,
                    river_card=river_card,
                    pot=pot,
                    stack=stack,
                    player=1,
                    node_kind="P1_AFTER_CHECK",
                )
            else:
                value = _policy_river_value(
                    spec,
                    policy,
                    i=i,
                    j=j,
                    history=history,
                    river_card=river_card,
                    pot=pot,
                    stack=stack,
                    player=1,
                    node_kind="P1_VS_BET",
                    faced_bet=_bet_amount(action),
                )
        elif player == 1 and node_kind == "P1_AFTER_CHECK":
            if action == "CHECK":
                value = _showdown_value(spec, i, j, river_card, pot=pot)
            else:
                value = _policy_river_value(
                    spec,
                    policy,
                    i=i,
                    j=j,
                    history=history,
                    river_card=river_card,
                    pot=pot,
                    stack=stack,
                    player=0,
                    node_kind="P0_VS_BET",
                    faced_bet=_bet_amount(action),
                )
        elif player == 1 and node_kind == "P1_VS_BET":
            assert faced_bet is not None
            value = (
                float(pot) / 2.0
                if action == "FOLD"
                else _showdown_value(
                    spec, i, j, river_card, pot=pot, matched_bet=faced_bet
                )
            )
        elif player == 0 and node_kind == "P0_VS_BET":
            assert faced_bet is not None
            value = (
                -float(pot) / 2.0
                if action == "FOLD"
                else _showdown_value(
                    spec, i, j, river_card, pot=pot, matched_bet=faced_bet
                )
            )
        else:  # pragma: no cover
            raise AssertionError((player, node_kind, action))
        values.append(value)
    return sum(probability * value for probability, value in zip(policy[key], values))


def _policy_river_chance_value(
    spec: TurnRiverGameSpec,
    policy: Policy,
    *,
    i: int,
    j: int,
    history: str,
) -> float:
    pot, stack = river_geometry(spec, history)
    cards = legal_river_cards(spec, i, j)
    total = 0.0
    for river_card in cards:
        if stack <= 0:
            total += _showdown_value(spec, i, j, river_card, pot=pot)
        else:
            total += _policy_river_value(
                spec,
                policy,
                i=i,
                j=j,
                history=history,
                river_card=river_card,
                pot=pot,
                stack=stack,
                player=0,
                node_kind="ROOT",
            )
    return total / float(len(cards))


def _policy_turn_value(
    spec: TurnRiverGameSpec,
    policy: Policy,
    *,
    i: int,
    j: int,
    player: int = 0,
    node_kind: str = "ROOT",
    faced_bet: int | None = None,
) -> float:
    state = spec.turn_state
    if player == 0 and node_kind == "ROOT":
        node = TURN_ROOT
    elif player == 1 and node_kind == "P1_AFTER_CHECK":
        node = TURN_P1_AFTER_CHECK
    elif player == 1 and node_kind == "P1_VS_BET" and faced_bet is not None:
        node = turn_p1_vs_bet_node(faced_bet)
    elif player == 0 and node_kind == "P0_VS_BET" and faced_bet is not None:
        node = turn_p0_vs_bet_node(faced_bet)
    else:
        raise AssertionError((player, node_kind, faced_bet))

    key = (player, node, i if player == 0 else j)
    actions = actions_for_infoset(spec, key)
    values: list[float] = []
    for action in actions:
        if player == 0 and node_kind == "ROOT":
            if action == "CHECK":
                value = _policy_turn_value(
                    spec, policy, i=i, j=j, player=1, node_kind="P1_AFTER_CHECK"
                )
            else:
                value = _policy_turn_value(
                    spec,
                    policy,
                    i=i,
                    j=j,
                    player=1,
                    node_kind="P1_VS_BET",
                    faced_bet=_bet_amount(action),
                )
        elif player == 1 and node_kind == "P1_AFTER_CHECK":
            if action == "CHECK":
                value = _policy_river_chance_value(
                    spec, policy, i=i, j=j, history="CHECK_CHECK"
                )
            else:
                value = _policy_turn_value(
                    spec,
                    policy,
                    i=i,
                    j=j,
                    player=0,
                    node_kind="P0_VS_BET",
                    faced_bet=_bet_amount(action),
                )
        elif player == 1 and node_kind == "P1_VS_BET":
            assert faced_bet is not None
            value = (
                float(state.pot) / 2.0
                if action == "FOLD"
                else _policy_river_chance_value(
                    spec,
                    policy,
                    i=i,
                    j=j,
                    history=p0_bet_call_history(faced_bet),
                )
            )
        elif player == 0 and node_kind == "P0_VS_BET":
            assert faced_bet is not None
            value = (
                -float(state.pot) / 2.0
                if action == "FOLD"
                else _policy_river_chance_value(
                    spec,
                    policy,
                    i=i,
                    j=j,
                    history=p1_bet_call_history(faced_bet),
                )
            )
        else:  # pragma: no cover
            raise AssertionError((player, node_kind, action))
        values.append(value)
    return sum(probability * value for probability, value in zip(policy[key], values))


def evaluate_turn_river_policy(spec: TurnRiverGameSpec, policy: Policy) -> float:
    deals = valid_turn_deals(spec)
    total = sum(weight for _, _, weight in deals)
    return sum(
        weight * _policy_turn_value(spec, policy, i=i, j=j)
        for i, j, weight in deals
    ) / total


def conditioned_river_ranges(
    spec: TurnRiverGameSpec,
    policy: Policy,
    *,
    history: str,
    river_card: int,
) -> tuple[tuple[RangeCombo, ...], tuple[RangeCombo, ...]]:
    """Return exact action-conditioned ranges at a public river subgame.

    Each player's original combo weight is multiplied only by that player's own
    realization probability along the public turn history. The public river card
    is then removed exactly. Opponent private cards are never inspected when
    computing an individual combo's reach factor.
    """

    if history not in continuation_histories(spec):
        raise ValueError(f"unknown continuation history: {history}")
    if river_card in spec.turn_state.board:
        raise ValueError("river card already appears on turn board")

    state = spec.turn_state
    p0_out: list[RangeCombo] = []
    p1_out: list[RangeCombo] = []

    for i, combo in enumerate(state.p0_range):
        if river_card in combo.hole:
            continue
        root_actions = actions_for_infoset(spec, (0, TURN_ROOT, i))
        root = policy[(0, TURN_ROOT, i)]
        if history == "CHECK_CHECK":
            reach = root[root_actions.index("CHECK")]
        elif history.startswith("P0_BET_"):
            amount = _history_turn_bet(spec, history)
            reach = root[root_actions.index(f"BET_{amount}")]
        else:
            amount = _history_turn_bet(spec, history)
            check_reach = root[root_actions.index("CHECK")]
            response_key = (0, turn_p0_vs_bet_node(amount), i)
            response_actions = actions_for_infoset(spec, response_key)
            call_reach = policy[response_key][response_actions.index("CALL")]
            reach = check_reach * call_reach
        weight = float(combo.weight) * reach
        if weight > 0.0:
            p0_out.append(RangeCombo(combo.hole, weight))

    for j, combo in enumerate(state.p1_range):
        if river_card in combo.hole:
            continue
        after_key = (1, TURN_P1_AFTER_CHECK, j)
        after_actions = actions_for_infoset(spec, after_key)
        after = policy[after_key]
        if history == "CHECK_CHECK":
            reach = after[after_actions.index("CHECK")]
        elif history.startswith("P0_BET_"):
            amount = _history_turn_bet(spec, history)
            response_key = (1, turn_p1_vs_bet_node(amount), j)
            response_actions = actions_for_infoset(spec, response_key)
            reach = policy[response_key][response_actions.index("CALL")]
        else:
            amount = _history_turn_bet(spec, history)
            reach = after[after_actions.index(f"BET_{amount}")]
        weight = float(combo.weight) * reach
        if weight > 0.0:
            p1_out.append(RangeCombo(combo.hole, weight))

    if not p0_out or not p1_out:
        raise ValueError("public turn history has zero posterior range mass")
    return tuple(p0_out), tuple(p1_out)


def turn_river_solver_result(
    spec: TurnRiverGameSpec,
    state: TurnRiverSolverState,
) -> TurnRiverSolveResult:
    state.validate(spec)
    if state.iterations <= 0:
        raise ValueError("cannot evaluate an untrained turn+river solver")
    policy = normalize_policy(spec, state.strategy_sum, state.regrets)
    policy_ev = evaluate_turn_river_policy(spec, policy)
    infosets = all_infosets(spec)
    return TurnRiverSolveResult(
        iterations=state.iterations,
        policy=policy,
        policy_ev=policy_ev,
        infosets=len(infosets),
        action_slots=sum(len(actions_for_infoset(spec, key)) for key in infosets),
    )
