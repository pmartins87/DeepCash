from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from math import ceil, floor
from typing import Iterable, Mapping, Sequence

from .cards import require_distinct
from .evaluator import evaluate_best


@dataclass(frozen=True)
class RangeCombo:
    hole: tuple[int, int]
    weight: float = 1.0

    def __post_init__(self) -> None:
        cards = require_distinct(self.hole)
        if len(cards) != 2:
            raise ValueError("range combo requires exactly two cards")
        if self.weight <= 0:
            raise ValueError("range weight must be positive")


@dataclass(frozen=True)
class RiverGameSpec:
    """Small exact HU river game used to audit action abstractions.

    Player 0 acts first. Both players may make at most one bet; the response is
    fold/call. This deliberately tractable tree admits exact best response by
    pure-plan enumeration and is a laboratory, not the production blueprint.
    """

    board: tuple[int, int, int, int, int]
    p0_range: tuple[RangeCombo, ...]
    p1_range: tuple[RangeCombo, ...]
    pot: int
    bet_sizes: tuple[int, ...]

    def __post_init__(self) -> None:
        board = require_distinct(self.board)
        if len(board) != 5:
            raise ValueError("river game requires exactly five board cards")
        if self.pot <= 0:
            raise ValueError("pot must be positive")
        if not self.p0_range or not self.p1_range:
            raise ValueError("both ranges must be non-empty")
        if not self.bet_sizes or any(b <= 0 for b in self.bet_sizes):
            raise ValueError("bet sizes must be positive and non-empty")
        if tuple(sorted(set(self.bet_sizes))) != self.bet_sizes:
            raise ValueError("bet sizes must be sorted and unique")
        board_set = set(board)
        for combo in (*self.p0_range, *self.p1_range):
            if board_set.intersection(combo.hole):
                raise ValueError("range combo overlaps board")
        if not _valid_deals(self):
            raise ValueError("ranges contain no compatible private-card deals")


@dataclass(frozen=True)
class RiverSolveResult:
    iterations: int
    policy: Mapping[tuple[int, str, int], tuple[float, ...]]
    policy_ev: float
    br0_value: float
    br1_value: float
    exploitability: float
    exploitability_per_pot: float
    infosets: int
    action_slots: int


ROOT = "ROOT"
P1_AFTER_CHECK = "P1_AFTER_CHECK"


def p1_vs_bet_node(amount: int) -> str:
    return f"P1_VS_BET_{amount}"


def p0_vs_bet_node(amount: int) -> str:
    return f"P0_VS_BET_{amount}"


def materialize_bet_sizes(
    *,
    pot: int,
    stack: int,
    min_bet: int,
    fractions: Sequence[Fraction | float],
) -> tuple[int, ...]:
    """Convert candidate pot fractions to exact integer-chip bet sizes.

    This is only a laboratory action generator. It rounds half-up to the chip
    unit, clips to [min_bet, stack], de-duplicates, and always retains an
    explicitly requested all-in when a fraction materializes at/above stack.
    """
    if pot <= 0 or stack <= 0 or min_bet <= 0:
        raise ValueError("pot/stack/min_bet must be positive")
    if min_bet > stack:
        return (stack,)
    out: set[int] = set()
    for frac in fractions:
        f = Fraction(frac)
        if f <= 0:
            raise ValueError("bet fractions must be positive")
        exact = Fraction(pot) * f
        q, r = divmod(exact.numerator, exact.denominator)
        rounded = q + int(2 * r >= exact.denominator)
        out.add(min(stack, max(min_bet, rounded)))
    if not out:
        raise ValueError("no bet sizes materialized")
    return tuple(sorted(out))


def _compatible(a: RangeCombo, b: RangeCombo) -> bool:
    return not set(a.hole).intersection(b.hole)


def _valid_deals(spec: RiverGameSpec) -> tuple[tuple[int, int, float], ...]:
    deals = []
    for i, a in enumerate(spec.p0_range):
        for j, b in enumerate(spec.p1_range):
            if _compatible(a, b):
                deals.append((i, j, float(a.weight) * float(b.weight)))
    return tuple(deals)


def _showdown_sign(spec: RiverGameSpec, i: int, j: int) -> int:
    v0 = evaluate_best((*spec.p0_range[i].hole, *spec.board))
    v1 = evaluate_best((*spec.p1_range[j].hole, *spec.board))
    return int(v0 > v1) - int(v0 < v1)


def _actions(spec: RiverGameSpec, player: int, node: str) -> tuple[str, ...]:
    bets = tuple(f"BET_{b}" for b in spec.bet_sizes)
    if player == 0 and node == ROOT:
        return ("CHECK", *bets)
    if player == 1 and node == P1_AFTER_CHECK:
        return ("CHECK", *bets)
    if (player == 1 and node.startswith("P1_VS_BET_")) or (
        player == 0 and node.startswith("P0_VS_BET_")
    ):
        return ("FOLD", "CALL")
    raise ValueError(f"unknown infoset node: player={player} node={node}")


def _all_infosets(spec: RiverGameSpec) -> tuple[tuple[int, str, int], ...]:
    keys: list[tuple[int, str, int]] = []
    for i in range(len(spec.p0_range)):
        keys.append((0, ROOT, i))
        for b in spec.bet_sizes:
            keys.append((0, p0_vs_bet_node(b), i))
    for j in range(len(spec.p1_range)):
        keys.append((1, P1_AFTER_CHECK, j))
        for b in spec.bet_sizes:
            keys.append((1, p1_vs_bet_node(b), j))
    return tuple(keys)


def _regret_strategy(regrets: Sequence[float]) -> tuple[float, ...]:
    positive = [max(0.0, r) for r in regrets]
    total = sum(positive)
    if total <= 0.0:
        return tuple(1.0 / len(regrets) for _ in regrets)
    return tuple(r / total for r in positive)


def _terminal_showdown(spec: RiverGameSpec, i: int, j: int, matched_bet: int = 0) -> float:
    sign = _showdown_sign(spec, i, j)
    return float(sign) * (float(spec.pot) / 2.0 + float(matched_bet))


def _bet_amount(action: str) -> int:
    if not action.startswith("BET_"):
        raise ValueError(action)
    return int(action.split("_", 1)[1])


def _traverse_cfr(
    spec: RiverGameSpec,
    *,
    i: int,
    j: int,
    chance: float,
    strategies: Mapping[tuple[int, str, int], tuple[float, ...]],
    regret_delta: dict[tuple[int, str, int], list[float]],
    strategy_delta: dict[tuple[int, str, int], list[float]],
    average_weight: float,
    node: str = ROOT,
    player: int = 0,
    reach0: float = 1.0,
    reach1: float = 1.0,
) -> float:
    hand_idx = i if player == 0 else j
    key = (player, node, hand_idx)
    actions = _actions(spec, player, node)
    sigma = strategies[key]
    action_values: list[float] = []

    for action in actions:
        if player == 0 and node == ROOT:
            if action == "CHECK":
                value = _traverse_cfr(
                    spec, i=i, j=j, chance=chance, strategies=strategies,
                    regret_delta=regret_delta, strategy_delta=strategy_delta,
                    average_weight=average_weight, node=P1_AFTER_CHECK, player=1,
                    reach0=reach0 * sigma[actions.index(action)], reach1=reach1,
                )
            else:
                amount = _bet_amount(action)
                value = _traverse_cfr(
                    spec, i=i, j=j, chance=chance, strategies=strategies,
                    regret_delta=regret_delta, strategy_delta=strategy_delta,
                    average_weight=average_weight, node=p1_vs_bet_node(amount), player=1,
                    reach0=reach0 * sigma[actions.index(action)], reach1=reach1,
                )
        elif player == 1 and node == P1_AFTER_CHECK:
            if action == "CHECK":
                value = _terminal_showdown(spec, i, j)
            else:
                amount = _bet_amount(action)
                value = _traverse_cfr(
                    spec, i=i, j=j, chance=chance, strategies=strategies,
                    regret_delta=regret_delta, strategy_delta=strategy_delta,
                    average_weight=average_weight, node=p0_vs_bet_node(amount), player=0,
                    reach0=reach0, reach1=reach1 * sigma[actions.index(action)],
                )
        elif player == 1 and node.startswith("P1_VS_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            value = float(spec.pot) / 2.0 if action == "FOLD" else _terminal_showdown(spec, i, j, amount)
        elif player == 0 and node.startswith("P0_VS_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            value = -float(spec.pot) / 2.0 if action == "FOLD" else _terminal_showdown(spec, i, j, amount)
        else:  # pragma: no cover
            raise AssertionError((player, node, action))
        action_values.append(value)

    node_value = sum(p * v for p, v in zip(sigma, action_values))
    if player == 0:
        cf_reach = chance * reach1
        for a, value in enumerate(action_values):
            regret_delta[key][a] += cf_reach * (value - node_value)
        avg_reach = chance * reach0
    else:
        cf_reach = chance * reach0
        for a, value in enumerate(action_values):
            regret_delta[key][a] += cf_reach * (node_value - value)
        avg_reach = chance * reach1

    for a, prob in enumerate(sigma):
        strategy_delta[key][a] += average_weight * avg_reach * prob
    return node_value


def _normalize_policy(
    spec: RiverGameSpec,
    strategy_sum: Mapping[tuple[int, str, int], Sequence[float]],
    regrets: Mapping[tuple[int, str, int], Sequence[float]],
) -> dict[tuple[int, str, int], tuple[float, ...]]:
    out = {}
    for key in _all_infosets(spec):
        vals = strategy_sum[key]
        total = sum(vals)
        if total > 0:
            out[key] = tuple(v / total for v in vals)
        else:
            out[key] = _regret_strategy(regrets[key])
    return out


def _policy_deal_value(
    spec: RiverGameSpec,
    i: int,
    j: int,
    policy: Mapping[tuple[int, str, int], tuple[float, ...]],
    *,
    deterministic_player: int | None = None,
    deterministic_plan: Mapping[tuple[int, str, int], int] | None = None,
    node: str = ROOT,
    player: int = 0,
) -> float:
    key = (player, node, i if player == 0 else j)
    actions = _actions(spec, player, node)
    if deterministic_player == player:
        assert deterministic_plan is not None
        selected = deterministic_plan[key]
        sigma = tuple(1.0 if k == selected else 0.0 for k in range(len(actions)))
    else:
        sigma = policy[key]

    values = []
    for action in actions:
        if player == 0 and node == ROOT:
            if action == "CHECK":
                value = _policy_deal_value(
                    spec, i, j, policy, deterministic_player=deterministic_player,
                    deterministic_plan=deterministic_plan, node=P1_AFTER_CHECK, player=1,
                )
            else:
                value = _policy_deal_value(
                    spec, i, j, policy, deterministic_player=deterministic_player,
                    deterministic_plan=deterministic_plan,
                    node=p1_vs_bet_node(_bet_amount(action)), player=1,
                )
        elif player == 1 and node == P1_AFTER_CHECK:
            if action == "CHECK":
                value = _terminal_showdown(spec, i, j)
            else:
                value = _policy_deal_value(
                    spec, i, j, policy, deterministic_player=deterministic_player,
                    deterministic_plan=deterministic_plan,
                    node=p0_vs_bet_node(_bet_amount(action)), player=0,
                )
        elif player == 1 and node.startswith("P1_VS_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            value = float(spec.pot) / 2.0 if action == "FOLD" else _terminal_showdown(spec, i, j, amount)
        elif player == 0 and node.startswith("P0_VS_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            value = -float(spec.pot) / 2.0 if action == "FOLD" else _terminal_showdown(spec, i, j, amount)
        else:  # pragma: no cover
            raise AssertionError((player, node, action))
        values.append(value)
    return sum(p * v for p, v in zip(sigma, values))


def evaluate_policy(
    spec: RiverGameSpec,
    policy: Mapping[tuple[int, str, int], tuple[float, ...]],
) -> float:
    deals = _valid_deals(spec)
    total = sum(w for _, _, w in deals)
    return sum(w * _policy_deal_value(spec, i, j, policy) for i, j, w in deals) / total


def _pure_plans_for_hand(spec: RiverGameSpec, player: int, hand_idx: int):
    if player == 0:
        root_key = (0, ROOT, hand_idx)
        response_keys = [(0, p0_vs_bet_node(b), hand_idx) for b in spec.bet_sizes]
        for root_choice in range(len(_actions(spec, 0, ROOT))):
            for responses in product((0, 1), repeat=len(response_keys)):
                plan = {root_key: root_choice}
                plan.update(dict(zip(response_keys, responses)))
                yield plan
    else:
        root_key = (1, P1_AFTER_CHECK, hand_idx)
        response_keys = [(1, p1_vs_bet_node(b), hand_idx) for b in spec.bet_sizes]
        for root_choice in range(len(_actions(spec, 1, P1_AFTER_CHECK))):
            for responses in product((0, 1), repeat=len(response_keys)):
                plan = {root_key: root_choice}
                plan.update(dict(zip(response_keys, responses)))
                yield plan


def exact_best_response_values(
    spec: RiverGameSpec,
    policy: Mapping[tuple[int, str, int], tuple[float, ...]],
) -> tuple[float, float]:
    """Return (P0 best-response value, P0 value vs P1 best response)."""
    deals = _valid_deals(spec)
    total = sum(w for _, _, w in deals)

    br0_numerator = 0.0
    for i in range(len(spec.p0_range)):
        compatible = [(j, w) for ii, j, w in deals if ii == i]
        if not compatible:
            continue
        best = None
        for plan in _pure_plans_for_hand(spec, 0, i):
            value = sum(
                w * _policy_deal_value(
                    spec, i, j, policy, deterministic_player=0, deterministic_plan=plan
                )
                for j, w in compatible
            )
            best = value if best is None else max(best, value)
        assert best is not None
        br0_numerator += best

    br1_numerator = 0.0
    for j in range(len(spec.p1_range)):
        compatible = [(i, w) for i, jj, w in deals if jj == j]
        if not compatible:
            continue
        best_for_p1 = None
        for plan in _pure_plans_for_hand(spec, 1, j):
            p0_value = sum(
                w * _policy_deal_value(
                    spec, i, j, policy, deterministic_player=1, deterministic_plan=plan
                )
                for i, w in compatible
            )
            best_for_p1 = p0_value if best_for_p1 is None else min(best_for_p1, p0_value)
        assert best_for_p1 is not None
        br1_numerator += best_for_p1

    return br0_numerator / total, br1_numerator / total


def solve_river_cfr_plus(spec: RiverGameSpec, *, iterations: int = 2_000) -> RiverSolveResult:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    infosets = _all_infosets(spec)
    regrets = {k: [0.0] * len(_actions(spec, k[0], k[1])) for k in infosets}
    strategy_sum = {k: [0.0] * len(_actions(spec, k[0], k[1])) for k in infosets}
    deals = _valid_deals(spec)
    total_chance = sum(w for _, _, w in deals)

    for iteration in range(1, iterations + 1):
        strategies = {k: _regret_strategy(regrets[k]) for k in infosets}
        regret_delta = {k: [0.0] * len(regrets[k]) for k in infosets}
        strategy_delta = {k: [0.0] * len(regrets[k]) for k in infosets}
        for i, j, raw_weight in deals:
            _traverse_cfr(
                spec,
                i=i,
                j=j,
                chance=raw_weight / total_chance,
                strategies=strategies,
                regret_delta=regret_delta,
                strategy_delta=strategy_delta,
                average_weight=float(iteration),
            )
        for key in infosets:
            for a in range(len(regrets[key])):
                regrets[key][a] = max(0.0, regrets[key][a] + regret_delta[key][a])
                strategy_sum[key][a] += strategy_delta[key][a]

    policy = _normalize_policy(spec, strategy_sum, regrets)
    policy_ev = evaluate_policy(spec, policy)
    br0, br1 = exact_best_response_values(spec, policy)
    exploitability = max(0.0, (br0 - br1) / 2.0)
    slots = sum(len(_actions(spec, k[0], k[1])) for k in infosets)
    return RiverSolveResult(
        iterations=iterations,
        policy=policy,
        policy_ev=policy_ev,
        br0_value=br0,
        br1_value=br1,
        exploitability=exploitability,
        exploitability_per_pot=exploitability / float(spec.pot),
        infosets=len(infosets),
        action_slots=slots,
    )
