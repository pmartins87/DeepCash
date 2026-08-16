from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .river_external_sampling import _external_traverse, _sample_deal
from .river_lab import (
    P1_AFTER_CHECK,
    ROOT,
    RiverGameSpec,
    RiverSolveResult,
    _actions,
    _all_infosets,
    _normalize_policy,
    _regret_strategy,
    evaluate_policy,
    exact_best_response_values,
    p0_vs_bet_node,
    p1_vs_bet_node,
)
from .river_training import river_spec_signature

InfoKey = tuple[int, str, int]


class AlternatingExternalVariant(str, Enum):
    ALT_ES_CFR_UNIFORM = "ALT_ES_CFR_UNIFORM"
    ALT_ES_CFR_LINEAR_AVG = "ALT_ES_CFR_LINEAR_AVG"
    ALT_ES_LCFR = "ALT_ES_LCFR"

    @property
    def average_linear(self) -> bool:
        return self in {self.ALT_ES_CFR_LINEAR_AVG, self.ALT_ES_LCFR}

    @property
    def regret_linear(self) -> bool:
        return self == self.ALT_ES_LCFR


@dataclass
class AlternatingExternalState:
    spec_signature: tuple
    variant: AlternatingExternalVariant
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
        variant: AlternatingExternalVariant | None = None,
    ) -> None:
        if self.spec_signature != river_spec_signature(spec):
            raise ValueError("alternating external checkpoint belongs to another game")
        if variant is not None and self.variant != variant:
            raise ValueError("alternating external checkpoint belongs to another variant")
        if self.iterations < 0 or self.terminal_visits < 0:
            raise ValueError("iteration/terminal counts cannot be negative")
        expected = set(_all_infosets(spec))
        if set(self.regrets) != expected or set(self.strategy_sum) != expected:
            raise ValueError("alternating external infosets do not match game")
        for key in expected:
            n = len(_actions(spec, key[0], key[1]))
            if len(self.regrets[key]) != n or len(self.strategy_sum[key]) != n:
                raise ValueError(f"alternating external action shape mismatch at {key}")
            for value in (*self.regrets[key], *self.strategy_sum[key]):
                if not math.isfinite(value):
                    raise ValueError("alternating external checkpoint contains non-finite values")
            if any(value < 0.0 for value in self.strategy_sum[key]):
                raise ValueError("average-strategy sums cannot be negative")
        rng = random.Random()
        try:
            rng.setstate(self.rng_state)
        except Exception as exc:  # pragma: no cover
            raise ValueError("invalid alternating external PRNG state") from exc


def init_alternating_external(
    spec: RiverGameSpec,
    variant: AlternatingExternalVariant | str,
    *,
    seed: int,
) -> AlternatingExternalState:
    variant = AlternatingExternalVariant(variant)
    infosets = _all_infosets(spec)
    rng = random.Random(int(seed))
    state = AlternatingExternalState(
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


def _accumulate_player_average(
    spec: RiverGameSpec,
    state: AlternatingExternalState,
    strategies: Mapping[InfoKey, tuple[float, ...]],
    *,
    player: int,
    iteration: int,
) -> None:
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    if iteration <= 0:
        raise ValueError("iteration must be positive")
    weight = float(iteration) if state.variant.average_linear else 1.0

    if player == 0:
        root_actions = _actions(spec, 0, ROOT)
        check_index = root_actions.index("CHECK")
        for i in range(len(spec.p0_range)):
            root = (0, ROOT, i)
            root_sigma = strategies[root]
            for a, probability in enumerate(root_sigma):
                state.strategy_sum[root][a] += weight * probability
            check_reach = root_sigma[check_index]
            for bet in spec.bet_sizes:
                key = (0, p0_vs_bet_node(bet), i)
                for a, probability in enumerate(strategies[key]):
                    state.strategy_sum[key][a] += weight * check_reach * probability
        return

    for j in range(len(spec.p1_range)):
        key = (1, P1_AFTER_CHECK, j)
        for a, probability in enumerate(strategies[key]):
            state.strategy_sum[key][a] += weight * probability
        for bet in spec.bet_sizes:
            key = (1, p1_vs_bet_node(bet), j)
            for a, probability in enumerate(strategies[key]):
                state.strategy_sum[key][a] += weight * probability


def _apply_player_regrets(
    state: AlternatingExternalState,
    regret_delta: Mapping[InfoKey, list[float]],
    *,
    player: int,
    iteration: int,
) -> None:
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    scale = float(iteration) if state.variant.regret_linear else 1.0
    for key, values in state.regrets.items():
        if key[0] != player:
            continue
        for a in range(len(values)):
            values[a] += scale * regret_delta[key][a]


def advance_alternating_external(
    spec: RiverGameSpec,
    state: AlternatingExternalState,
    *,
    additional_iterations: int,
) -> AlternatingExternalState:
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec)
    if additional_iterations == 0:
        return state

    infosets = _all_infosets(spec)
    rng = random.Random()
    rng.setstate(state.rng_state)

    for offset in range(1, additional_iterations + 1):
        iteration = state.iterations + offset
        for player in (0, 1):
            strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
            _accumulate_player_average(
                spec,
                state,
                strategies,
                player=player,
                iteration=iteration,
            )

            i, j = _sample_deal(spec, rng)
            regret_delta = {
                key: [0.0] * len(state.regrets[key]) for key in infosets
            }
            counter = [0]
            _external_traverse(
                spec,
                i=i,
                j=j,
                traverser=player,
                rng=rng,
                strategies=strategies,
                regret_delta=regret_delta,
                counter=counter,
            )
            _apply_player_regrets(
                state,
                regret_delta,
                player=player,
                iteration=iteration,
            )
            state.terminal_visits += counter[0]

    state.iterations += additional_iterations
    state.rng_state = rng.getstate()
    state.validate(spec)
    return state


def alternating_external_result(
    spec: RiverGameSpec,
    state: AlternatingExternalState,
) -> RiverSolveResult:
    state.validate(spec)
    if state.iterations <= 0:
        raise ValueError("cannot evaluate an untrained alternating external state")
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


def alternating_external_state_to_dict(state: AlternatingExternalState) -> dict[str, Any]:
    return {
        "schema": "DEEPCASH_RIVER_ALTERNATING_EXTERNAL_LCFR_STATE_V1",
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


def alternating_external_state_from_dict(
    spec: RiverGameSpec,
    payload: Mapping[str, Any],
    *,
    expected_variant: AlternatingExternalVariant | str | None = None,
) -> AlternatingExternalState:
    if payload.get("schema") != "DEEPCASH_RIVER_ALTERNATING_EXTERNAL_LCFR_STATE_V1":
        raise ValueError("unsupported alternating external checkpoint schema")
    variant = AlternatingExternalVariant(payload["variant"])
    if expected_variant is not None and variant != AlternatingExternalVariant(expected_variant):
        raise ValueError("alternating external checkpoint variant mismatch")
    state = AlternatingExternalState(
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
