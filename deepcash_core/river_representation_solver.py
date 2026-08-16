from __future__ import annotations

from .river_lab import RiverGameSpec, RiverSolveResult
from .river_representation_lab import RiverBucketMaps
from .river_representation_training import (
    advance_representation_cfr_plus,
    init_representation_cfr_plus,
    representation_result_from_state,
)


def solve_river_representation_cfr_plus(
    spec: RiverGameSpec,
    maps: RiverBucketMaps,
    *,
    iterations: int = 2_000,
) -> RiverSolveResult:
    """Authoritative monolithic convenience wrapper for the R4 solver.

    Training and evaluation deliberately go through the same resumable state
    path used by production benchmarks.  In particular, final best responses
    are the exact bucket-constrained BRs from
    ``representation_result_from_state``.  This avoids maintaining a second
    monolithic evaluator with subtly different information semantics.
    """
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    state = init_representation_cfr_plus(spec, maps)
    advance_representation_cfr_plus(
        spec,
        maps,
        state,
        additional_iterations=iterations,
    )
    return representation_result_from_state(spec, maps, state)
