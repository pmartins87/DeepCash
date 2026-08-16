from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .river_lab import (
    RiverGameSpec,
    RiverSolveResult,
    _actions,
    _regret_strategy,
    _valid_deals,
    evaluate_policy,
)
from .river_representation_br import bucket_constrained_best_response_values
from .river_representation_lab import (
    RiverBucketMaps,
    _abstract_infosets,
    _expand_policy,
    _normalize_abstract_policy,
    _traverse_abstract_cfr,
)

InfoKey = tuple[int, str, int]


def representation_spec_signature(spec: RiverGameSpec, maps: RiverBucketMaps) -> tuple:
    maps.validate(spec)
    return (
        tuple(spec.board),
        tuple((tuple(c.hole), float(c.weight)) for c in spec.p0_range),
        tuple((tuple(c.hole), float(c.weight)) for c in spec.p1_range),
        int(spec.pot),
        tuple(spec.bet_sizes),
        tuple(maps.p0),
        tuple(maps.p1),
    )


@dataclass
class RiverRepresentationCFRState:
    spec_signature: tuple
    iterations: int
    regrets: dict[InfoKey, list[float]]
    strategy_sum: dict[InfoKey, list[float]]

    def validate(self, spec: RiverGameSpec, maps: RiverBucketMaps) -> None:
        maps.validate(spec)
        if self.spec_signature != representation_spec_signature(spec, maps):
            raise ValueError("representation CFR checkpoint belongs to a different spec/map")
        if self.iterations < 0:
            raise ValueError("iterations cannot be negative")
        expected = set(_abstract_infosets(spec, maps))
        if set(self.regrets) != expected or set(self.strategy_sum) != expected:
            raise ValueError("representation CFR checkpoint infosets do not match spec/map")
        for key in expected:
            n = len(_actions(spec, key[0], key[1]))
            if len(self.regrets[key]) != n or len(self.strategy_sum[key]) != n:
                raise ValueError(f"representation CFR action shape mismatch at {key}")
            if any(x < 0.0 for x in self.regrets[key]):
                raise ValueError("CFR+ regrets must remain non-negative")


def init_representation_cfr_plus(
    spec: RiverGameSpec, maps: RiverBucketMaps
) -> RiverRepresentationCFRState:
    infosets = _abstract_infosets(spec, maps)
    state = RiverRepresentationCFRState(
        spec_signature=representation_spec_signature(spec, maps),
        iterations=0,
        regrets={k: [0.0] * len(_actions(spec, k[0], k[1])) for k in infosets},
        strategy_sum={k: [0.0] * len(_actions(spec, k[0], k[1])) for k in infosets},
    )
    state.validate(spec, maps)
    return state


def advance_representation_cfr_plus(
    spec: RiverGameSpec,
    maps: RiverBucketMaps,
    state: RiverRepresentationCFRState,
    *,
    additional_iterations: int,
) -> RiverRepresentationCFRState:
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec, maps)
    if additional_iterations == 0:
        return state

    infosets = _abstract_infosets(spec, maps)
    deals = _valid_deals(spec)
    total_chance = sum(w for _, _, w in deals)
    for offset in range(1, additional_iterations + 1):
        global_iteration = state.iterations + offset
        strategies = {k: _regret_strategy(state.regrets[k]) for k in infosets}
        regret_delta = {k: [0.0] * len(state.regrets[k]) for k in infosets}
        strategy_delta = {k: [0.0] * len(state.regrets[k]) for k in infosets}
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
                average_weight=float(global_iteration),
            )
        for key in infosets:
            for a_idx in range(len(state.regrets[key])):
                state.regrets[key][a_idx] = max(
                    0.0,
                    state.regrets[key][a_idx] + regret_delta[key][a_idx],
                )
                state.strategy_sum[key][a_idx] += strategy_delta[key][a_idx]
    state.iterations += additional_iterations
    state.validate(spec, maps)
    return state


def representation_result_from_state(
    spec: RiverGameSpec,
    maps: RiverBucketMaps,
    state: RiverRepresentationCFRState,
) -> RiverSolveResult:
    """Evaluate the trained abstract game with BRs respecting the same buckets.

    The policy is expanded to exact combos for exact payoff evaluation, while
    each best responder is constrained to one pure action pattern per private
    bucket.  This makes `br0_value - br1_value` a convergence interval for the
    actual representation-restricted game instead of mixing abstraction loss
    into the interval by granting the responder information the solver did not
    have.
    """
    state.validate(spec, maps)
    if state.iterations <= 0:
        raise ValueError("cannot evaluate an untrained representation CFR state")
    infosets = _abstract_infosets(spec, maps)
    abstract_policy = _normalize_abstract_policy(
        spec, infosets, state.strategy_sum, state.regrets
    )
    policy = _expand_policy(spec, maps, abstract_policy)
    policy_ev = evaluate_policy(spec, policy)
    br0, br1 = bucket_constrained_best_response_values(spec, maps, policy)
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


def _encode_key(key: InfoKey) -> str:
    return f"{key[0]}\t{key[1]}\t{key[2]}"


def _decode_key(text: str) -> InfoKey:
    parts = text.split("\t")
    if len(parts) != 3:
        raise ValueError(f"invalid infoset key encoding: {text!r}")
    return int(parts[0]), parts[1], int(parts[2])


def state_to_dict(state: RiverRepresentationCFRState) -> dict[str, Any]:
    return {
        "schema": "DEEPCASH_RIVER_REPRESENTATION_CFR_PLUS_STATE_V1",
        "spec_signature": state.spec_signature,
        "iterations": state.iterations,
        "regrets": {_encode_key(k): list(v) for k, v in sorted(state.regrets.items())},
        "strategy_sum": {
            _encode_key(k): list(v) for k, v in sorted(state.strategy_sum.items())
        },
    }


def _deep_tuple(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_deep_tuple(x) for x in value)
    return value


def state_from_dict(
    spec: RiverGameSpec,
    maps: RiverBucketMaps,
    payload: Mapping[str, Any],
) -> RiverRepresentationCFRState:
    if payload.get("schema") != "DEEPCASH_RIVER_REPRESENTATION_CFR_PLUS_STATE_V1":
        raise ValueError("unsupported representation CFR checkpoint schema")
    state = RiverRepresentationCFRState(
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
    state.validate(spec, maps)
    return state
