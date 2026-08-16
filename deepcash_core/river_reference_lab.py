from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Mapping, Sequence

from .cards import require_distinct
from .evaluator import evaluate_best
from .river_lab import RangeCombo, RiverSolveResult

ROOT = "ROOT"
P1_AFTER_CHECK = "P1_AFTER_CHECK"


def p1_vs_p0_bet_node(amount: int) -> str:
    return f"P1_VS_P0_BET_{amount}"


def p0_vs_p1_bet_node(amount: int) -> str:
    return f"P0_VS_P1_BET_{amount}"


@dataclass(frozen=True)
class AsymmetricRiverGameSpec:
    """One-bet HU river game with independent action sets for each player.

    This is the reference-game control needed for action-abstraction research.
    Comparing exploitability inside two different restricted games is not a
    valid estimate of the strategic cost of the restriction.  Instead we can
    keep one player on a rich reference action set while restricting only the
    other player, solve both games, and bound the value lost by that restriction.
    """

    board: tuple[int, int, int, int, int]
    p0_range: tuple[RangeCombo, ...]
    p1_range: tuple[RangeCombo, ...]
    pot: int
    p0_bet_sizes: tuple[int, ...]
    p1_bet_sizes: tuple[int, ...]

    def __post_init__(self) -> None:
        board = require_distinct(self.board)
        if len(board) != 5:
            raise ValueError("river game requires exactly five board cards")
        if self.pot <= 0:
            raise ValueError("pot must be positive")
        if not self.p0_range or not self.p1_range:
            raise ValueError("both ranges must be non-empty")
        for name, sizes in (("p0", self.p0_bet_sizes), ("p1", self.p1_bet_sizes)):
            if not sizes or tuple(sorted(set(sizes))) != sizes or any(b <= 0 for b in sizes):
                raise ValueError(f"{name} bet sizes must be positive, sorted and unique")
        board_set = set(board)
        for combo in (*self.p0_range, *self.p1_range):
            if board_set.intersection(combo.hole):
                raise ValueError("range combo overlaps board")
        if not valid_deals(self):
            raise ValueError("ranges contain no compatible private-card deals")


@dataclass(frozen=True)
class RestrictionLossResult:
    reference_sizes: tuple[int, ...]
    candidate_sizes: tuple[int, ...]
    reference: RiverSolveResult
    p0_restricted: RiverSolveResult
    p1_restricted: RiverSolveResult
    p0_loss_lower: float
    p0_loss_upper: float
    p1_loss_lower: float
    p1_loss_upper: float
    worst_loss_upper: float
    worst_loss_upper_per_pot: float


def valid_deals(spec: AsymmetricRiverGameSpec) -> tuple[tuple[int, int, float], ...]:
    out = []
    for i, a in enumerate(spec.p0_range):
        for j, b in enumerate(spec.p1_range):
            if not set(a.hole).intersection(b.hole):
                out.append((i, j, float(a.weight) * float(b.weight)))
    return tuple(out)


def showdown_value(spec: AsymmetricRiverGameSpec, i: int, j: int, matched: int = 0) -> float:
    v0 = evaluate_best((*spec.p0_range[i].hole, *spec.board))
    v1 = evaluate_best((*spec.p1_range[j].hole, *spec.board))
    sign = int(v0 > v1) - int(v0 < v1)
    return float(sign) * (float(spec.pot) / 2.0 + float(matched))


def bet_amount(action: str) -> int:
    if not action.startswith("BET_"):
        raise ValueError(action)
    return int(action.split("_", 1)[1])


def actions(spec: AsymmetricRiverGameSpec, player: int, node: str) -> tuple[str, ...]:
    if player == 0 and node == ROOT:
        return ("CHECK", *(f"BET_{b}" for b in spec.p0_bet_sizes))
    if player == 1 and node == P1_AFTER_CHECK:
        return ("CHECK", *(f"BET_{b}" for b in spec.p1_bet_sizes))
    if player == 1 and node.startswith("P1_VS_P0_BET_"):
        return ("FOLD", "CALL")
    if player == 0 and node.startswith("P0_VS_P1_BET_"):
        return ("FOLD", "CALL")
    raise ValueError(f"unknown infoset: player={player} node={node}")


def all_infosets(spec: AsymmetricRiverGameSpec) -> tuple[tuple[int, str, int], ...]:
    keys = []
    for i in range(len(spec.p0_range)):
        keys.append((0, ROOT, i))
        keys.extend((0, p0_vs_p1_bet_node(b), i) for b in spec.p1_bet_sizes)
    for j in range(len(spec.p1_range)):
        keys.append((1, P1_AFTER_CHECK, j))
        keys.extend((1, p1_vs_p0_bet_node(b), j) for b in spec.p0_bet_sizes)
    return tuple(keys)


def regret_strategy(regrets: Sequence[float]) -> tuple[float, ...]:
    positive = [max(0.0, r) for r in regrets]
    total = sum(positive)
    if total <= 0:
        return tuple(1.0 / len(regrets) for _ in regrets)
    return tuple(r / total for r in positive)


def traverse_cfr(
    spec: AsymmetricRiverGameSpec,
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
    key = (player, node, i if player == 0 else j)
    acts = actions(spec, player, node)
    sigma = strategies[key]
    values = []
    for a_idx, action in enumerate(acts):
        if player == 0 and node == ROOT:
            if action == "CHECK":
                value = traverse_cfr(spec, i=i, j=j, chance=chance, strategies=strategies, regret_delta=regret_delta, strategy_delta=strategy_delta, average_weight=average_weight, node=P1_AFTER_CHECK, player=1, reach0=reach0 * sigma[a_idx], reach1=reach1)
            else:
                value = traverse_cfr(spec, i=i, j=j, chance=chance, strategies=strategies, regret_delta=regret_delta, strategy_delta=strategy_delta, average_weight=average_weight, node=p1_vs_p0_bet_node(bet_amount(action)), player=1, reach0=reach0 * sigma[a_idx], reach1=reach1)
        elif player == 1 and node == P1_AFTER_CHECK:
            if action == "CHECK":
                value = showdown_value(spec, i, j)
            else:
                value = traverse_cfr(spec, i=i, j=j, chance=chance, strategies=strategies, regret_delta=regret_delta, strategy_delta=strategy_delta, average_weight=average_weight, node=p0_vs_p1_bet_node(bet_amount(action)), player=0, reach0=reach0, reach1=reach1 * sigma[a_idx])
        elif player == 1 and node.startswith("P1_VS_P0_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            value = float(spec.pot) / 2.0 if action == "FOLD" else showdown_value(spec, i, j, amount)
        elif player == 0 and node.startswith("P0_VS_P1_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            value = -float(spec.pot) / 2.0 if action == "FOLD" else showdown_value(spec, i, j, amount)
        else:  # pragma: no cover
            raise AssertionError((player, node, action))
        values.append(value)

    node_value = sum(p * v for p, v in zip(sigma, values))
    if player == 0:
        cf_reach = chance * reach1
        for a_idx, value in enumerate(values):
            regret_delta[key][a_idx] += cf_reach * (value - node_value)
        avg_reach = chance * reach0
    else:
        cf_reach = chance * reach0
        for a_idx, value in enumerate(values):
            regret_delta[key][a_idx] += cf_reach * (node_value - value)
        avg_reach = chance * reach1
    for a_idx, prob in enumerate(sigma):
        strategy_delta[key][a_idx] += average_weight * avg_reach * prob
    return node_value


def normalize_policy(spec, strategy_sum, regrets):
    out = {}
    for key in all_infosets(spec):
        vals = strategy_sum[key]
        total = sum(vals)
        out[key] = tuple(v / total for v in vals) if total > 0 else regret_strategy(regrets[key])
    return out


def deal_value(spec, i, j, policy, *, deterministic_player=None, deterministic_plan=None, node=ROOT, player=0):
    key = (player, node, i if player == 0 else j)
    acts = actions(spec, player, node)
    if deterministic_player == player:
        assert deterministic_plan is not None
        selected = deterministic_plan[key]
        sigma = tuple(1.0 if k == selected else 0.0 for k in range(len(acts)))
    else:
        sigma = policy[key]
    values = []
    for action in acts:
        if player == 0 and node == ROOT:
            value = deal_value(spec, i, j, policy, deterministic_player=deterministic_player, deterministic_plan=deterministic_plan, node=P1_AFTER_CHECK, player=1) if action == "CHECK" else deal_value(spec, i, j, policy, deterministic_player=deterministic_player, deterministic_plan=deterministic_plan, node=p1_vs_p0_bet_node(bet_amount(action)), player=1)
        elif player == 1 and node == P1_AFTER_CHECK:
            value = showdown_value(spec, i, j) if action == "CHECK" else deal_value(spec, i, j, policy, deterministic_player=deterministic_player, deterministic_plan=deterministic_plan, node=p0_vs_p1_bet_node(bet_amount(action)), player=0)
        elif player == 1 and node.startswith("P1_VS_P0_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            value = float(spec.pot) / 2.0 if action == "FOLD" else showdown_value(spec, i, j, amount)
        elif player == 0 and node.startswith("P0_VS_P1_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            value = -float(spec.pot) / 2.0 if action == "FOLD" else showdown_value(spec, i, j, amount)
        else:  # pragma: no cover
            raise AssertionError((player, node, action))
        values.append(value)
    return sum(p * v for p, v in zip(sigma, values))


def pure_plans_for_hand(spec, player: int, hand_idx: int):
    keys = [k for k in all_infosets(spec) if k[0] == player and k[2] == hand_idx]
    ranges = [range(len(actions(spec, k[0], k[1]))) for k in keys]
    for choices in product(*ranges):
        yield dict(zip(keys, choices))


def exact_best_response_values(spec, policy) -> tuple[float, float]:
    deals = valid_deals(spec)
    total = sum(w for _, _, w in deals)
    br0 = 0.0
    for i in range(len(spec.p0_range)):
        ds = [(j, w) for ii, j, w in deals if ii == i]
        if ds:
            br0 += max(sum(w * deal_value(spec, i, j, policy, deterministic_player=0, deterministic_plan=plan) for j, w in ds) for plan in pure_plans_for_hand(spec, 0, i))
    br1 = 0.0
    for j in range(len(spec.p1_range)):
        ds = [(i, w) for i, jj, w in deals if jj == j]
        if ds:
            br1 += min(sum(w * deal_value(spec, i, j, policy, deterministic_player=1, deterministic_plan=plan) for i, w in ds) for plan in pure_plans_for_hand(spec, 1, j))
    return br0 / total, br1 / total


def solve_asymmetric_river_cfr_plus(spec: AsymmetricRiverGameSpec, *, iterations: int = 1000) -> RiverSolveResult:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    infosets = all_infosets(spec)
    regrets = {k: [0.0] * len(actions(spec, k[0], k[1])) for k in infosets}
    strategy_sum = {k: [0.0] * len(actions(spec, k[0], k[1])) for k in infosets}
    deals = valid_deals(spec)
    total_chance = sum(w for _, _, w in deals)
    for iteration in range(1, iterations + 1):
        strategies = {k: regret_strategy(regrets[k]) for k in infosets}
        rd = {k: [0.0] * len(regrets[k]) for k in infosets}
        sd = {k: [0.0] * len(regrets[k]) for k in infosets}
        for i, j, raw_weight in deals:
            traverse_cfr(spec, i=i, j=j, chance=raw_weight / total_chance, strategies=strategies, regret_delta=rd, strategy_delta=sd, average_weight=float(iteration))
        for key in infosets:
            for a_idx in range(len(regrets[key])):
                regrets[key][a_idx] = max(0.0, regrets[key][a_idx] + rd[key][a_idx])
                strategy_sum[key][a_idx] += sd[key][a_idx]
    policy = normalize_policy(spec, strategy_sum, regrets)
    deals = valid_deals(spec)
    total = sum(w for _, _, w in deals)
    policy_ev = sum(w * deal_value(spec, i, j, policy) for i, j, w in deals) / total
    br0, br1 = exact_best_response_values(spec, policy)
    exploitability = max(0.0, (br0 - br1) / 2.0)
    slots = sum(len(actions(spec, k[0], k[1])) for k in infosets)
    return RiverSolveResult(iterations, policy, policy_ev, br0, br1, exploitability, exploitability / float(spec.pot), len(infosets), slots)


def evaluate_restriction_loss(
    *,
    board: tuple[int, int, int, int, int],
    p0_range: tuple[RangeCombo, ...],
    p1_range: tuple[RangeCombo, ...],
    pot: int,
    reference_sizes: tuple[int, ...],
    candidate_sizes: tuple[int, ...],
    iterations: int,
) -> RestrictionLossResult:
    if not set(candidate_sizes).issubset(reference_sizes):
        raise ValueError("candidate sizes must be a subset of the reference action set")
    ref = solve_asymmetric_river_cfr_plus(AsymmetricRiverGameSpec(board, p0_range, p1_range, pot, reference_sizes, reference_sizes), iterations=iterations)
    p0r = solve_asymmetric_river_cfr_plus(AsymmetricRiverGameSpec(board, p0_range, p1_range, pot, candidate_sizes, reference_sizes), iterations=iterations)
    p1r = solve_asymmetric_river_cfr_plus(AsymmetricRiverGameSpec(board, p0_range, p1_range, pot, reference_sizes, candidate_sizes), iterations=iterations)

    # Each solved zero-sum game has true value V in [br1_value, br0_value].
    # Therefore the strategic value lost by restricting only P0 is bounded by
    # [Vref_low - Vp0_high, Vref_high - Vp0_low]. Restricting P1 is measured
    # symmetrically as [Vp1_low - Vref_high, Vp1_high - Vref_low].
    p0_lower = ref.br1_value - p0r.br0_value
    p0_upper = ref.br0_value - p0r.br1_value
    p1_lower = p1r.br1_value - ref.br0_value
    p1_upper = p1r.br0_value - ref.br1_value
    worst_upper = max(0.0, p0_upper, p1_upper)
    return RestrictionLossResult(
        reference_sizes=reference_sizes,
        candidate_sizes=candidate_sizes,
        reference=ref,
        p0_restricted=p0r,
        p1_restricted=p1r,
        p0_loss_lower=p0_lower,
        p0_loss_upper=p0_upper,
        p1_loss_lower=p1_lower,
        p1_loss_upper=p1_upper,
        worst_loss_upper=worst_upper,
        worst_loss_upper_per_pot=worst_upper / float(pot),
    )
