from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from .river_lab import (
    P1_AFTER_CHECK,
    ROOT,
    RiverGameSpec,
    RiverSolveResult,
    _actions,
    _all_infosets,
    _bet_amount,
    _normalize_policy,
    _regret_strategy,
    _terminal_showdown,
    _valid_deals,
    evaluate_policy,
    exact_best_response_values,
    p0_vs_bet_node,
    p1_vs_bet_node,
)
from .river_training import river_spec_signature

InfoKey = tuple[int, str, int]


class ExternalSamplingVariant(str, Enum):
    ES_CFR_LINEAR = "ES_CFR_LINEAR"
    ES_CFR_PLUS_LINEAR = "ES_CFR_PLUS_LINEAR"

    @property
    def clips_regrets(self) -> bool:
        return self == self.ES_CFR_PLUS_LINEAR


@dataclass
class RiverExternalSamplingState:
    spec_signature: tuple
    variant: ExternalSamplingVariant
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
        variant: ExternalSamplingVariant | None = None,
    ) -> None:
        if self.spec_signature != river_spec_signature(spec):
            raise ValueError("external-sampling checkpoint belongs to another game")
        if variant is not None and self.variant != variant:
            raise ValueError("external-sampling checkpoint belongs to another variant")
        if self.iterations < 0 or self.terminal_visits < 0:
            raise ValueError("iteration/terminal counts cannot be negative")
        expected = set(_all_infosets(spec))
        if set(self.regrets) != expected or set(self.strategy_sum) != expected:
            raise ValueError("external-sampling infosets do not match game")
        for key in expected:
            n = len(_actions(spec, key[0], key[1]))
            if len(self.regrets[key]) != n or len(self.strategy_sum[key]) != n:
                raise ValueError(f"external-sampling action shape mismatch at {key}")
            for value in (*self.regrets[key], *self.strategy_sum[key]):
                if not math.isfinite(value):
                    raise ValueError("external-sampling checkpoint contains non-finite values")
            if any(value < 0.0 for value in self.strategy_sum[key]):
                raise ValueError("average-strategy sums cannot be negative")
            if self.variant.clips_regrets and any(value < 0.0 for value in self.regrets[key]):
                raise ValueError("external-sampling CFR+ regrets must be non-negative")
        rng = random.Random()
        try:
            rng.setstate(self.rng_state)
        except Exception as exc:  # pragma: no cover - implementation-specific exception
            raise ValueError("invalid external-sampling PRNG state") from exc


def init_external_sampling(
    spec: RiverGameSpec,
    variant: ExternalSamplingVariant | str,
    *,
    seed: int,
) -> RiverExternalSamplingState:
    variant = ExternalSamplingVariant(variant)
    rng = random.Random(int(seed))
    infosets = _all_infosets(spec)
    state = RiverExternalSamplingState(
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


def _weighted_choice_index(rng: random.Random, weights: Sequence[float]) -> int:
    if not weights or any((not math.isfinite(w) or w < 0.0) for w in weights):
        raise ValueError("sampling weights must be finite and non-negative")
    total = sum(weights)
    if total <= 0.0:
        raise ValueError("sampling weights must have positive mass")
    target = rng.random() * total
    running = 0.0
    for idx, weight in enumerate(weights):
        running += weight
        if target < running:
            return idx
    return len(weights) - 1


def _sample_deal(spec: RiverGameSpec, rng: random.Random) -> tuple[int, int]:
    deals = _valid_deals(spec)
    idx = _weighted_choice_index(rng, [weight for _, _, weight in deals])
    i, j, _ = deals[idx]
    return i, j


def _accumulate_exact_average(
    spec: RiverGameSpec,
    strategies: Mapping[InfoKey, tuple[float, ...]],
    strategy_sum: dict[InfoKey, list[float]],
    *,
    weight: float,
) -> None:
    """Accumulate exact own-reach average strategy for the small river tree.

    Chance/private-hand occurrence mass is constant for a given infoset across
    iterations and cancels during per-infoset normalization. P1 has no prior own
    action before any of its infosets. P0 reaches a response-to-P1-bet infoset
    only through its own root CHECK, so that root probability is the only own
    realization reach below root.
    """
    if weight <= 0.0 or not math.isfinite(weight):
        raise ValueError("average weight must be finite and positive")

    for i in range(len(spec.p0_range)):
        root = (0, ROOT, i)
        root_sigma = strategies[root]
        for a, probability in enumerate(root_sigma):
            strategy_sum[root][a] += weight * probability
        check_reach = root_sigma[_actions(spec, 0, ROOT).index("CHECK")]
        for bet in spec.bet_sizes:
            key = (0, p0_vs_bet_node(bet), i)
            for a, probability in enumerate(strategies[key]):
                strategy_sum[key][a] += weight * check_reach * probability

    for j in range(len(spec.p1_range)):
        root = (1, P1_AFTER_CHECK, j)
        for a, probability in enumerate(strategies[root]):
            strategy_sum[root][a] += weight * probability
        for bet in spec.bet_sizes:
            key = (1, p1_vs_bet_node(bet), j)
            for a, probability in enumerate(strategies[key]):
                strategy_sum[key][a] += weight * probability


def _external_traverse(
    spec: RiverGameSpec,
    *,
    i: int,
    j: int,
    traverser: int,
    rng: random.Random,
    strategies: Mapping[InfoKey, tuple[float, ...]],
    regret_delta: dict[InfoKey, list[float]],
    counter: list[int],
    node: str = ROOT,
    player: int = 0,
) -> float:
    hand_index = i if player == 0 else j
    key = (player, node, hand_index)
    actions = _actions(spec, player, node)
    sigma = strategies[key]

    def descend(action: str) -> float:
        if player == 0 and node == ROOT:
            if action == "CHECK":
                return _external_traverse(
                    spec,
                    i=i,
                    j=j,
                    traverser=traverser,
                    rng=rng,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    counter=counter,
                    node=P1_AFTER_CHECK,
                    player=1,
                )
            return _external_traverse(
                spec,
                i=i,
                j=j,
                traverser=traverser,
                rng=rng,
                strategies=strategies,
                regret_delta=regret_delta,
                counter=counter,
                node=p1_vs_bet_node(_bet_amount(action)),
                player=1,
            )

        if player == 1 and node == P1_AFTER_CHECK:
            if action == "CHECK":
                counter[0] += 1
                return _terminal_showdown(spec, i, j)
            return _external_traverse(
                spec,
                i=i,
                j=j,
                traverser=traverser,
                rng=rng,
                strategies=strategies,
                regret_delta=regret_delta,
                counter=counter,
                node=p0_vs_bet_node(_bet_amount(action)),
                player=0,
            )

        if player == 1 and node.startswith("P1_VS_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            counter[0] += 1
            if action == "FOLD":
                return float(spec.pot) / 2.0
            return _terminal_showdown(spec, i, j, amount)

        if player == 0 and node.startswith("P0_VS_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            counter[0] += 1
            if action == "FOLD":
                return -float(spec.pot) / 2.0
            return _terminal_showdown(spec, i, j, amount)

        raise AssertionError((player, node, action))  # pragma: no cover

    if player == traverser:
        action_values = [descend(action) for action in actions]
        node_value = sum(prob * value for prob, value in zip(sigma, action_values))
        direction = 1.0 if traverser == 0 else -1.0
        for a, value in enumerate(action_values):
            regret_delta[key][a] += direction * (value - node_value)
        return node_value

    sampled = _weighted_choice_index(rng, sigma)
    return descend(actions[sampled])


def advance_external_sampling(
    spec: RiverGameSpec,
    state: RiverExternalSamplingState,
    *,
    additional_iterations: int,
) -> RiverExternalSamplingState:
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec)
    if additional_iterations == 0:
        return state

    infosets = _all_infosets(spec)
    rng = random.Random()
    rng.setstate(state.rng_state)

    for offset in range(1, additional_iterations + 1):
        global_iteration = state.iterations + offset
        strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
        _accumulate_exact_average(
            spec,
            strategies,
            state.strategy_sum,
            weight=float(global_iteration),
        )
        regret_delta = {key: [0.0] * len(state.regrets[key]) for key in infosets}
        counter = [0]

        # Both traversers use the same pre-update strategy snapshot. Chance and
        # opponent actions are independently sampled from one deterministic RNG
        # stream; all traverser actions are enumerated.
        for traverser in (0, 1):
            i, j = _sample_deal(spec, rng)
            _external_traverse(
                spec,
                i=i,
                j=j,
                traverser=traverser,
                rng=rng,
                strategies=strategies,
                regret_delta=regret_delta,
                counter=counter,
            )

        for key in infosets:
            for a in range(len(state.regrets[key])):
                regret = state.regrets[key][a] + regret_delta[key][a]
                if state.variant.clips_regrets:
                    regret = max(0.0, regret)
                state.regrets[key][a] = regret
        state.terminal_visits += counter[0]

    state.iterations += additional_iterations
    state.rng_state = rng.getstate()
    state.validate(spec)
    return state


def external_sampling_result(
    spec: RiverGameSpec,
    state: RiverExternalSamplingState,
) -> RiverSolveResult:
    state.validate(spec)
    if state.iterations <= 0:
        raise ValueError("cannot evaluate an untrained external-sampling state")
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


def external_sampling_state_to_dict(state: RiverExternalSamplingState) -> dict[str, Any]:
    return {
        "schema": "DEEPCASH_RIVER_EXTERNAL_SAMPLING_STATE_V1",
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


def external_sampling_state_from_dict(
    spec: RiverGameSpec,
    payload: Mapping[str, Any],
    *,
    expected_variant: ExternalSamplingVariant | str | None = None,
) -> RiverExternalSamplingState:
    if payload.get("schema") != "DEEPCASH_RIVER_EXTERNAL_SAMPLING_STATE_V1":
        raise ValueError("unsupported external-sampling checkpoint schema")
    variant = ExternalSamplingVariant(payload["variant"])
    if expected_variant is not None and variant != ExternalSamplingVariant(expected_variant):
        raise ValueError("external-sampling checkpoint variant mismatch")
    state = RiverExternalSamplingState(
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
