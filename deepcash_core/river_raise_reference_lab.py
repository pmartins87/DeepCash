from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Mapping, Sequence

from .cards import require_distinct
from .evaluator import evaluate_best
from .river_lab import RangeCombo, RiverSolveResult

ROOT = "ROOT"
P1_AFTER_CHECK = "P1_AFTER_CHECK"


def p1_vs_p0_bet_node(bet: int) -> str:
    return f"P1_VS_P0_BET_{bet}"


def p0_vs_p1_bet_node(bet: int) -> str:
    return f"P0_VS_P1_BET_{bet}"


def p0_vs_p1_raise_node(bet: int, raise_to: int) -> str:
    return f"P0_VS_P1_RAISE_{bet}_{raise_to}"


def p1_vs_p0_raise_node(bet: int, raise_to: int) -> str:
    return f"P1_VS_P0_RAISE_{bet}_{raise_to}"


@dataclass(frozen=True)
class AsymmetricRiverRaiseGameSpec:
    """HU river one-raise game with independent opening bet sets.

    Raise targets are attached to the *faced reference bet size* and may differ
    by raiser. This lets R3 restrict only one player's opening action set while
    leaving the richer raise-response geometry unchanged, isolating the value of
    omitted opening sizes in a tree where raises actually exist.

    An empty target tuple is meaningful: the faced opening bet is all-in (or
    otherwise leaves no legal raise response), so the responder retains only
    fold/call. This is required for exact low-SPR geometry rather than silently
    deleting all-in opening actions from the reference game.
    """

    board: tuple[int, int, int, int, int]
    p0_range: tuple[RangeCombo, ...]
    p1_range: tuple[RangeCombo, ...]
    pot: int
    p0_bet_sizes: tuple[int, ...]
    p1_bet_sizes: tuple[int, ...]
    p1_raise_targets_vs_p0: tuple[tuple[int, tuple[int, ...]], ...]
    p0_raise_targets_vs_p1: tuple[tuple[int, tuple[int, ...]], ...]

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

        self._validate_raise_map(
            "p1_raise_targets_vs_p0",
            self.p1_raise_targets_vs_p0,
            self.p0_bet_sizes,
        )
        self._validate_raise_map(
            "p0_raise_targets_vs_p1",
            self.p0_raise_targets_vs_p1,
            self.p1_bet_sizes,
        )

        board_set = set(board)
        for combo in (*self.p0_range, *self.p1_range):
            if board_set.intersection(combo.hole):
                raise ValueError("range combo overlaps board")
        if not valid_deals(self):
            raise ValueError("ranges contain no compatible private-card deals")

    @staticmethod
    def _validate_raise_map(
        name: str,
        entries: tuple[tuple[int, tuple[int, ...]], ...],
        faced_sizes: tuple[int, ...],
    ) -> None:
        mapping = dict(entries)
        if len(mapping) != len(entries) or set(mapping) != set(faced_sizes):
            raise ValueError(f"{name} must cover every faced opening bet exactly once")
        for bet, targets in entries:
            # Empty is legal and explicitly represents a faced all-in/no-raise
            # node. Non-empty tuples must remain canonical and strictly above
            # the opening bet.
            if tuple(sorted(set(targets))) != targets:
                raise ValueError(f"{name} targets must be sorted and unique")
            if any(target <= bet for target in targets):
                raise ValueError(f"{name} raise target must exceed faced opening bet")

    def p1_targets(self, p0_bet: int) -> tuple[int, ...]:
        return dict(self.p1_raise_targets_vs_p0)[p0_bet]

    def p0_targets(self, p1_bet: int) -> tuple[int, ...]:
        return dict(self.p0_raise_targets_vs_p1)[p1_bet]


@dataclass(frozen=True)
class OpeningRestrictionWithRaisesResult:
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


def valid_deals(spec: AsymmetricRiverRaiseGameSpec) -> tuple[tuple[int, int, float], ...]:
    out = []
    for i, a in enumerate(spec.p0_range):
        for j, b in enumerate(spec.p1_range):
            if not set(a.hole).intersection(b.hole):
                out.append((i, j, float(a.weight) * float(b.weight)))
    return tuple(out)


def showdown_value(spec: AsymmetricRiverRaiseGameSpec, i: int, j: int, matched: int = 0) -> float:
    v0 = evaluate_best((*spec.p0_range[i].hole, *spec.board))
    v1 = evaluate_best((*spec.p1_range[j].hole, *spec.board))
    sign = int(v0 > v1) - int(v0 < v1)
    return float(sign) * (float(spec.pot) / 2.0 + float(matched))


def _bet_amount(action: str) -> int:
    if not action.startswith("BET_"):
        raise ValueError(action)
    return int(action.split("_", 1)[1])


def _raise_amount(action: str) -> int:
    if not action.startswith("RAISE_TO_"):
        raise ValueError(action)
    return int(action.split("RAISE_TO_", 1)[1])


def _parse_final_raise_node(node: str) -> tuple[int, int]:
    parts = node.split("_")
    return int(parts[-2]), int(parts[-1])


def actions(spec: AsymmetricRiverRaiseGameSpec, player: int, node: str) -> tuple[str, ...]:
    if player == 0 and node == ROOT:
        return ("CHECK", *(f"BET_{b}" for b in spec.p0_bet_sizes))
    if player == 1 and node == P1_AFTER_CHECK:
        return ("CHECK", *(f"BET_{b}" for b in spec.p1_bet_sizes))
    if player == 1 and node.startswith("P1_VS_P0_BET_"):
        bet = int(node.rsplit("_", 1)[1])
        return ("FOLD", "CALL", *(f"RAISE_TO_{r}" for r in spec.p1_targets(bet)))
    if player == 0 and node.startswith("P0_VS_P1_BET_"):
        bet = int(node.rsplit("_", 1)[1])
        return ("FOLD", "CALL", *(f"RAISE_TO_{r}" for r in spec.p0_targets(bet)))
    if player == 0 and node.startswith("P0_VS_P1_RAISE_"):
        return ("FOLD", "CALL")
    if player == 1 and node.startswith("P1_VS_P0_RAISE_"):
        return ("FOLD", "CALL")
    raise ValueError(f"unknown infoset: player={player} node={node}")


def all_infosets(spec: AsymmetricRiverRaiseGameSpec) -> tuple[tuple[int, str, int], ...]:
    keys: list[tuple[int, str, int]] = []
    for i in range(len(spec.p0_range)):
        keys.append((0, ROOT, i))
        for bet in spec.p1_bet_sizes:
            keys.append((0, p0_vs_p1_bet_node(bet), i))
        for bet in spec.p0_bet_sizes:
            for target in spec.p1_targets(bet):
                keys.append((0, p0_vs_p1_raise_node(bet, target), i))
    for j in range(len(spec.p1_range)):
        keys.append((1, P1_AFTER_CHECK, j))
        for bet in spec.p0_bet_sizes:
            keys.append((1, p1_vs_p0_bet_node(bet), j))
        for bet in spec.p1_bet_sizes:
            for target in spec.p0_targets(bet):
                keys.append((1, p1_vs_p0_raise_node(bet, target), j))
    return tuple(keys)


def _regret_strategy(regrets: Sequence[float]) -> tuple[float, ...]:
    positive = [max(0.0, r) for r in regrets]
    total = sum(positive)
    if total <= 0.0:
        return tuple(1.0 / len(regrets) for _ in regrets)
    return tuple(r / total for r in positive)


def _traverse_cfr(
    spec: AsymmetricRiverRaiseGameSpec,
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
    values: list[float] = []

    for a_idx, action in enumerate(acts):
        if player == 0 and node == ROOT:
            if action == "CHECK":
                value = _traverse_cfr(
                    spec, i=i, j=j, chance=chance, strategies=strategies,
                    regret_delta=regret_delta, strategy_delta=strategy_delta,
                    average_weight=average_weight, node=P1_AFTER_CHECK, player=1,
                    reach0=reach0 * sigma[a_idx], reach1=reach1,
                )
            else:
                bet = _bet_amount(action)
                value = _traverse_cfr(
                    spec, i=i, j=j, chance=chance, strategies=strategies,
                    regret_delta=regret_delta, strategy_delta=strategy_delta,
                    average_weight=average_weight, node=p1_vs_p0_bet_node(bet), player=1,
                    reach0=reach0 * sigma[a_idx], reach1=reach1,
                )
        elif player == 1 and node == P1_AFTER_CHECK:
            if action == "CHECK":
                value = showdown_value(spec, i, j)
            else:
                bet = _bet_amount(action)
                value = _traverse_cfr(
                    spec, i=i, j=j, chance=chance, strategies=strategies,
                    regret_delta=regret_delta, strategy_delta=strategy_delta,
                    average_weight=average_weight, node=p0_vs_p1_bet_node(bet), player=0,
                    reach0=reach0, reach1=reach1 * sigma[a_idx],
                )
        elif player == 1 and node.startswith("P1_VS_P0_BET_"):
            bet = int(node.rsplit("_", 1)[1])
            if action == "FOLD":
                value = float(spec.pot) / 2.0
            elif action == "CALL":
                value = showdown_value(spec, i, j, bet)
            else:
                target = _raise_amount(action)
                value = _traverse_cfr(
                    spec, i=i, j=j, chance=chance, strategies=strategies,
                    regret_delta=regret_delta, strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    node=p0_vs_p1_raise_node(bet, target), player=0,
                    reach0=reach0, reach1=reach1 * sigma[a_idx],
                )
        elif player == 0 and node.startswith("P0_VS_P1_BET_"):
            bet = int(node.rsplit("_", 1)[1])
            if action == "FOLD":
                value = -float(spec.pot) / 2.0
            elif action == "CALL":
                value = showdown_value(spec, i, j, bet)
            else:
                target = _raise_amount(action)
                value = _traverse_cfr(
                    spec, i=i, j=j, chance=chance, strategies=strategies,
                    regret_delta=regret_delta, strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    node=p1_vs_p0_raise_node(bet, target), player=1,
                    reach0=reach0 * sigma[a_idx], reach1=reach1,
                )
        elif player == 0 and node.startswith("P0_VS_P1_RAISE_"):
            bet, target = _parse_final_raise_node(node)
            value = -(float(spec.pot) / 2.0 + float(bet)) if action == "FOLD" else showdown_value(spec, i, j, target)
        elif player == 1 and node.startswith("P1_VS_P0_RAISE_"):
            bet, target = _parse_final_raise_node(node)
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


def _normalize_policy(spec, strategy_sum, regrets):
    out = {}
    for key in all_infosets(spec):
        vals = strategy_sum[key]
        total = sum(vals)
        out[key] = tuple(v / total for v in vals) if total > 0 else _regret_strategy(regrets[key])
    return out


def _deal_value(
    spec,
    i,
    j,
    policy,
    *,
    deterministic_player=None,
    deterministic_plan=None,
    node=ROOT,
    player=0,
):
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
            value = _deal_value(spec, i, j, policy, deterministic_player=deterministic_player, deterministic_plan=deterministic_plan, node=P1_AFTER_CHECK, player=1) if action == "CHECK" else _deal_value(spec, i, j, policy, deterministic_player=deterministic_player, deterministic_plan=deterministic_plan, node=p1_vs_p0_bet_node(_bet_amount(action)), player=1)
        elif player == 1 and node == P1_AFTER_CHECK:
            value = showdown_value(spec, i, j) if action == "CHECK" else _deal_value(spec, i, j, policy, deterministic_player=deterministic_player, deterministic_plan=deterministic_plan, node=p0_vs_p1_bet_node(_bet_amount(action)), player=0)
        elif player == 1 and node.startswith("P1_VS_P0_BET_"):
            bet = int(node.rsplit("_", 1)[1])
            if action == "FOLD":
                value = float(spec.pot) / 2.0
            elif action == "CALL":
                value = showdown_value(spec, i, j, bet)
            else:
                value = _deal_value(spec, i, j, policy, deterministic_player=deterministic_player, deterministic_plan=deterministic_plan, node=p0_vs_p1_raise_node(bet, _raise_amount(action)), player=0)
        elif player == 0 and node.startswith("P0_VS_P1_BET_"):
            bet = int(node.rsplit("_", 1)[1])
            if action == "FOLD":
                value = -float(spec.pot) / 2.0
            elif action == "CALL":
                value = showdown_value(spec, i, j, bet)
            else:
                value = _deal_value(spec, i, j, policy, deterministic_player=deterministic_player, deterministic_plan=deterministic_plan, node=p1_vs_p0_raise_node(bet, _raise_amount(action)), player=1)
        elif player == 0 and node.startswith("P0_VS_P1_RAISE_"):
            bet, target = _parse_final_raise_node(node)
            value = -(float(spec.pot) / 2.0 + float(bet)) if action == "FOLD" else showdown_value(spec, i, j, target)
        elif player == 1 and node.startswith("P1_VS_P0_RAISE_"):
            bet, target = _parse_final_raise_node(node)
            value = (float(spec.pot) / 2.0 + float(bet)) if action == "FOLD" else showdown_value(spec, i, j, target)
        else:  # pragma: no cover
            raise AssertionError((player, node, action))
        values.append(value)
    return sum(p * v for p, v in zip(sigma, values))


def _pure_plans_for_hand(spec, player: int, hand_idx: int):
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
            br0 += max(
                sum(w * _deal_value(spec, i, j, policy, deterministic_player=0, deterministic_plan=plan) for j, w in ds)
                for plan in _pure_plans_for_hand(spec, 0, i)
            )
    br1 = 0.0
    for j in range(len(spec.p1_range)):
        ds = [(i, w) for i, jj, w in deals if jj == j]
        if ds:
            br1 += min(
                sum(w * _deal_value(spec, i, j, policy, deterministic_player=1, deterministic_plan=plan) for i, w in ds)
                for plan in _pure_plans_for_hand(spec, 1, j)
            )
    return br0 / total, br1 / total


def solve_asymmetric_river_raise_cfr_plus(
    spec: AsymmetricRiverRaiseGameSpec,
    *,
    iterations: int = 500,
) -> RiverSolveResult:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    infosets = all_infosets(spec)
    regrets = {k: [0.0] * len(actions(spec, k[0], k[1])) for k in infosets}
    strategy_sum = {k: [0.0] * len(actions(spec, k[0], k[1])) for k in infosets}
    deals = valid_deals(spec)
    total_chance = sum(w for _, _, w in deals)

    for iteration in range(1, iterations + 1):
        strategies = {k: _regret_strategy(regrets[k]) for k in infosets}
        rd = {k: [0.0] * len(regrets[k]) for k in infosets}
        sd = {k: [0.0] * len(regrets[k]) for k in infosets}
        for i, j, raw_weight in deals:
            _traverse_cfr(
                spec,
                i=i,
                j=j,
                chance=raw_weight / total_chance,
                strategies=strategies,
                regret_delta=rd,
                strategy_delta=sd,
                average_weight=float(iteration),
            )
        for key in infosets:
            for a_idx in range(len(regrets[key])):
                regrets[key][a_idx] = max(0.0, regrets[key][a_idx] + rd[key][a_idx])
                strategy_sum[key][a_idx] += sd[key][a_idx]

    policy = _normalize_policy(spec, strategy_sum, regrets)
    total = sum(w for _, _, w in deals)
    policy_ev = sum(w * _deal_value(spec, i, j, policy) for i, j, w in deals) / total
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


def _subset_raise_map(
    full_map: tuple[tuple[int, tuple[int, ...]], ...],
    faced_sizes: tuple[int, ...],
) -> tuple[tuple[int, tuple[int, ...]], ...]:
    mapping = dict(full_map)
    return tuple((bet, mapping[bet]) for bet in faced_sizes)


def evaluate_opening_restriction_loss_with_raises(
    *,
    board: tuple[int, int, int, int, int],
    p0_range: tuple[RangeCombo, ...],
    p1_range: tuple[RangeCombo, ...],
    pot: int,
    reference_sizes: tuple[int, ...],
    candidate_sizes: tuple[int, ...],
    reference_raise_targets: tuple[tuple[int, tuple[int, ...]], ...],
    iterations: int,
) -> OpeningRestrictionWithRaisesResult:
    """Bound opening-size restriction loss while keeping rich raises available.

    Candidate sizes must be a subset of reference opening sizes.  The player's
    raise responses to the opponent's reference bets remain the full reference
    raise set; the opponent's raises over candidate opening bets are the same
    reference raises those bets would face in R-vs-R.  Therefore this isolates
    opening-bet action loss in a one-raise environment instead of simultaneously
    changing both opening and raise abstractions.
    """
    if not set(candidate_sizes).issubset(reference_sizes):
        raise ValueError("candidate sizes must be a subset of reference sizes")
    ref_map = dict(reference_raise_targets)
    if set(ref_map) != set(reference_sizes):
        raise ValueError("reference raise targets must cover reference sizes")

    ref = solve_asymmetric_river_raise_cfr_plus(
        AsymmetricRiverRaiseGameSpec(
            board, p0_range, p1_range, pot,
            reference_sizes, reference_sizes,
            reference_raise_targets, reference_raise_targets,
        ),
        iterations=iterations,
    )
    p0r = solve_asymmetric_river_raise_cfr_plus(
        AsymmetricRiverRaiseGameSpec(
            board, p0_range, p1_range, pot,
            candidate_sizes, reference_sizes,
            _subset_raise_map(reference_raise_targets, candidate_sizes),
            reference_raise_targets,
        ),
        iterations=iterations,
    )
    p1r = solve_asymmetric_river_raise_cfr_plus(
        AsymmetricRiverRaiseGameSpec(
            board, p0_range, p1_range, pot,
            reference_sizes, candidate_sizes,
            reference_raise_targets,
            _subset_raise_map(reference_raise_targets, candidate_sizes),
        ),
        iterations=iterations,
    )

    p0_lower = ref.br1_value - p0r.br0_value
    p0_upper = ref.br0_value - p0r.br1_value
    p1_lower = p1r.br1_value - ref.br0_value
    p1_upper = p1r.br0_value - ref.br1_value
    worst_upper = max(0.0, p0_upper, p1_upper)
    return OpeningRestrictionWithRaisesResult(
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
