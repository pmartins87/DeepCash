from __future__ import annotations

from dataclasses import dataclass
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

InfoKey = tuple[int, str, int]


def river_spec_signature(spec: RiverGameSpec) -> tuple:
    """Lossless signature preventing a checkpoint from being resumed on another game."""
    return (
        tuple(spec.board),
        tuple((tuple(c.hole), float(c.weight)) for c in spec.p0_range),
        tuple((tuple(c.hole), float(c.weight)) for c in spec.p1_range),
        int(spec.pot),
        tuple(spec.bet_sizes),
    )


@dataclass
class RiverCFRState:
    """Deterministic resumable synchronous CFR+ state for the river lab.

    `iterations` is the number of completed global iterations. Linear average
    weights therefore continue as N+1, N+2, ... after resume; staged training
    must be exactly equivalent to one monolithic run with the same total count.
    """

    spec_signature: tuple
    iterations: int
    regrets: dict[InfoKey, list[float]]
    strategy_sum: dict[InfoKey, list[float]]

    def validate(self, spec: RiverGameSpec) -> None:
        if self.spec_signature != river_spec_signature(spec):
            raise ValueError("CFR checkpoint belongs to a different river game spec")
        if self.iterations < 0:
            raise ValueError("iterations cannot be negative")
        expected = set(_all_infosets(spec))
        if set(self.regrets) != expected or set(self.strategy_sum) != expected:
            raise ValueError("CFR checkpoint infosets do not match game spec")
        for key in expected:
            n = len(_actions(spec, key[0], key[1]))
            if len(self.regrets[key]) != n or len(self.strategy_sum[key]) != n:
                raise ValueError(f"CFR checkpoint action shape mismatch at {key}")
            if any(r < 0.0 for r in self.regrets[key]):
                raise ValueError("CFR+ regrets must remain non-negative")


def init_river_cfr_plus(spec: RiverGameSpec) -> RiverCFRState:
    infosets = _all_infosets(spec)
    state = RiverCFRState(
        spec_signature=river_spec_signature(spec),
        iterations=0,
        regrets={k: [0.0] * len(_actions(spec, k[0], k[1])) for k in infosets},
        strategy_sum={k: [0.0] * len(_actions(spec, k[0], k[1])) for k in infosets},
    )
    state.validate(spec)
    return state


def advance_river_cfr_plus(
    spec: RiverGameSpec,
    state: RiverCFRState,
    *,
    additional_iterations: int,
) -> RiverCFRState:
    """Advance `state` in place and return it for convenient chaining."""
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec)
    if additional_iterations == 0:
        return state

    infosets = _all_infosets(spec)
    deals = _valid_deals(spec)
    total_chance = sum(w for _, _, w in deals)

    for offset in range(1, additional_iterations + 1):
        global_iteration = state.iterations + offset
        strategies = {k: _regret_strategy(state.regrets[k]) for k in infosets}
        regret_delta = {k: [0.0] * len(state.regrets[k]) for k in infosets}
        strategy_delta = {k: [0.0] * len(state.regrets[k]) for k in infosets}

        for i, j, raw_weight in deals:
            _traverse_cfr(
                spec,
                i=i,
                j=j,
                chance=raw_weight / total_chance,
                strategies=strategies,
                regret_delta=regret_delta,
                strategy_delta=strategy_delta,
                average_weight=float(global_iteration),
            )

        for key in infosets:
            for a in range(len(state.regrets[key])):
                state.regrets[key][a] = max(
                    0.0,
                    state.regrets[key][a] + regret_delta[key][a],
                )
                state.strategy_sum[key][a] += strategy_delta[key][a]

    state.iterations += additional_iterations
    state.validate(spec)
    return state


def river_result_from_state(spec: RiverGameSpec, state: RiverCFRState) -> RiverSolveResult:
    state.validate(spec)
    if state.iterations <= 0:
        raise ValueError("cannot evaluate an untrained CFR state")
    infosets = _all_infosets(spec)
    policy = _normalize_policy(spec, state.strategy_sum, state.regrets)
    policy_ev = evaluate_policy(spec, policy)
    br0, br1 = exact_best_response_values(spec, policy)
    exploitability = max(0.0, (br0 - br1) / 2.0)
    slots = sum(len(_actions(spec, k[0], k[1])) for k in infosets)
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


def _encode_key(key: InfoKey) -> str:
    return f"{key[0]}\t{key[1]}\t{key[2]}"


def _decode_key(text: str) -> InfoKey:
    parts = text.split("\t")
    if len(parts) != 3:
        raise ValueError(f"invalid infoset key encoding: {text!r}")
    return int(parts[0]), parts[1], int(parts[2])


def river_cfr_state_to_dict(state: RiverCFRState) -> dict[str, Any]:
    return {
        "schema": "DEEPCASH_RIVER_CFR_PLUS_STATE_V1",
        "spec_signature": state.spec_signature,
        "iterations": state.iterations,
        "regrets": {_encode_key(k): list(v) for k, v in sorted(state.regrets.items())},
        "strategy_sum": {
            _encode_key(k): list(v) for k, v in sorted(state.strategy_sum.items())
        },
    }


def _deep_tuple(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_deep_tuple(v) for v in value)
    return value


def river_cfr_state_from_dict(spec: RiverGameSpec, payload: Mapping[str, Any]) -> RiverCFRState:
    if payload.get("schema") != "DEEPCASH_RIVER_CFR_PLUS_STATE_V1":
        raise ValueError("unsupported river CFR checkpoint schema")
    state = RiverCFRState(
        spec_signature=_deep_tuple(payload["spec_signature"]),
        iterations=int(payload["iterations"]),
        regrets={
            _decode_key(k): [float(x) for x in v]
            for k, v in payload["regrets"].items()
        },
        strategy_sum={
            _decode_key(k): [float(x) for x in v]
            for k, v in payload["strategy_sum"].items()
        },
    )
    state.validate(spec)
    return state
