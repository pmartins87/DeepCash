from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .river_lab import RiverSolveResult
from .river_raise_reference_dp import exact_best_response_values_dp
from .river_raise_reference_lab import (
    AsymmetricRiverRaiseGameSpec,
    _deal_value,
    _normalize_policy,
    _regret_strategy,
    _traverse_cfr,
    actions,
    all_infosets,
    valid_deals,
)

InfoKey = tuple[int, str, int]


def spec_signature(spec: AsymmetricRiverRaiseGameSpec) -> tuple:
    return (
        tuple(spec.board),
        tuple((tuple(c.hole), float(c.weight)) for c in spec.p0_range),
        tuple((tuple(c.hole), float(c.weight)) for c in spec.p1_range),
        int(spec.pot),
        tuple(spec.p0_bet_sizes),
        tuple(spec.p1_bet_sizes),
        tuple((int(b), tuple(int(x) for x in targets)) for b, targets in spec.p1_raise_targets_vs_p0),
        tuple((int(b), tuple(int(x) for x in targets)) for b, targets in spec.p0_raise_targets_vs_p1),
    )


@dataclass
class AsymmetricRiverRaiseCFRState:
    spec_signature: tuple
    iterations: int
    regrets: dict[InfoKey, list[float]]
    strategy_sum: dict[InfoKey, list[float]]

    def validate(self, spec: AsymmetricRiverRaiseGameSpec) -> None:
        if self.spec_signature != spec_signature(spec):
            raise ValueError("CFR checkpoint belongs to a different one-raise river game spec")
        if self.iterations < 0:
            raise ValueError("iterations cannot be negative")
        expected = set(all_infosets(spec))
        if set(self.regrets) != expected or set(self.strategy_sum) != expected:
            raise ValueError("CFR checkpoint infosets do not match game spec")
        for key in expected:
            n = len(actions(spec, key[0], key[1]))
            if len(self.regrets[key]) != n or len(self.strategy_sum[key]) != n:
                raise ValueError(f"CFR checkpoint action shape mismatch at {key}")
            if any(x < 0.0 for x in self.regrets[key]):
                raise ValueError("CFR+ regrets must remain non-negative")


def init_cfr_plus(spec: AsymmetricRiverRaiseGameSpec) -> AsymmetricRiverRaiseCFRState:
    infosets = all_infosets(spec)
    state = AsymmetricRiverRaiseCFRState(
        spec_signature=spec_signature(spec),
        iterations=0,
        regrets={k: [0.0] * len(actions(spec, k[0], k[1])) for k in infosets},
        strategy_sum={k: [0.0] * len(actions(spec, k[0], k[1])) for k in infosets},
    )
    state.validate(spec)
    return state


def advance_cfr_plus(
    spec: AsymmetricRiverRaiseGameSpec,
    state: AsymmetricRiverRaiseCFRState,
    *,
    additional_iterations: int,
) -> AsymmetricRiverRaiseCFRState:
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec)
    if additional_iterations == 0:
        return state

    infosets = all_infosets(spec)
    deals = valid_deals(spec)
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
            for a_idx in range(len(state.regrets[key])):
                state.regrets[key][a_idx] = max(
                    0.0,
                    state.regrets[key][a_idx] + regret_delta[key][a_idx],
                )
                state.strategy_sum[key][a_idx] += strategy_delta[key][a_idx]
    state.iterations += additional_iterations
    state.validate(spec)
    return state


def result_from_state(
    spec: AsymmetricRiverRaiseGameSpec,
    state: AsymmetricRiverRaiseCFRState,
) -> RiverSolveResult:
    state.validate(spec)
    if state.iterations <= 0:
        raise ValueError("cannot evaluate an untrained CFR state")
    infosets = all_infosets(spec)
    policy = _normalize_policy(spec, state.strategy_sum, state.regrets)
    deals = valid_deals(spec)
    total = sum(w for _, _, w in deals)
    policy_ev = sum(w * _deal_value(spec, i, j, policy) for i, j, w in deals) / total
    br0, br1 = exact_best_response_values_dp(spec, policy)
    exploitability = max(0.0, (br0 - br1) / 2.0)
    slots = sum(len(actions(spec, key[0], key[1])) for key in infosets)
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


def state_to_dict(state: AsymmetricRiverRaiseCFRState) -> dict[str, Any]:
    return {
        "schema": "DEEPCASH_ASYMMETRIC_RIVER_RAISE_CFR_PLUS_STATE_V1",
        "spec_signature": state.spec_signature,
        "iterations": state.iterations,
        "regrets": {_encode_key(k): list(v) for k, v in sorted(state.regrets.items())},
        "strategy_sum": {_encode_key(k): list(v) for k, v in sorted(state.strategy_sum.items())},
    }


def _deep_tuple(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_deep_tuple(x) for x in value)
    return value


def state_from_dict(
    spec: AsymmetricRiverRaiseGameSpec,
    payload: Mapping[str, Any],
) -> AsymmetricRiverRaiseCFRState:
    if payload.get("schema") != "DEEPCASH_ASYMMETRIC_RIVER_RAISE_CFR_PLUS_STATE_V1":
        raise ValueError("unsupported one-raise CFR checkpoint schema")
    state = AsymmetricRiverRaiseCFRState(
        spec_signature=_deep_tuple(payload["spec_signature"]),
        iterations=int(payload["iterations"]),
        regrets={_decode_key(k): [float(x) for x in v] for k, v in payload["regrets"].items()},
        strategy_sum={_decode_key(k): [float(x) for x in v] for k, v in payload["strategy_sum"].items()},
    )
    state.validate(spec)
    return state
