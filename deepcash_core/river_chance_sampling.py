from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .river_external_sampling import _accumulate_exact_average, _sample_deal
from .river_lab import (
    RiverGameSpec,
    RiverSolveResult,
    _actions,
    _all_infosets,
    _normalize_policy,
    _regret_strategy,
    _traverse_cfr,
    evaluate_policy,
    exact_best_response_values,
)
from .river_training import river_spec_signature

InfoKey = tuple[int, str, int]


class ChanceSamplingVariant(str, Enum):
    CS_CFR_LINEAR = "CS_CFR_LINEAR"
    CS_CFR_PLUS_LINEAR = "CS_CFR_PLUS_LINEAR"

    @property
    def clips_regrets(self) -> bool:
        return self == self.CS_CFR_PLUS_LINEAR


@dataclass
class RiverChanceSamplingState:
    spec_signature: tuple
    variant: ChanceSamplingVariant
    seed: int
    iterations: int
    terminal_visits: int
    regrets: dict[InfoKey, list[float]]
    strategy_sum: dict[InfoKey, list[float]]
    rng_state: tuple

    def validate(
        self,
        spec: RiverGameSpec,
        *,
        variant: ChanceSamplingVariant | None = None,
    ) -> None:
        if self.spec_signature != river_spec_signature(spec):
            raise ValueError("chance-sampling checkpoint belongs to another game")
        if variant is not None and self.variant != variant:
            raise ValueError("chance-sampling checkpoint belongs to another variant")
        if self.iterations < 0 or self.terminal_visits < 0:
            raise ValueError("iteration/terminal counts cannot be negative")
        expected = set(_all_infosets(spec))
        if set(self.regrets) != expected or set(self.strategy_sum) != expected:
            raise ValueError("chance-sampling infosets do not match game")
        for key in expected:
            n = len(_actions(spec, key[0], key[1]))
            if len(self.regrets[key]) != n or len(self.strategy_sum[key]) != n:
                raise ValueError(f"chance-sampling action shape mismatch at {key}")
            for value in (*self.regrets[key], *self.strategy_sum[key]):
                if not math.isfinite(value):
                    raise ValueError("chance-sampling checkpoint contains non-finite values")
            if any(value < 0.0 for value in self.strategy_sum[key]):
                raise ValueError("average-strategy sums cannot be negative")
            if self.variant.clips_regrets and any(value < 0.0 for value in self.regrets[key]):
                raise ValueError("chance-sampling CFR+ regrets must be non-negative")
        rng = random.Random()
        try:
            rng.setstate(self.rng_state)
        except Exception as exc:  # pragma: no cover
            raise ValueError("invalid chance-sampling PRNG state") from exc


def init_chance_sampling(
    spec: RiverGameSpec,
    variant: ChanceSamplingVariant | str,
    *,
    seed: int,
) -> RiverChanceSamplingState:
    variant = ChanceSamplingVariant(variant)
    rng = random.Random(int(seed))
    infosets = _all_infosets(spec)
    state = RiverChanceSamplingState(
        spec_signature=river_spec_signature(spec),
        variant=variant,
        seed=int(seed),
        iterations=0,
        terminal_visits=0,
        regrets={key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets},
        strategy_sum={key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets},
        rng_state=rng.getstate(),
    )
    state.validate(spec, variant=variant)
    return state


def advance_chance_sampling(
    spec: RiverGameSpec,
    state: RiverChanceSamplingState,
    *,
    additional_iterations: int,
) -> RiverChanceSamplingState:
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec)
    if additional_iterations == 0:
        return state

    infosets = _all_infosets(spec)
    rng = random.Random()
    rng.setstate(state.rng_state)
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

        i, j = _sample_deal(spec, rng)
        regret_delta = {key: [0.0] * len(state.regrets[key]) for key in infosets}
        dummy_strategy_delta = {
            key: [0.0] * len(state.regrets[key]) for key in infosets
        }
        _traverse_cfr(
            spec,
            i=i,
            j=j,
            chance=1.0,
            strategies=strategies,
            regret_delta=regret_delta,
            strategy_delta=dummy_strategy_delta,
            average_weight=0.0,
        )

        for key in infosets:
            for a in range(len(state.regrets[key])):
                regret = state.regrets[key][a] + regret_delta[key][a]
                if state.variant.clips_regrets:
                    regret = max(0.0, regret)
                state.regrets[key][a] = regret
        state.terminal_visits += terminal_leaves_per_deal

    state.iterations += additional_iterations
    state.rng_state = rng.getstate()
    state.validate(spec)
    return state


def chance_sampling_result(
    spec: RiverGameSpec,
    state: RiverChanceSamplingState,
) -> RiverSolveResult:
    state.validate(spec)
    if state.iterations <= 0:
        raise ValueError("cannot evaluate an untrained chance-sampling state")
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


def chance_sampling_state_to_dict(state: RiverChanceSamplingState) -> dict[str, Any]:
    return {
        "schema": "DEEPCASH_RIVER_CHANCE_SAMPLING_STATE_V1",
        "spec_signature": state.spec_signature,
        "variant": state.variant.value,
        "seed": state.seed,
        "iterations": state.iterations,
        "terminal_visits": state.terminal_visits,
        "rng_state": state.rng_state,
        "regrets": {_encode_key(k): list(v) for k, v in sorted(state.regrets.items())},
        "strategy_sum": {
            _encode_key(k): list(v) for k, v in sorted(state.strategy_sum.items())
        },
    }


def chance_sampling_state_from_dict(
    spec: RiverGameSpec,
    payload: Mapping[str, Any],
    *,
    expected_variant: ChanceSamplingVariant | str | None = None,
) -> RiverChanceSamplingState:
    if payload.get("schema") != "DEEPCASH_RIVER_CHANCE_SAMPLING_STATE_V1":
        raise ValueError("unsupported chance-sampling checkpoint schema")
    variant = ChanceSamplingVariant(payload["variant"])
    if expected_variant is not None and variant != ChanceSamplingVariant(expected_variant):
        raise ValueError("chance-sampling checkpoint variant mismatch")
    state = RiverChanceSamplingState(
        spec_signature=_deep_tuple(payload["spec_signature"]),
        variant=variant,
        seed=int(payload["seed"]),
        iterations=int(payload["iterations"]),
        terminal_visits=int(payload["terminal_visits"]),
        rng_state=_deep_tuple(payload["rng_state"]),
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
