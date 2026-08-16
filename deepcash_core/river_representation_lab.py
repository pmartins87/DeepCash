from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Sequence

from .evaluator import evaluate_best
from .river_lab import (
    P1_AFTER_CHECK,
    ROOT,
    RiverGameSpec,
    RiverSolveResult,
    _actions,
    _bet_amount,
    _regret_strategy,
    _terminal_showdown,
    _valid_deals,
    evaluate_policy,
    exact_best_response_values,
    p0_vs_bet_node,
    p1_vs_bet_node,
)


RIVER_REPRESENTATION_CANDIDATES = (
    "category",
    "strength4",
    "equity4",
    "equity8",
    "category_equity4",
    "equity4_blocker2",
    "equity8_blocker2",
)


@dataclass(frozen=True)
class RiverBucketMaps:
    """Private-state bucket id for every exact combo in each player's range.

    The chance model, cards, payoff and action tree remain exact. Only the
    information-set identity used by CFR is aliased. This is intentionally the
    same separation required later in the full DeepCash architecture: lossy
    compression is allowed at the solver/encoder observation boundary, never in
    the game engine itself.
    """

    p0: tuple[int, ...]
    p1: tuple[int, ...]
    name: str = "custom"

    def validate(self, spec: RiverGameSpec) -> None:
        if len(self.p0) != len(spec.p0_range) or len(self.p1) != len(spec.p1_range):
            raise ValueError("bucket maps must cover every exact range combo")
        if any(v < 0 for v in (*self.p0, *self.p1)):
            raise ValueError("bucket ids must be non-negative")

    @property
    def p0_bucket_count(self) -> int:
        return len(set(self.p0))

    @property
    def p1_bucket_count(self) -> int:
        return len(set(self.p1))



def _dense(features: Sequence[Hashable]) -> tuple[int, ...]:
    # Stable first-occurrence densification avoids depending on physical card
    # integer ordering when two exact combos share the same strategic feature.
    ids: dict[Hashable, int] = {}
    out: list[int] = []
    for feature in features:
        if feature not in ids:
            ids[feature] = len(ids)
        out.append(ids[feature])
    return tuple(out)



def exact_bucket_map(count: int) -> tuple[int, ...]:
    if count <= 0:
        raise ValueError("count must be positive")
    return tuple(range(count))



def exact_bucket_maps(spec: RiverGameSpec) -> RiverBucketMaps:
    return RiverBucketMaps(
        exact_bucket_map(len(spec.p0_range)),
        exact_bucket_map(len(spec.p1_range)),
        "exact",
    )



def _player_range(spec: RiverGameSpec, player: int):
    if player == 0:
        return spec.p0_range
    if player == 1:
        return spec.p1_range
    raise ValueError("player must be 0 or 1")



def _opponent_range(spec: RiverGameSpec, player: int):
    return spec.p1_range if player == 0 else spec.p0_range



def category_bucket_map(spec: RiverGameSpec, player: int) -> tuple[int, ...]:
    features = [
        evaluate_best((*combo.hole, *spec.board))[0]
        for combo in _player_range(spec, player)
    ]
    return _dense(features)



def _weighted_quantile_map(
    values: Sequence[Hashable], weights: Sequence[float], bucket_count: int
) -> tuple[int, ...]:
    """Bucket ordered feature values without splitting exact ties.

    Equal feature values always receive the same bucket. This matters for suit
    and card-order invariance: a tie must never be broken by incidental combo
    enumeration order.
    """
    if bucket_count <= 0:
        raise ValueError("bucket_count must be positive")
    if len(values) != len(weights) or not values:
        raise ValueError("values/weights must be non-empty and aligned")
    if any(w <= 0 for w in weights):
        raise ValueError("weights must be positive")

    groups: dict[Hashable, float] = {}
    for value, weight in zip(values, weights):
        groups[value] = groups.get(value, 0.0) + float(weight)
    ordered = sorted(groups.items(), key=lambda item: item[0])
    total = sum(weight for _, weight in ordered)
    feature_bucket: dict[Hashable, int] = {}
    cumulative = 0.0
    for feature, weight in ordered:
        midpoint = cumulative + 0.5 * weight
        raw = min(bucket_count - 1, int(bucket_count * midpoint / total))
        feature_bucket[feature] = raw
        cumulative += weight

    # Clipping/ties can leave empty nominal quantiles. Densify the materialized
    # buckets so reported compression reflects the tree that actually exists.
    return _dense([feature_bucket[value] for value in values])



def strength_quantile_bucket_map(
    spec: RiverGameSpec, player: int, bucket_count: int
) -> tuple[int, ...]:
    rng = _player_range(spec, player)
    values = [evaluate_best((*combo.hole, *spec.board)) for combo in rng]
    weights = [float(combo.weight) for combo in rng]
    return _weighted_quantile_map(values, weights, bucket_count)



def showdown_equities(spec: RiverGameSpec, player: int) -> tuple[float, ...]:
    """Exact river showdown equity versus the supplied opponent range.

    Card removal is exact: incompatible opponent combos are excluded separately
    for each private hand. Opponent combo weights are respected conditionally.
    """
    own = _player_range(spec, player)
    opp = _opponent_range(spec, player)
    out: list[float] = []
    for own_combo in own:
        numerator = 0.0
        denominator = 0.0
        own_cards = set(own_combo.hole)
        own_value = evaluate_best((*own_combo.hole, *spec.board))
        for opp_combo in opp:
            if own_cards.intersection(opp_combo.hole):
                continue
            weight = float(opp_combo.weight)
            opp_value = evaluate_best((*opp_combo.hole, *spec.board))
            if own_value > opp_value:
                score = 1.0
            elif own_value == opp_value:
                score = 0.5
            else:
                score = 0.0
            numerator += weight * score
            denominator += weight
        if denominator <= 0.0:
            raise ValueError("private combo has no compatible opponent range")
        out.append(numerator / denominator)
    return tuple(out)



def equity_quantile_bucket_map(
    spec: RiverGameSpec, player: int, bucket_count: int
) -> tuple[int, ...]:
    rng = _player_range(spec, player)
    return _weighted_quantile_map(
        showdown_equities(spec, player),
        [float(combo.weight) for combo in rng],
        bucket_count,
    )



def blocker_masses(spec: RiverGameSpec, player: int) -> tuple[float, ...]:
    """Opponent range weight removed by each exact private combo."""
    own = _player_range(spec, player)
    opp = _opponent_range(spec, player)
    total_opp = sum(float(combo.weight) for combo in opp)
    out = []
    for own_combo in own:
        own_cards = set(own_combo.hole)
        compatible = sum(
            float(opp_combo.weight)
            for opp_combo in opp
            if not own_cards.intersection(opp_combo.hole)
        )
        out.append(total_opp - compatible)
    return tuple(out)



def blocker_quantile_bucket_map(
    spec: RiverGameSpec, player: int, bucket_count: int
) -> tuple[int, ...]:
    rng = _player_range(spec, player)
    return _weighted_quantile_map(
        blocker_masses(spec, player),
        [float(combo.weight) for combo in rng],
        bucket_count,
    )



def combine_bucket_maps(*maps: Sequence[int]) -> tuple[int, ...]:
    if not maps:
        raise ValueError("at least one bucket map is required")
    n = len(maps[0])
    if any(len(m) != n for m in maps):
        raise ValueError("bucket maps must have equal length")
    return _dense([tuple(m[i] for m in maps) for i in range(n)])



def candidate_bucket_map(
    spec: RiverGameSpec, player: int, name: str
) -> tuple[int, ...]:
    if name == "exact":
        return exact_bucket_map(len(_player_range(spec, player)))
    if name == "category":
        return category_bucket_map(spec, player)
    if name == "strength4":
        return strength_quantile_bucket_map(spec, player, 4)
    if name == "equity4":
        return equity_quantile_bucket_map(spec, player, 4)
    if name == "equity8":
        return equity_quantile_bucket_map(spec, player, 8)
    if name == "category_equity4":
        return combine_bucket_maps(
            category_bucket_map(spec, player),
            equity_quantile_bucket_map(spec, player, 4),
        )
    if name == "equity4_blocker2":
        return combine_bucket_maps(
            equity_quantile_bucket_map(spec, player, 4),
            blocker_quantile_bucket_map(spec, player, 2),
        )
    if name == "equity8_blocker2":
        return combine_bucket_maps(
            equity_quantile_bucket_map(spec, player, 8),
            blocker_quantile_bucket_map(spec, player, 2),
        )
    raise ValueError(f"unknown river representation candidate: {name}")



def candidate_bucket_maps(spec: RiverGameSpec, name: str) -> RiverBucketMaps:
    maps = RiverBucketMaps(
        candidate_bucket_map(spec, 0, name),
        candidate_bucket_map(spec, 1, name),
        name,
    )
    maps.validate(spec)
    return maps



def _abstract_infosets(spec: RiverGameSpec, maps: RiverBucketMaps):
    maps.validate(spec)
    keys: list[tuple[int, str, int]] = []
    for bucket in sorted(set(maps.p0)):
        keys.append((0, ROOT, bucket))
        for bet in spec.bet_sizes:
            keys.append((0, p0_vs_bet_node(bet), bucket))
    for bucket in sorted(set(maps.p1)):
        keys.append((1, P1_AFTER_CHECK, bucket))
        for bet in spec.bet_sizes:
            keys.append((1, p1_vs_bet_node(bet), bucket))
    return tuple(keys)



def _abstract_key(
    maps: RiverBucketMaps, player: int, node: str, i: int, j: int
) -> tuple[int, str, int]:
    return (player, node, maps.p0[i] if player == 0 else maps.p1[j])



def _traverse_abstract_cfr(
    spec: RiverGameSpec,
    maps: RiverBucketMaps,
    *,
    i: int,
    j: int,
    chance: float,
    strategies,
    regret_delta,
    strategy_delta,
    average_weight: float,
    node: str = ROOT,
    player: int = 0,
    reach0: float = 1.0,
    reach1: float = 1.0,
) -> float:
    key = _abstract_key(maps, player, node, i, j)
    actions = _actions(spec, player, node)
    sigma = strategies[key]
    action_values: list[float] = []

    for action_index, action in enumerate(actions):
        if player == 0 and node == ROOT:
            if action == "CHECK":
                value = _traverse_abstract_cfr(
                    spec,
                    maps,
                    i=i,
                    j=j,
                    chance=chance,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    node=P1_AFTER_CHECK,
                    player=1,
                    reach0=reach0 * sigma[action_index],
                    reach1=reach1,
                )
            else:
                value = _traverse_abstract_cfr(
                    spec,
                    maps,
                    i=i,
                    j=j,
                    chance=chance,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    node=p1_vs_bet_node(_bet_amount(action)),
                    player=1,
                    reach0=reach0 * sigma[action_index],
                    reach1=reach1,
                )
        elif player == 1 and node == P1_AFTER_CHECK:
            if action == "CHECK":
                value = _terminal_showdown(spec, i, j)
            else:
                value = _traverse_abstract_cfr(
                    spec,
                    maps,
                    i=i,
                    j=j,
                    chance=chance,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    strategy_delta=strategy_delta,
                    average_weight=average_weight,
                    node=p0_vs_bet_node(_bet_amount(action)),
                    player=0,
                    reach0=reach0,
                    reach1=reach1 * sigma[action_index],
                )
        elif player == 1 and node.startswith("P1_VS_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            value = (
                float(spec.pot) / 2.0
                if action == "FOLD"
                else _terminal_showdown(spec, i, j, amount)
            )
        elif player == 0 and node.startswith("P0_VS_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            value = (
                -float(spec.pot) / 2.0
                if action == "FOLD"
                else _terminal_showdown(spec, i, j, amount)
            )
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



def _normalize_abstract_policy(spec, infosets, strategy_sum, regrets):
    out = {}
    for key in infosets:
        vals = strategy_sum[key]
        total = sum(vals)
        if total > 0.0:
            out[key] = tuple(v / total for v in vals)
        else:
            out[key] = _regret_strategy(regrets[key])
    return out



def _expand_policy(spec: RiverGameSpec, maps: RiverBucketMaps, abstract_policy):
    out = {}
    for i in range(len(spec.p0_range)):
        out[(0, ROOT, i)] = abstract_policy[(0, ROOT, maps.p0[i])]
        for bet in spec.bet_sizes:
            node = p0_vs_bet_node(bet)
            out[(0, node, i)] = abstract_policy[(0, node, maps.p0[i])]
    for j in range(len(spec.p1_range)):
        out[(1, P1_AFTER_CHECK, j)] = abstract_policy[(1, P1_AFTER_CHECK, maps.p1[j])]
        for bet in spec.bet_sizes:
            node = p1_vs_bet_node(bet)
            out[(1, node, j)] = abstract_policy[(1, node, maps.p1[j])]
    return out



def solve_river_representation_cfr_plus(
    spec: RiverGameSpec,
    maps: RiverBucketMaps,
    *,
    iterations: int = 2_000,
) -> RiverSolveResult:
    """Solve the exact river chance game with aliased private infosets.

    The returned policy is expanded back to exact combo keys before evaluation,
    so exploitability and best responses are measured in the uncompressed game.
    `infosets` and `action_slots` report the compressed training tree.
    """
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    maps.validate(spec)
    infosets = _abstract_infosets(spec, maps)
    regrets = {k: [0.0] * len(_actions(spec, k[0], k[1])) for k in infosets}
    strategy_sum = {k: [0.0] * len(_actions(spec, k[0], k[1])) for k in infosets}
    deals = _valid_deals(spec)
    total_chance = sum(w for _, _, w in deals)

    for iteration in range(1, iterations + 1):
        strategies = {k: _regret_strategy(regrets[k]) for k in infosets}
        regret_delta = {k: [0.0] * len(regrets[k]) for k in infosets}
        strategy_delta = {k: [0.0] * len(regrets[k]) for k in infosets}
        for i, j, raw_weight in deals:
            _traverse_abstract_cfr(
                spec,
                maps,
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

    abstract_policy = _normalize_abstract_policy(spec, infosets, strategy_sum, regrets)
    policy = _expand_policy(spec, maps, abstract_policy)
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



def one_sided_bucket_maps(
    spec: RiverGameSpec, candidate: RiverBucketMaps, restricted_player: int
) -> RiverBucketMaps:
    candidate.validate(spec)
    exact = exact_bucket_maps(spec)
    if restricted_player == 0:
        return RiverBucketMaps(candidate.p0, exact.p1, f"{candidate.name}:p0_only")
    if restricted_player == 1:
        return RiverBucketMaps(exact.p0, candidate.p1, f"{candidate.name}:p1_only")
    raise ValueError("restricted_player must be 0 or 1")
