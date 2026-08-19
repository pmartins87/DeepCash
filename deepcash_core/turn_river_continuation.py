from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .r4_production_representation import production_representation_name
from .river_alternating_dcfr import AlternatingVariant
from .river_representation_alternating_dcfr import (
    advance_alternating_representation_solver,
    alternating_representation_result,
    init_alternating_representation_solver,
)
from .river_representation_gen2 import gen2_candidate_bucket_maps
from .river_representation_lab import RiverBucketMaps, exact_bucket_maps
from .turn_river_public_state import RiverPublicChild, TurnPublicState, enumerate_river_children


DEFAULT_R4_PRODUCTION_FREEZE = (
    Path(__file__).resolve().parent / "data" / "r4_production_representation_v1.json"
)
PRODUCTION_SOLVER_VARIANT = AlternatingVariant.ALT_DCFR_150_0_2


@dataclass(frozen=True)
class RiverContinuationValue:
    river_card: int
    chance_probability: float
    chance_mass: float
    policy_ev: float
    exploitability_per_pot: float
    infosets: int
    action_slots: int
    iterations: int


@dataclass(frozen=True)
class TurnContinuationResult:
    representation: str
    solver_variant: str
    river_iterations: int
    children: tuple[RiverContinuationValue, ...]
    policy_ev: float
    weighted_child_exploitability_per_pot: float

    def validate(self) -> None:
        if self.river_iterations <= 0:
            raise ValueError("river_iterations must be positive")
        if not self.children:
            raise ValueError("turn continuation must contain at least one river child")
        probability = sum(child.chance_probability for child in self.children)
        if abs(probability - 1.0) > 1e-12:
            raise ValueError("river continuation chance probabilities must sum to one")
        low = min(child.policy_ev for child in self.children)
        high = max(child.policy_ev for child in self.children)
        if self.policy_ev < low - 1e-12 or self.policy_ev > high + 1e-12:
            raise ValueError("weighted continuation value is outside child-value range")
        if self.weighted_child_exploitability_per_pot < -1e-15:
            raise ValueError("weighted child exploitability cannot be negative")


def _maps_for_child(
    child: RiverPublicChild,
    *,
    representation: str,
) -> RiverBucketMaps:
    if representation == "exact":
        return exact_bucket_maps(child.spec)
    return gen2_candidate_bucket_maps(child.spec, representation)


def solve_turn_river_continuation(
    state: TurnPublicState,
    *,
    river_iterations: int,
    representation: Literal["production", "exact"] | str = "production",
    production_freeze_path: str | Path = DEFAULT_R4_PRODUCTION_FREEZE,
) -> TurnContinuationResult:
    """Solve a chance-only turn continuation into independently solved river subgames.

    This is the first R6 composition primitive, not a turn betting solver.  The
    turn state reaches an exact public river chance node; card removal conditions
    both private ranges before any lossy representation is constructed.  Every
    public river child is then solved independently with the exact frozen
    alternating post-update discounted semantics used by the physical bridge.

    ``representation='production'`` resolves through the immutable R4 production
    freeze. ``representation='exact'`` is a regression/reference mode in which
    private infosets are not aliased.
    """
    state.validate()
    if river_iterations <= 0:
        raise ValueError("river_iterations must be positive")

    if representation == "production":
        representation_name = production_representation_name(production_freeze_path)
    else:
        representation_name = str(representation)
        if representation_name != "exact":
            # Fail closed through the frozen Generation-2 candidate registry.
            # gen2_candidate_bucket_maps performs the canonical name check per child.
            pass

    river_children = enumerate_river_children(state)
    solved: list[RiverContinuationValue] = []
    for child in river_children:
        maps = _maps_for_child(child, representation=representation_name)
        solver_state = init_alternating_representation_solver(
            child.spec,
            maps,
            PRODUCTION_SOLVER_VARIANT,
        )
        advance_alternating_representation_solver(
            child.spec,
            maps,
            solver_state,
            additional_iterations=river_iterations,
        )
        result = alternating_representation_result(child.spec, maps, solver_state)
        solved.append(
            RiverContinuationValue(
                river_card=child.river_card,
                chance_probability=child.chance_probability,
                chance_mass=child.chance_mass,
                policy_ev=result.policy_ev,
                exploitability_per_pot=result.exploitability_per_pot,
                infosets=result.infosets,
                action_slots=result.action_slots,
                iterations=result.iterations,
            )
        )

    policy_ev = sum(child.chance_probability * child.policy_ev for child in solved)
    weighted_exploitability = sum(
        child.chance_probability * child.exploitability_per_pot for child in solved
    )
    out = TurnContinuationResult(
        representation=representation_name,
        solver_variant=PRODUCTION_SOLVER_VARIANT.value,
        river_iterations=river_iterations,
        children=tuple(solved),
        policy_ev=policy_ev,
        weighted_child_exploitability_per_pot=weighted_exploitability,
    )
    out.validate()
    return out
