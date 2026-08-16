from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Mapping

from .river_external_sampling import (
    ExternalSamplingVariant,
    InfoKey,
    RiverExternalSamplingState,
    WeightedDealSampler,
    _accumulate_exact_average,
    _sample_deal,
    _weighted_choice_index,
    external_sampling_result,
    external_sampling_state_from_dict,
    external_sampling_state_to_dict,
    init_external_sampling,
)
from .river_lab import (
    P1_AFTER_CHECK,
    ROOT,
    RiverGameSpec,
    RiverSolveResult,
    _actions,
    _all_infosets,
    _bet_amount,
    _regret_strategy,
    _terminal_showdown,
    p0_vs_bet_node,
    p1_vs_bet_node,
)
from .vr_mccfr_baseline import baseline_enhanced_node_value


BaselineKey = tuple[int, int, int, str]


@dataclass
class RiverTabularVRState:
    """External-sampling state plus legal-information running baselines.

    Baseline keys are `(traverser, traverser_hand_index, acting_player,
    public_node)`.  In particular there is no realized opponent-hand index.
    Every action at that public node has its own running mean and count.
    """

    base: RiverExternalSamplingState
    baseline_mean: dict[BaselineKey, list[float]]
    baseline_count: dict[BaselineKey, list[int]]

    def validate(self, spec: RiverGameSpec) -> None:
        self.base.validate(spec)
        expected = set(_expected_baseline_keys(spec))
        if set(self.baseline_mean) != expected or set(self.baseline_count) != expected:
            raise ValueError("tabular baseline keys do not match game")
        for key in expected:
            traverser, own_hand, player, node = key
            if traverser not in (0, 1) or player != 1 - traverser:
                raise ValueError("baseline key must describe a non-traverser node")
            own_count = len(spec.p0_range) if traverser == 0 else len(spec.p1_range)
            if not 0 <= own_hand < own_count:
                raise ValueError("baseline own-hand index outside traverser range")
            n_actions = len(_actions(spec, player, node))
            means = self.baseline_mean[key]
            counts = self.baseline_count[key]
            if len(means) != n_actions or len(counts) != n_actions:
                raise ValueError("tabular baseline action shape mismatch")
            if any(not math.isfinite(value) for value in means):
                raise ValueError("tabular baseline contains non-finite mean")
            if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts):
                raise ValueError("tabular baseline counts must be non-negative integers")


def _expected_baseline_keys(spec: RiverGameSpec) -> tuple[BaselineKey, ...]:
    keys: list[BaselineKey] = []
    # Traverser P0: every opponent decision is by P1.
    p1_nodes = (P1_AFTER_CHECK, *(p1_vs_bet_node(bet) for bet in spec.bet_sizes))
    for i in range(len(spec.p0_range)):
        for node in p1_nodes:
            keys.append((0, i, 1, node))

    # Traverser P1: every opponent decision is by P0.
    p0_nodes = (ROOT, *(p0_vs_bet_node(bet) for bet in spec.bet_sizes))
    for j in range(len(spec.p1_range)):
        for node in p0_nodes:
            keys.append((1, j, 0, node))
    return tuple(keys)


def init_tabular_vr(
    spec: RiverGameSpec,
    variant: ExternalSamplingVariant | str,
    *,
    seed: int,
) -> RiverTabularVRState:
    base = init_external_sampling(spec, variant, seed=seed)
    means: dict[BaselineKey, list[float]] = {}
    counts: dict[BaselineKey, list[int]] = {}
    for key in _expected_baseline_keys(spec):
        _, _, player, node = key
        n = len(_actions(spec, player, node))
        means[key] = [0.0] * n
        counts[key] = [0] * n
    state = RiverTabularVRState(base=base, baseline_mean=means, baseline_count=counts)
    state.validate(spec)
    return state


def _estimate_then_update_running_baseline(
    *,
    sigma: tuple[float, ...],
    means: list[float],
    counts: list[int],
    sampled_action: int,
    sampled_child_value: float,
) -> float:
    """Use the pre-sample table as control variate, then learn from the sample."""
    frozen = tuple(means)
    estimate = baseline_enhanced_node_value(
        target_policy=sigma,
        sampling_policy=sigma,
        baselines=frozen,
        sampled_action=sampled_action,
        sampled_child_value=sampled_child_value,
    )

    # Update strictly after the estimator has consumed the old baseline. A
    # current-sample-updated baseline would make the control variate depend on
    # the same random draw it is correcting and would invalidate the intended
    # martingale/unbiasedness contract.
    old_count = counts[sampled_action]
    new_count = old_count + 1
    old_mean = means[sampled_action]
    means[sampled_action] = old_mean + (
        float(sampled_child_value) - old_mean
    ) / float(new_count)
    counts[sampled_action] = new_count
    return estimate


def _tabular_traverse(
    spec: RiverGameSpec,
    *,
    i: int,
    j: int,
    traverser: int,
    rng: random.Random,
    strategies: Mapping[InfoKey, tuple[float, ...]],
    regret_delta: dict[InfoKey, list[float]],
    counter: list[int],
    baseline_mean: dict[BaselineKey, list[float]],
    baseline_count: dict[BaselineKey, list[int]],
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
                return _tabular_traverse(
                    spec,
                    i=i,
                    j=j,
                    traverser=traverser,
                    rng=rng,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    counter=counter,
                    baseline_mean=baseline_mean,
                    baseline_count=baseline_count,
                    node=P1_AFTER_CHECK,
                    player=1,
                )
            return _tabular_traverse(
                spec,
                i=i,
                j=j,
                traverser=traverser,
                rng=rng,
                strategies=strategies,
                regret_delta=regret_delta,
                counter=counter,
                baseline_mean=baseline_mean,
                baseline_count=baseline_count,
                node=p1_vs_bet_node(_bet_amount(action)),
                player=1,
            )

        if player == 1 and node == P1_AFTER_CHECK:
            if action == "CHECK":
                counter[0] += 1
                return _terminal_showdown(spec, i, j)
            return _tabular_traverse(
                spec,
                i=i,
                j=j,
                traverser=traverser,
                rng=rng,
                strategies=strategies,
                regret_delta=regret_delta,
                counter=counter,
                baseline_mean=baseline_mean,
                baseline_count=baseline_count,
                node=p0_vs_bet_node(_bet_amount(action)),
                player=0,
            )

        if player == 1 and node.startswith("P1_VS_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            counter[0] += 1
            return (
                float(spec.pot) / 2.0
                if action == "FOLD"
                else _terminal_showdown(spec, i, j, amount)
            )

        if player == 0 and node.startswith("P0_VS_BET_"):
            amount = int(node.rsplit("_", 1)[1])
            counter[0] += 1
            return (
                -float(spec.pot) / 2.0
                if action == "FOLD"
                else _terminal_showdown(spec, i, j, amount)
            )

        raise AssertionError((player, node, action))  # pragma: no cover

    if player == traverser:
        action_values = [descend(action) for action in actions]
        node_value = sum(prob * value for prob, value in zip(sigma, action_values))
        direction = 1.0 if traverser == 0 else -1.0
        for a, value in enumerate(action_values):
            regret_delta[key][a] += direction * (value - node_value)
        return node_value

    sampled = _weighted_choice_index(rng, sigma)
    sampled_child = descend(actions[sampled])
    own_hand = i if traverser == 0 else j
    baseline_key = (traverser, own_hand, player, node)
    return _estimate_then_update_running_baseline(
        sigma=sigma,
        means=baseline_mean[baseline_key],
        counts=baseline_count[baseline_key],
        sampled_action=sampled,
        sampled_child_value=sampled_child,
    )


def advance_tabular_vr(
    spec: RiverGameSpec,
    state: RiverTabularVRState,
    *,
    additional_iterations: int,
) -> RiverTabularVRState:
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec)
    if additional_iterations == 0:
        return state

    infosets = _all_infosets(spec)
    sampler = WeightedDealSampler.from_spec(spec)
    rng = random.Random()
    rng.setstate(state.base.rng_state)

    for offset in range(1, additional_iterations + 1):
        global_iteration = state.base.iterations + offset
        strategies = {
            key: _regret_strategy(state.base.regrets[key]) for key in infosets
        }
        _accumulate_exact_average(
            spec,
            strategies,
            state.base.strategy_sum,
            weight=float(global_iteration),
        )
        regret_delta = {
            key: [0.0] * len(state.base.regrets[key]) for key in infosets
        }
        counter = [0]

        for traverser in (0, 1):
            i, j = _sample_deal(spec, rng, sampler)
            _tabular_traverse(
                spec,
                i=i,
                j=j,
                traverser=traverser,
                rng=rng,
                strategies=strategies,
                regret_delta=regret_delta,
                counter=counter,
                baseline_mean=state.baseline_mean,
                baseline_count=state.baseline_count,
            )

        for key in infosets:
            for action_index in range(len(state.base.regrets[key])):
                regret = state.base.regrets[key][action_index] + regret_delta[key][action_index]
                if state.base.variant.clips_regrets:
                    regret = max(0.0, regret)
                state.base.regrets[key][action_index] = regret
        state.base.terminal_visits += counter[0]

    state.base.iterations += additional_iterations
    state.base.rng_state = rng.getstate()
    state.validate(spec)
    return state


def tabular_vr_result(spec: RiverGameSpec, state: RiverTabularVRState) -> RiverSolveResult:
    state.validate(spec)
    return external_sampling_result(spec, state.base)


def _encode_baseline_key(key: BaselineKey) -> str:
    traverser, own_hand, player, node = key
    return f"{traverser}\t{own_hand}\t{player}\t{node}"


def _decode_baseline_key(text: str) -> BaselineKey:
    parts = text.split("\t", 3)
    if len(parts) != 4:
        raise ValueError("invalid tabular baseline key encoding")
    return int(parts[0]), int(parts[1]), int(parts[2]), parts[3]


def tabular_vr_state_to_dict(state: RiverTabularVRState) -> dict[str, Any]:
    return {
        "schema": "DEEPCASH_RIVER_TABULAR_VR_STATE_V1",
        "base": external_sampling_state_to_dict(state.base),
        "baseline_mean": {
            _encode_baseline_key(key): list(values)
            for key, values in sorted(state.baseline_mean.items())
        },
        "baseline_count": {
            _encode_baseline_key(key): list(values)
            for key, values in sorted(state.baseline_count.items())
        },
    }


def tabular_vr_state_from_dict(
    spec: RiverGameSpec,
    payload: Mapping[str, Any],
    *,
    expected_variant: ExternalSamplingVariant | str | None = None,
) -> RiverTabularVRState:
    if payload.get("schema") != "DEEPCASH_RIVER_TABULAR_VR_STATE_V1":
        raise ValueError("unsupported tabular VR checkpoint schema")
    base = external_sampling_state_from_dict(
        spec,
        payload["base"],
        expected_variant=expected_variant,
    )
    state = RiverTabularVRState(
        base=base,
        baseline_mean={
            _decode_baseline_key(key): [float(value) for value in values]
            for key, values in payload["baseline_mean"].items()
        },
        baseline_count={
            _decode_baseline_key(key): [int(value) for value in values]
            for key, values in payload["baseline_count"].items()
        },
    )
    state.validate(spec)
    return state
