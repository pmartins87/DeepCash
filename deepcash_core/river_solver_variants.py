from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .river_lab import (
    RiverGameSpec,
    RiverSolveResult,
    _actions,
    _all_infosets,
    _normalize_policy,
    _regret_strategy,
    _traverse_cfr,
    _valid_deals,
    evaluate_policy,
    exact_best_response_values,
)
from .river_training import river_spec_signature

InfoKey = tuple[int, str, int]


class SolverVariant(str, Enum):
    CFR_UNIFORM = "CFR_UNIFORM"
    CFR_LINEAR = "CFR_LINEAR"
    CFR_PLUS_UNIFORM = "CFR_PLUS_UNIFORM"
    CFR_PLUS_LINEAR = "CFR_PLUS_LINEAR"

    @property
    def clips_regrets(self) -> bool:
        return self in {self.CFR_PLUS_UNIFORM, self.CFR_PLUS_LINEAR}

    @property
    def linear_average(self) -> bool:
        return self in {self.CFR_LINEAR, self.CFR_PLUS_LINEAR}


@dataclass
class RiverSolverState:
    spec_signature: tuple
    variant: SolverVariant
    iterations: int
    regrets: dict[InfoKey, list[float]]
    strategy_sum: dict[InfoKey, list[float]]

    def validate(self, spec: RiverGameSpec, *, variant: SolverVariant | None = None) -> None:
        if self.spec_signature != river_spec_signature(spec):
            raise ValueError("solver checkpoint belongs to a different river game spec")
        if variant is not None and self.variant != variant:
            raise ValueError("solver checkpoint belongs to a different solver variant")
        if self.iterations < 0:
            raise ValueError("iterations cannot be negative")
        expected = set(_all_infosets(spec))
        if set(self.regrets) != expected or set(self.strategy_sum) != expected:
            raise ValueError("solver checkpoint infosets do not match game spec")
        for key in expected:
            n = len(_actions(spec, key[0], key[1]))
            if len(self.regrets[key]) != n or len(self.strategy_sum[key]) != n:
                raise ValueError(f"solver checkpoint action shape mismatch at {key}")
            for value in (*self.regrets[key], *self.strategy_sum[key]):
                if not math.isfinite(value):
                    raise ValueError("solver checkpoint contains non-finite values")
            if any(value < 0.0 for value in self.strategy_sum[key]):
                raise ValueError("average-strategy sums cannot be negative")
            if self.variant.clips_regrets and any(value < 0.0 for value in self.regrets[key]):
                raise ValueError("CFR+ checkpoint regrets must remain non-negative")


def init_river_solver(spec: RiverGameSpec, variant: SolverVariant | str) -> RiverSolverState:
    variant = SolverVariant(variant)
    infosets = _all_infosets(spec)
    state = RiverSolverState(
        spec_signature=river_spec_signature(spec),
        variant=variant,
        iterations=0,
        regrets={key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets},
        strategy_sum={key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets},
    )
    state.validate(spec, variant=variant)
    return state


def advance_river_solver(
    spec: RiverGameSpec,
    state: RiverSolverState,
    *,
    additional_iterations: int,
) -> RiverSolverState:
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec)
    if additional_iterations == 0:
        return state

    infosets = _all_infosets(spec)
    deals = _valid_deals(spec)
    total_chance = sum(weight for _, _, weight in deals)

    for offset in range(1, additional_iterations + 1):
        global_iteration = state.iterations + offset
        average_weight = (
            float(global_iteration) if state.variant.linear_average else 1.0
        )
        strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
        regret_delta = {key: [0.0] * len(state.regrets[key]) for key in infosets}
        strategy_delta = {key: [0.0] * len(state.regrets[key]) for key in infosets}

        for i, j, raw_weight in deals:
            _traverse_cfr(
                spec,
                i=i,
                j=j,
                chance=raw_weight / total_chance,
                strategies=strategies,
                regret_delta=regret_delta,
                strategy_delta=strategy_delta,
                average_weight=average_weight,
            )

        for key in infosets:
            for action_index in range(len(state.regrets[key])):
                regret = state.regrets[key][action_index] + regret_delta[key][action_index]
                if state.variant.clips_regrets:
                    regret = max(0.0, regret)
                state.regrets[key][action_index] = regret
                state.strategy_sum[key][action_index] += strategy_delta[key][action_index]

    state.iterations += additional_iterations
    state.validate(spec)
    return state


def river_solver_result(spec: RiverGameSpec, state: RiverSolverState) -> RiverSolveResult:
    state.validate(spec)
    if state.iterations <= 0:
        raise ValueError("cannot evaluate an untrained solver state")
    infosets = _all_infosets(spec)
    policy = _normalize_policy(spec, state.strategy_sum, state.regrets)
    policy_ev = evaluate_policy(spec, policy)
    br0, br1 = exact_best_response_values(spec, policy)
    exploitability = max(0.0, (br0 - br1) / 2.0)
    slots = sum(len(_actions(spec, key[0], key[1])) for key in infosets)
    return RiverSolveResult(
        iterations=state.iterations,
        policy=policy,
        policy_ev=policy_ev,
        br0_value=br0,
        br1_value=br1,
        exploitability=exploitability,
        exploitability_per_pot=exploitability / float(spec.pot),
        infosets=len(infosets),
        action_slots=slots,
    )


def solve_river_variant(
    spec: RiverGameSpec,
    *,
    variant: SolverVariant | str,
    iterations: int,
) -> RiverSolveResult:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    state = init_river_solver(spec, variant)
    advance_river_solver(spec, state, additional_iterations=iterations)
    return river_solver_result(spec, state)


def _encode_key(key: InfoKey) -> str:
    return f"{key[0]}\t{key[1]}\t{key[2]}"


def _decode_key(text: str) -> InfoKey:
    parts = text.split("\t")
    if len(parts) != 3:
        raise ValueError(f"invalid infoset key encoding: {text!r}")
    return int(parts[0]), parts[1], int(parts[2])


def _deep_tuple(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_deep_tuple(v) for v in value)
    return value


def river_solver_state_to_dict(state: RiverSolverState) -> dict[str, Any]:
    return {
        "schema": "DEEPCASH_RIVER_SOLVER_VARIANT_STATE_V1",
        "spec_signature": state.spec_signature,
        "variant": state.variant.value,
        "iterations": state.iterations,
        "regrets": {_encode_key(k): list(v) for k, v in sorted(state.regrets.items())},
        "strategy_sum": {
            _encode_key(k): list(v) for k, v in sorted(state.strategy_sum.items())
        },
    }


def river_solver_state_from_dict(
    spec: RiverGameSpec,
    payload: Mapping[str, Any],
    *,
    expected_variant: SolverVariant | str | None = None,
) -> RiverSolverState:
    if payload.get("schema") != "DEEPCASH_RIVER_SOLVER_VARIANT_STATE_V1":
        raise ValueError("unsupported river solver checkpoint schema")
    variant = SolverVariant(payload["variant"])
    if expected_variant is not None and variant != SolverVariant(expected_variant):
        raise ValueError("solver checkpoint variant does not match expected variant")
    state = RiverSolverState(
        spec_signature=_deep_tuple(payload["spec_signature"]),
        variant=variant,
        iterations=int(payload["iterations"]),
        regrets={
            _decode_key(key): [float(x) for x in values]
            for key, values in payload["regrets"].items()
        },
        strategy_sum={
            _decode_key(key): [float(x) for x in values]
            for key, values in payload["strategy_sum"].items()
        },
    )
    state.validate(spec, variant=variant)
    return state
