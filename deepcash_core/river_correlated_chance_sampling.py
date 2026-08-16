from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .river_external_sampling import _accumulate_exact_average
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
GOLDEN_ROTATION = (math.sqrt(5.0) - 1.0) / 2.0
CCS_VARIANT = "CCS_CFR_PLUS_LINEAR"


@dataclass
class CorrelatedChanceState:
    spec_signature: tuple
    variant: str
    seed: int
    iterations: int
    terminal_visits: int
    phase: float
    visit_index: int
    regrets: dict[InfoKey, list[float]]
    strategy_sum: dict[InfoKey, list[float]]

    def validate(self, spec: RiverGameSpec) -> None:
        if self.spec_signature != river_spec_signature(spec):
            raise ValueError("correlated-chance checkpoint belongs to another game")
        if self.variant != CCS_VARIANT:
            raise ValueError("unsupported correlated-chance variant")
        if self.iterations < 0 or self.terminal_visits < 0 or self.visit_index < 0:
            raise ValueError("iteration/visit counts cannot be negative")
        if self.visit_index != self.iterations:
            raise ValueError("root correlated-chance visit index must equal iterations")
        if not math.isfinite(self.phase) or not 0.0 <= self.phase < 1.0:
            raise ValueError("correlated-chance phase must be finite in [0,1)")

        expected = set(_all_infosets(spec))
        if set(self.regrets) != expected or set(self.strategy_sum) != expected:
            raise ValueError("correlated-chance infosets do not match game")
        for key in expected:
            n = len(_actions(spec, key[0], key[1]))
            if len(self.regrets[key]) != n or len(self.strategy_sum[key]) != n:
                raise ValueError(f"correlated-chance action shape mismatch at {key}")
            for value in (*self.regrets[key], *self.strategy_sum[key]):
                if not math.isfinite(value):
                    raise ValueError("correlated-chance checkpoint contains non-finite values")
            if any(value < 0.0 for value in self.regrets[key]):
                raise ValueError("CCS CFR+ regrets must remain non-negative")
            if any(value < 0.0 for value in self.strategy_sum[key]):
                raise ValueError("average-strategy sums cannot be negative")


def weyl_phase(phase: float, visit_index: int) -> float:
    if not math.isfinite(phase) or not 0.0 <= phase < 1.0:
        raise ValueError("phase must be finite in [0,1)")
    if visit_index < 0:
        raise ValueError("visit_index cannot be negative")
    return (phase + float(visit_index) * GOLDEN_ROTATION) % 1.0


def weighted_quantile_index(weights: Sequence[float], u: float) -> int:
    if not math.isfinite(u) or not 0.0 <= u < 1.0:
        raise ValueError("u must be finite in [0,1)")
    if not weights:
        raise ValueError("weights cannot be empty")
    checked = []
    for weight in weights:
        value = float(weight)
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("weights must be finite and non-negative")
        checked.append(value)
    total = sum(checked)
    if total <= 0.0:
        raise ValueError("weights must contain positive mass")

    target = u * total
    running = 0.0
    for index, weight in enumerate(checked):
        running += weight
        if target < running:
            return index
    # u < 1 by contract; this protects only against final floating-point drift.
    return len(checked) - 1


def correlated_deal_at(spec: RiverGameSpec, phase: float, visit_index: int) -> tuple[int, int]:
    deals = _valid_deals(spec)
    u = weyl_phase(phase, visit_index)
    index = weighted_quantile_index([weight for _, _, weight in deals], u)
    i, j, _ = deals[index]
    return i, j


def init_correlated_chance(spec: RiverGameSpec, *, seed: int) -> CorrelatedChanceState:
    rng = random.Random(int(seed))
    phase = rng.random()
    infosets = _all_infosets(spec)
    state = CorrelatedChanceState(
        spec_signature=river_spec_signature(spec),
        variant=CCS_VARIANT,
        seed=int(seed),
        iterations=0,
        terminal_visits=0,
        phase=phase,
        visit_index=0,
        regrets={key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets},
        strategy_sum={key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets},
    )
    state.validate(spec)
    return state


def advance_correlated_chance(
    spec: RiverGameSpec,
    state: CorrelatedChanceState,
    *,
    additional_iterations: int,
) -> CorrelatedChanceState:
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec)
    if additional_iterations == 0:
        return state

    infosets = _all_infosets(spec)
    terminal_leaves_per_deal = 1 + 4 * len(spec.bet_sizes)

    for offset in range(1, additional_iterations + 1):
        global_iteration = state.iterations + offset
        strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
        _accumulate_exact_average(
            spec,
            strategies,
            state.strategy_sum,
            weight=float(global_iteration),
        )

        i, j = correlated_deal_at(spec, state.phase, state.visit_index)
        regret_delta = {key: [0.0] * len(state.regrets[key]) for key in infosets}
        strategy_dummy = {key: [0.0] * len(state.regrets[key]) for key in infosets}
        _traverse_cfr(
            spec,
            i=i,
            j=j,
            chance=1.0,
            strategies=strategies,
            regret_delta=regret_delta,
            strategy_delta=strategy_dummy,
            average_weight=0.0,
        )

        for key in infosets:
            for a in range(len(state.regrets[key])):
                state.regrets[key][a] = max(
                    0.0, state.regrets[key][a] + regret_delta[key][a]
                )
        state.visit_index += 1
        state.terminal_visits += terminal_leaves_per_deal

    state.iterations += additional_iterations
    state.validate(spec)
    return state


def correlated_chance_result(
    spec: RiverGameSpec,
    state: CorrelatedChanceState,
) -> RiverSolveResult:
    state.validate(spec)
    if state.iterations <= 0:
        raise ValueError("cannot evaluate an untrained correlated-chance state")
    infosets = _all_infosets(spec)
    policy = _normalize_policy(spec, state.strategy_sum, state.regrets)
    policy_ev = evaluate_policy(spec, policy)
    br0, br1 = exact_best_response_values(spec, policy)
    exploitability = max(0.0, (br0 - br1) / 2.0)
    return RiverSolveResult(
        iterations=state.iterations,
        policy=policy,
        policy_ev=policy_ev,
        br0_value=br0,
        br1_value=br1,
        exploitability=exploitability,
        exploitability_per_pot=exploitability / float(spec.pot),
        infosets=len(infosets),
        action_slots=sum(len(_actions(spec, key[0], key[1])) for key in infosets),
    )


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


def correlated_chance_state_to_dict(state: CorrelatedChanceState) -> dict[str, Any]:
    return {
        "schema": "DEEPCASH_RIVER_CORRELATED_CHANCE_STATE_V1",
        "spec_signature": state.spec_signature,
        "variant": state.variant,
        "seed": state.seed,
        "iterations": state.iterations,
        "terminal_visits": state.terminal_visits,
        "phase": state.phase,
        "visit_index": state.visit_index,
        "regrets": {_encode_key(k): list(v) for k, v in sorted(state.regrets.items())},
        "strategy_sum": {
            _encode_key(k): list(v) for k, v in sorted(state.strategy_sum.items())
        },
    }


def correlated_chance_state_from_dict(
    spec: RiverGameSpec,
    payload: Mapping[str, Any],
) -> CorrelatedChanceState:
    if payload.get("schema") != "DEEPCASH_RIVER_CORRELATED_CHANCE_STATE_V1":
        raise ValueError("unsupported correlated-chance checkpoint schema")
    state = CorrelatedChanceState(
        spec_signature=_deep_tuple(payload["spec_signature"]),
        variant=str(payload["variant"]),
        seed=int(payload["seed"]),
        iterations=int(payload["iterations"]),
        terminal_visits=int(payload["terminal_visits"]),
        phase=float(payload["phase"]),
        visit_index=int(payload["visit_index"]),
        regrets={
            _decode_key(key): [float(x) for x in values]
            for key, values in payload["regrets"].items()
        },
        strategy_sum={
            _decode_key(key): [float(x) for x in values]
            for key, values in payload["strategy_sum"].items()
        },
    )
    state.validate(spec)
    return state
