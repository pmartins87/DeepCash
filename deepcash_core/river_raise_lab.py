from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Mapping, Sequence

from .cards import require_distinct
from .evaluator import evaluate_best
from .river_lab import RangeCombo, RiverSolveResult

ROOT = "ROOT"
P1_AFTER_CHECK = "P1_AFTER_CHECK"


def p1_vs_bet_node(bet: int) -> str:
    return f"P1_VS_BET_{bet}"


def p0_vs_bet_node(bet: int) -> str:
    return f"P0_VS_BET_{bet}"


def p0_vs_p1_raise_node(bet: int, raise_to: int) -> str:
    return f"P0_VS_P1_RAISE_{bet}_{raise_to}"


def p1_vs_p0_raise_node(bet: int, raise_to: int) -> str:
    return f"P1_VS_P0_RAISE_{bet}_{raise_to}"


@dataclass(frozen=True)
class RiverRaiseGameSpec:
    """Exact HU river lab with at most one raise after the first bet.

    `raise_targets` maps each opening bet size to exact total river contribution
    targets. Example: `((50, (150,)),)` means an opening bet of 50 can be raised
    to 150 total. Targets are explicit integer chips; the production action
    abstraction will later derive/legalize them from pot/stack geometry.
    """

    board: tuple[int, int, int, int, int]
    p0_range: tuple[RangeCombo, ...]
    p1_range: tuple[RangeCombo, ...]
    pot: int
    bet_sizes: tuple[int, ...]
    raise_targets: tuple[tuple[int, tuple[int, ...]], ...]

    def __post_init__(self) -> None:
        board = require_distinct(self.board)
        if len(board) != 5:
            raise ValueError("river game requires exactly five board cards")
        if self.pot <= 0:
            raise ValueError("pot must be positive")
        if not self.p0_range or not self.p1_range:
            raise ValueError("both ranges must be non-empty")
        if not self.bet_sizes or tuple(sorted(set(self.bet_sizes))) != self.bet_sizes:
            raise ValueError("bet sizes must be non-empty, sorted and unique")
        if any(b <= 0 for b in self.bet_sizes):
            raise ValueError("bet sizes must be positive")

        mapping = dict(self.raise_targets)
        if len(mapping) != len(self.raise_targets) or set(mapping) != set(self.bet_sizes):
            raise ValueError("raise_targets must cover every opening bet exactly once")
        for bet, targets in self.raise_targets:
            if not targets or tuple(sorted(set(targets))) != targets:
                raise ValueError("raise targets must be non-empty, sorted and unique")
            if any(target <= bet for target in targets):
                raise ValueError("raise target must exceed the faced opening bet")

        board_set = set(board)
        for combo in (*self.p0_range, *self.p1_range):
            if board_set.intersection(combo.hole):
                raise ValueError("range combo overlaps board")
        if not valid_deals(self):
            raise ValueError("ranges contain no compatible private-card deals")

    def targets_for(self, bet: int) -> tuple[int, ...]:
        return dict(self.raise_targets)[bet]


def compatible(a: RangeCombo, b: RangeCombo) -> bool:
    return not set(a.hole).intersection(b.hole)


def valid_deals(spec: RiverRaiseGameSpec) -> tuple[tuple[int, int, float], ...]:
    out = []
    for i, a in enumerate(spec.p0_range):
        for j, b in enumerate(spec.p1_range):
            if compatible(a, b):
                out.append((i, j, float(a.weight) * float(b.weight)))
    return tuple(out)


def showdown_sign(spec: RiverRaiseGameSpec, i: int, j: int) -> int:
    v0 = evaluate_best((*spec.p0_range[i].hole, *spec.board))
    v1 = evaluate_best((*spec.p1_range[j].hole, *spec.board))
    return int(v0 > v1) - int(v0 < v1)


def showdown_value(spec: RiverRaiseGameSpec, i: int, j: int, matched: int = 0) -> float:
    return float(showdown_sign(spec, i, j)) * (float(spec.pot) / 2.0 + float(matched))


def bet_amount(action: str) -> int:
    if not action.startswith("BET_"):
        raise ValueError(action)
    return int(action.split("_", 1)[1])


def raise_amount(action: str) -> int:
    if not action.startswith("RAISE_TO_"):
        raise ValueError(action)
    return int(action.split("RAISE_TO_", 1)[1])


def parse_final_raise_node(node: str) -> tuple[int, int]:
    parts = node.split("_")
    # P0_VS_P1_RAISE_<bet>_<raise> / P1_VS_P0_RAISE_<bet>_<raise>
    return int(parts[-2]), int(parts[-1])


def actions(spec: RiverRaiseGameSpec, player: int, node: str) -> tuple[str, ...]:
    opening = tuple(f"BET_{b}" for b in spec.bet_sizes)
    if player == 0 and node == ROOT:
        return ("CHECK", *opening)
    if player == 1 and node == P1_AFTER_CHECK:
        return ("CHECK", *opening)
    if player == 1 and node.startswith("P1_VS_BET_"):
        bet = int(node.rsplit("_", 1)[1])
        return ("FOLD", "CALL", *(f"RAISE_TO_{r}" for r in spec.targets_for(bet)))
    if player == 0 and node.startswith("P0_VS_BET_"):
        bet = int(node.rsplit("_", 1)[1])
        return ("FOLD", "CALL", *(f"RAISE_TO_{r}" for r in spec.targets_for(bet)))
    if player == 0 and node.startswith("P0_VS_P1_RAISE_"):
        return ("FOLD", "CALL")
    if player == 1 and node.startswith("P1_VS_P0_RAISE_"):
        return ("FOLD", "CALL")
    raise ValueError(f"unknown infoset node: player={player} node={node}")


def all_infosets(spec: RiverRaiseGameSpec) -> tuple[tuple[int, str, int], ...]:
    keys: list[tuple[int, str, int]] = []
    for i in range(len(spec.p0_range)):
        keys.append((0, ROOT, i))
        for bet in spec.bet_sizes:
            keys.append((0, p0_vs_bet_node(bet), i))
            for target in spec.targets_for(bet):
                keys.append((0, p0_vs_p1_raise_node(bet, target), i))
    for j in range(len(spec.p1_range)):
        keys.append((1, P1_AFTER_CHECK, j))
        for bet in spec.bet_sizes:
            keys.append((1, p1_vs_bet_node(bet), j))
            for target in spec.targets_for(bet):
                keys.append((1, p1_vs_p0_raise_node(bet, target), j))
    return tuple(keys)


def regret_strategy(regrets: Sequence[float]) -> tuple[float, ...]:
    positive = [max(0.0, r) for r in regrets]
    total = sum(positive)
    if total <= 0.0:
        return tuple(1.0 / len(regrets) for _ in regrets)
    return tuple(r / total for r in positive)


def traverse_cfr(
    spec: RiverRaiseGameSpec,
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
    acts = actions(spec, player, node)
    sigma = strategies[key]
    values: list[float] = []

    for a_idx, action in enumerate(acts):
        if player == 0 and node == ROOT:
            if action == "CHECK":
                value = traverse_cfr(
                    spec, i=i, j=j, chance=chance, strategies=strategies,
                    regret_delta=regret_delta, strategy_delta=strategy_delta,
                    average_weight=average_weight, node=P1_AFTER_CHECK, player=1,
                    reach0=reach0 * sigma[a_idx], reach1=reach1,
                )
            else:
                bet = bet_amount(action)
                value = traverse_cfr(
                    spec, i=i, j=j, chance=chance, strategies=strategies,
                    regret_delta=regret_delta, strategy_delta=strategy_delta,
                    average_weight=average_weight, node=p1_vs_bet_node(bet), player=1,
                    reach0=reach0 * sigma[a_idx], reach1=reach1,
                )
        elif player == 1 and node == P1_AFTER_CHECK:
            if action == "CHECK":
                value = showdown_value(spec, i, j)
            else:
                bet = bet_amount(action)
                value = traverse_cfr(
                    spec, i=i, j=j, chance=chance, strategies=strategies,
                    regret_delta=regret_delta, strategy_delta=strategy_delta,
                    average_weight=average_weight, node=p0_vs_bet_node(bet), player=0,
                    reach0=reach0, reach1=reach1 * sigma[a_idx],
                )
        elif player == 1 and node.startswith("P1_VS_BET_"):
            bet = int(node.rsplit("_", 1)[1])
            if action == "FOLD":
                value = float(spec.pot) / 2.0
            elif action == "CALL":
                value = showdown_value(spec, i, j, bet)
            else:
                target = raise_amount(action)
                value = traverse_cfr(
                    spec, i=i, j=j, chance=chance, strategies=strategies,
                    regret_delta=regret_delta, strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    node=p0_vs_p1_raise_node(bet, target), player=0,
                    reach0=reach0, reach1=reach1 * sigma[a_idx],
                )
        elif player == 0 and node.startswith("P0_VS_BET_"):
            bet = int(node.rsplit("_", 1)[1])
            if action == "FOLD":
                value = -float(spec.pot) / 2.0
            elif action == "CALL":
                value = showdown_value(spec, i, j, bet)
            else:
                target = raise_amount(action)
                value = traverse_cfr(
                    spec, i=i, j=j, chance=chance, strategies=strategies,
                    regret_delta=regret_delta, strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    node=p1_vs_p0_raise_node(bet, target), player=1,
                    reach0=reach0 * sigma[a_idx], reach1=reach1,
                )
        elif player == 0 and node.startswith("P0_VS_P1_RAISE_"):
            bet, target = parse_final_raise_node(node)
            value = -(float(spec.pot) / 2.0 + float(bet)) if action == "FOLD" else showdown_value(spec, i, j, target)
        elif player == 1 and node.startswith("P1_VS_P0_RAISE_"):
            bet, target = parse_final_raise_node(node)
            value = (float(spec.pot) / 2.0 + float(bet)) if action == "FOLD" else showdown_value(spec, i, j, target)
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


def normalize_policy(
    spec: RiverRaiseGameSpec,
    strategy_sum: Mapping[tuple[int, str, int], Sequence[float]],
    regrets: Mapping[tuple[int, str, int], Sequence[float]],
) -> dict[tuple[int, str, int], tuple[float, ...]]:
    out = {}
    for key in all_infosets(spec):
        vals = strategy_sum[key]
        total = sum(vals)
        out[key] = tuple(v / total for v in vals) if total > 0 else regret_strategy(regrets[key])
    return out


def deal_value(
    spec: RiverRaiseGameSpec,
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
            if action == "CHECK":
                value = deal_value(spec, i, j, policy, deterministic_player=deterministic_player, deterministic_plan=deterministic_plan, node=P1_AFTER_CHECK, player=1)
            else:
                value = deal_value(spec, i, j, policy, deterministic_player=deterministic_player, deterministic_plan=deterministic_plan, node=p1_vs_bet_node(bet_amount(action)), player=1)
        elif player == 1 and node == P1_AFTER_CHECK:
            if action == "CHECK":
                value = showdown_value(spec, i, j)
            else:
                value = deal_value(spec, i, j, policy, deterministic_player=deterministic_player, deterministic_plan=deterministic_plan, node=p0_vs_bet_node(bet_amount(action)), player=0)
        elif player == 1 and node.startswith("P1_VS_BET_"):
            bet = int(node.rsplit("_", 1)[1])
            if action == "FOLD":
                value = float(spec.pot) / 2.0
            elif action == "CALL":
                value = showdown_value(spec, i, j, bet)
            else:
                value = deal_value(spec, i, j, policy, deterministic_player=deterministic_player, deterministic_plan=deterministic_plan, node=p0_vs_p1_raise_node(bet, raise_amount(action)), player=0)
        elif player == 0 and node.startswith("P0_VS_BET_"):
            bet = int(node.rsplit("_", 1)[1])
            if action == "FOLD":
                value = -float(spec.pot) / 2.0
            elif action == "CALL":
                value = showdown_value(spec, i, j, bet)
            else:
                value = deal_value(spec, i, j, policy, deterministic_player=deterministic_player, deterministic_plan=deterministic_plan, node=p1_vs_p0_raise_node(bet, raise_amount(action)), player=1)
        elif player == 0 and node.startswith("P0_VS_P1_RAISE_"):
            bet, target = parse_final_raise_node(node)
            value = -(float(spec.pot) / 2.0 + float(bet)) if action == "FOLD" else showdown_value(spec, i, j, target)
        elif player == 1 and node.startswith("P1_VS_P0_RAISE_"):
            bet, target = parse_final_raise_node(node)
            value = (float(spec.pot) / 2.0 + float(bet)) if action == "FOLD" else showdown_value(spec, i, j, target)
        else:  # pragma: no cover
            raise AssertionError((player, node, action))
        values.append(value)
    return sum(p * v for p, v in zip(sigma, values))


def evaluate_policy(spec: RiverRaiseGameSpec, policy: Mapping[tuple[int, str, int], tuple[float, ...]]) -> float:
    deals = valid_deals(spec)
    total = sum(w for _, _, w in deals)
    return sum(w * deal_value(spec, i, j, policy) for i, j, w in deals) / total


def pure_plans_for_hand(spec: RiverRaiseGameSpec, player: int, hand_idx: int):
    keys = [k for k in all_infosets(spec) if k[0] == player and k[2] == hand_idx]
    action_ranges = [range(len(actions(spec, key[0], key[1]))) for key in keys]
    for choices in product(*action_ranges):
        yield dict(zip(keys, choices))


def exact_best_response_values(
    spec: RiverRaiseGameSpec,
    policy: Mapping[tuple[int, str, int], tuple[float, ...]],
) -> tuple[float, float]:
    deals = valid_deals(spec)
    total = sum(w for _, _, w in deals)

    br0_num = 0.0
    for i in range(len(spec.p0_range)):
        compatible_deals = [(j, w) for ii, j, w in deals if ii == i]
        if not compatible_deals:
            continue
        best = max(
            sum(w * deal_value(spec, i, j, policy, deterministic_player=0, deterministic_plan=plan) for j, w in compatible_deals)
            for plan in pure_plans_for_hand(spec, 0, i)
        )
        br0_num += best

    br1_num = 0.0
    for j in range(len(spec.p1_range)):
        compatible_deals = [(i, w) for i, jj, w in deals if jj == j]
        if not compatible_deals:
            continue
        best_for_p1 = min(
            sum(w * deal_value(spec, i, j, policy, deterministic_player=1, deterministic_plan=plan) for i, w in compatible_deals)
            for plan in pure_plans_for_hand(spec, 1, j)
        )
        br1_num += best_for_p1

    return br0_num / total, br1_num / total


def solve_river_raise_cfr_plus(spec: RiverRaiseGameSpec, *, iterations: int = 1_000) -> RiverSolveResult:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    infosets = all_infosets(spec)
    regrets = {k: [0.0] * len(actions(spec, k[0], k[1])) for k in infosets}
    strategy_sum = {k: [0.0] * len(actions(spec, k[0], k[1])) for k in infosets}
    deals = valid_deals(spec)
    total_chance = sum(w for _, _, w in deals)

    for iteration in range(1, iterations + 1):
        strategies = {k: regret_strategy(regrets[k]) for k in infosets}
        regret_delta = {k: [0.0] * len(regrets[k]) for k in infosets}
        strategy_delta = {k: [0.0] * len(regrets[k]) for k in infosets}
        for i, j, raw_weight in deals:
            traverse_cfr(
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
            for a_idx in range(len(regrets[key])):
                regrets[key][a_idx] = max(0.0, regrets[key][a_idx] + regret_delta[key][a_idx])
                strategy_sum[key][a_idx] += strategy_delta[key][a_idx]

    policy = normalize_policy(spec, strategy_sum, regrets)
    policy_ev = evaluate_policy(spec, policy)
    br0, br1 = exact_best_response_values(spec, policy)
    exploitability = max(0.0, (br0 - br1) / 2.0)
    slots = sum(len(actions(spec, k[0], k[1])) for k in infosets)
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
