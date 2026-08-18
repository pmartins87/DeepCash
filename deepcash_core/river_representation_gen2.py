from __future__ import annotations

from fractions import Fraction
from typing import Optional

from .evaluator import evaluate_best
from .river_lab import RiverGameSpec
from .river_representation_lab import (
    RiverBucketMaps,
    combine_bucket_maps,
    equity_quantile_bucket_map,
)


# Generation-2 is deliberately separate from RIVER_REPRESENTATION_CANDIDATES.
# Re-running a Generation-1 workflow must never silently consume these candidates.
R4_GEN2_CANDIDATES = (
    "equity8",
    "matchup_cluster4",
    "matchup_cluster8",
    "equity4_matchup2",
)

# Unlike Generation-1's one-bet reference (which clips SPR2 and SPR4 to the same
# materialized action set), this frozen grid produces a genuinely different action
# geometry at stack/pot ratios 1, 2 and 4:
#   SPR1 -> 25/50/100
#   SPR2 -> 25/50/100/200
#   SPR4 -> 25/50/100/200/400
GEN2_REFERENCE_FRACTIONS = (
    Fraction(1, 4),
    Fraction(1, 2),
    Fraction(1, 1),
    Fraction(2, 1),
    Fraction(4, 1),
)


def _player_range(spec: RiverGameSpec, player: int):
    if player == 0:
        return spec.p0_range
    if player == 1:
        return spec.p1_range
    raise ValueError("player must be 0 or 1")


def _opponent_range(spec: RiverGameSpec, player: int):
    return spec.p1_range if player == 0 else spec.p0_range


def _showdown_score(own_value, opp_value) -> float:
    if own_value > opp_value:
        return 1.0
    if own_value == opp_value:
        return 0.5
    return 0.0


def matchup_profile_distance_matrix(
    spec: RiverGameSpec, player: int
) -> tuple[tuple[float, ...], ...]:
    """Pairwise distance between private hands from exact matchup profiles.

    For every own exact combo we evaluate its showdown result against every
    opponent-range combo. Card removal is represented explicitly: an incompatible
    opponent combo has no showdown score. Two own hands are distant when they
    disagree on showdown result and/or block different opponent mass.

    The distance uses only legal decision-time information: public board, the
    player's own private combo and the modelled opponent range. There is no
    realized opponent private hand, solved policy or future action value input.
    Opponent weights are respected, and summation makes the distance invariant to
    opponent-range enumeration order.
    """
    own = _player_range(spec, player)
    opp = _opponent_range(spec, player)
    if not own or not opp:
        raise ValueError("both ranges must be non-empty")

    opp_values = [evaluate_best((*combo.hole, *spec.board)) for combo in opp]
    opp_weights = [float(combo.weight) for combo in opp]
    total_opp_weight = sum(opp_weights)
    if total_opp_weight <= 0.0:
        raise ValueError("opponent range must have positive total weight")

    profiles: list[tuple[Optional[float], ...]] = []
    for own_combo in own:
        own_cards = set(own_combo.hole)
        own_value = evaluate_best((*own_combo.hole, *spec.board))
        row: list[Optional[float]] = []
        for opp_combo, opp_value in zip(opp, opp_values):
            if own_cards.intersection(opp_combo.hole):
                row.append(None)
            else:
                row.append(_showdown_score(own_value, opp_value))
        profiles.append(tuple(row))

    matrix: list[tuple[float, ...]] = []
    for left in profiles:
        distances: list[float] = []
        for right in profiles:
            total = 0.0
            for a, b, weight in zip(left, right, opp_weights):
                if a is None and b is None:
                    delta = 0.0
                elif a is None or b is None:
                    # Blocking a combo that the other hand must face is a full
                    # profile disagreement. This lets clustering capture card
                    # removal without leaking the realized opponent hand.
                    delta = 1.0
                else:
                    delta = abs(a - b)
                total += weight * delta
            distances.append(total / total_opp_weight)
        matrix.append(tuple(distances))
    return tuple(matrix)


def _weighted_medoid(
    members: tuple[int, ...],
    distances: tuple[tuple[float, ...], ...],
    weights: tuple[float, ...],
) -> int:
    if not members:
        raise ValueError("cannot choose medoid of empty cluster")
    return min(
        members,
        key=lambda candidate: (
            sum(weights[j] * distances[candidate][j] for j in members),
            candidate,
        ),
    )


def matchup_cluster_bucket_map(
    spec: RiverGameSpec,
    player: int,
    bucket_count: int,
) -> tuple[int, ...]:
    """Deterministic weighted k-medoids over exact matchup-profile distance.

    Initialization is central-medoid then deterministic farthest-first. Lloyd-like
    medoid refinement is deterministic. If fewer than ``bucket_count`` distinct
    matchup profiles exist, the materialized bucket count is smaller rather than
    inventing distinctions that do not exist.
    """
    if bucket_count <= 0:
        raise ValueError("bucket_count must be positive")
    own = _player_range(spec, player)
    n = len(own)
    if n <= 0:
        raise ValueError("player range must be non-empty")
    if n == 1:
        return (0,)

    distances = matchup_profile_distance_matrix(spec, player)
    weights = tuple(float(combo.weight) for combo in own)
    target = min(int(bucket_count), n)

    # Start from the global weighted medoid, then add the point farthest from its
    # nearest existing medoid. Index is only a deterministic final tie-breaker;
    # global suit permutation and hole-card reversal preserve range position.
    all_members = tuple(range(n))
    medoids = [_weighted_medoid(all_members, distances, weights)]
    while len(medoids) < target:
        candidates = [i for i in range(n) if i not in medoids]
        if not candidates:
            break
        nearest = {
            i: min(distances[i][m] for m in medoids)
            for i in candidates
        }
        best_distance = max(nearest.values())
        if best_distance <= 1e-15:
            break
        next_medoid = min(i for i in candidates if abs(nearest[i] - best_distance) <= 1e-15)
        medoids.append(next_medoid)

    assignments = [0] * n
    for _ in range(50):
        clusters: list[list[int]] = [[] for _ in medoids]
        for i in range(n):
            cluster = min(
                range(len(medoids)),
                key=lambda c: (distances[i][medoids[c]], c),
            )
            assignments[i] = cluster
            clusters[cluster].append(i)

        new_medoids = [
            _weighted_medoid(tuple(members), distances, weights)
            for members in clusters
        ]
        if new_medoids == medoids:
            break
        medoids = new_medoids
    else:
        raise RuntimeError("deterministic matchup clustering did not converge")

    # Recompute once using the final medoids and densify in first-occurrence
    # order so labels are stable and contain no empty materialized buckets.
    raw = []
    for i in range(n):
        raw.append(
            min(
                range(len(medoids)),
                key=lambda c: (distances[i][medoids[c]], c),
            )
        )
    dense_ids: dict[int, int] = {}
    out: list[int] = []
    for cluster in raw:
        if cluster not in dense_ids:
            dense_ids[cluster] = len(dense_ids)
        out.append(dense_ids[cluster])
    return tuple(out)


def gen2_candidate_bucket_map(
    spec: RiverGameSpec, player: int, name: str
) -> tuple[int, ...]:
    if name == "equity8":
        return equity_quantile_bucket_map(spec, player, 8)
    if name == "matchup_cluster4":
        return matchup_cluster_bucket_map(spec, player, 4)
    if name == "matchup_cluster8":
        return matchup_cluster_bucket_map(spec, player, 8)
    if name == "equity4_matchup2":
        return combine_bucket_maps(
            equity_quantile_bucket_map(spec, player, 4),
            matchup_cluster_bucket_map(spec, player, 2),
        )
    raise ValueError(f"unknown R4 Generation-2 candidate: {name}")


def gen2_candidate_bucket_maps(spec: RiverGameSpec, name: str) -> RiverBucketMaps:
    if name not in R4_GEN2_CANDIDATES:
        raise ValueError(f"candidate is not frozen for R4 Generation-2: {name}")
    maps = RiverBucketMaps(
        gen2_candidate_bucket_map(spec, 0, name),
        gen2_candidate_bucket_map(spec, 1, name),
        name,
    )
    maps.validate(spec)
    return maps
