from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

from .river_alternating_dcfr import AlternatingVariant, dcfr_regret_factor
from .river_lab import P1_AFTER_CHECK, ROOT, RiverGameSpec, RiverSolveResult, _actions, _regret_strategy, _valid_deals, evaluate_policy, p0_vs_bet_node, p1_vs_bet_node
from .river_representation_br import bucket_constrained_best_response_values
from .river_representation_lab import RiverBucketMaps, _abstract_infosets, _expand_policy, _normalize_abstract_policy, _traverse_abstract_cfr
from .river_representation_training import representation_spec_signature

InfoKey = tuple[int, str, int]


@dataclass
class AlternatingRepresentationState:
    spec_signature: tuple
    variant: AlternatingVariant
    iterations: int
    regrets: dict[InfoKey, list[float]]
    strategy_sum: dict[InfoKey, list[float]]

    def validate(self, spec: RiverGameSpec, maps: RiverBucketMaps, *, variant: AlternatingVariant | str | None = None) -> None:
        maps.validate(spec)
        if self.spec_signature != representation_spec_signature(spec, maps):
            raise ValueError("abstract alternating checkpoint belongs to another spec/map")
        if variant is not None and self.variant != AlternatingVariant(variant):
            raise ValueError("abstract alternating checkpoint variant mismatch")
        if self.iterations < 0:
            raise ValueError("iterations cannot be negative")
        expected = set(_abstract_infosets(spec, maps))
        if set(self.regrets) != expected or set(self.strategy_sum) != expected:
            raise ValueError("abstract alternating checkpoint infosets do not match spec/map")
        for key in expected:
            n = len(_actions(spec, key[0], key[1]))
            if len(self.regrets[key]) != n or len(self.strategy_sum[key]) != n:
                raise ValueError(f"abstract alternating action shape mismatch at {key}")
            for value in (*self.regrets[key], *self.strategy_sum[key]):
                if not math.isfinite(value):
                    raise ValueError("abstract alternating checkpoint contains non-finite values")
            if any(value < 0.0 for value in self.strategy_sum[key]):
                raise ValueError("average-strategy sums cannot be negative")
            if not self.variant.is_dcfr and any(value < 0.0 for value in self.regrets[key]):
                raise ValueError("CFR+ regrets must remain non-negative")


def init_alternating_representation_solver(
    spec: RiverGameSpec,
    maps: RiverBucketMaps,
    variant: AlternatingVariant | str,
) -> AlternatingRepresentationState:
    maps.validate(spec)
    variant = AlternatingVariant(variant)
    infosets = _abstract_infosets(spec, maps)
    state = AlternatingRepresentationState(
        spec_signature=representation_spec_signature(spec, maps),
        variant=variant,
        iterations=0,
        regrets={key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets},
        strategy_sum={key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets},
    )
    state.validate(spec, maps, variant=variant)
    return state


def _full_regret_delta(
    spec: RiverGameSpec,
    maps: RiverBucketMaps,
    strategies: Mapping[InfoKey, tuple[float, ...]],
) -> dict[InfoKey, list[float]]:
    infosets = _abstract_infosets(spec, maps)
    regret_delta = {key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets}
    strategy_dummy = {key: [0.0] * len(regret_delta[key]) for key in infosets}
    deals = _valid_deals(spec)
    total_chance = sum(weight for _, _, weight in deals)
    for i, j, raw_weight in deals:
        _traverse_abstract_cfr(
            spec,
            maps,
            i=i,
            j=j,
            chance=raw_weight / total_chance,
            strategies=strategies,
            regret_delta=regret_delta,
            strategy_delta=strategy_dummy,
            average_weight=0.0,
        )
    return regret_delta


def _apply_player_update(
    state: AlternatingRepresentationState,
    regret_delta: Mapping[InfoKey, list[float]],
    *,
    player: int,
    iteration: int,
) -> None:
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    for key, values in state.regrets.items():
        if key[0] != player:
            continue
        for action_index in range(len(values)):
            updated = values[action_index] + regret_delta[key][action_index]
            if state.variant.is_dcfr:
                exponent = 1.5 if updated >= 0.0 else float(state.variant.beta)
                updated *= dcfr_regret_factor(iteration, exponent)
            else:
                updated = max(0.0, updated)
            values[action_index] = updated


def _average_iteration_weight(variant: AlternatingVariant, iteration: int) -> float:
    if iteration <= 0:
        raise ValueError("average iteration must be positive")
    if variant == AlternatingVariant.ALT_CFR_PLUS_LINEAR:
        return float(iteration)
    return float(iteration * iteration)


def _accumulate_player_average(
    spec: RiverGameSpec,
    maps: RiverBucketMaps,
    state: AlternatingRepresentationState,
    strategies: Mapping[InfoKey, tuple[float, ...]],
    *,
    player: int,
    iteration: int,
) -> None:
    """Accumulate the alternating player's abstract policy at player-local timing.

    Fixed private/chance mass for a materialized abstract infoset cancels when its
    average strategy is normalized. The only action-dependent own realization
    reach below the root is the P0 check branch, exactly as in the exact solver.
    """
    weight = _average_iteration_weight(state.variant, iteration)
    if player == 0:
        root_actions = _actions(spec, 0, ROOT)
        check_index = root_actions.index("CHECK")
        for bucket in sorted(set(maps.p0)):
            root = (0, ROOT, bucket)
            root_sigma = strategies[root]
            for action_index, probability in enumerate(root_sigma):
                state.strategy_sum[root][action_index] += weight * probability
            check_reach = root_sigma[check_index]
            for bet in spec.bet_sizes:
                key = (0, p0_vs_bet_node(bet), bucket)
                for action_index, probability in enumerate(strategies[key]):
                    state.strategy_sum[key][action_index] += weight * check_reach * probability
        return
    if player == 1:
        for bucket in sorted(set(maps.p1)):
            key = (1, P1_AFTER_CHECK, bucket)
            for action_index, probability in enumerate(strategies[key]):
                state.strategy_sum[key][action_index] += weight * probability
            for bet in spec.bet_sizes:
                key = (1, p1_vs_bet_node(bet), bucket)
                for action_index, probability in enumerate(strategies[key]):
                    state.strategy_sum[key][action_index] += weight * probability
        return
    raise ValueError("player must be 0 or 1")


def advance_alternating_representation_solver(
    spec: RiverGameSpec,
    maps: RiverBucketMaps,
    state: AlternatingRepresentationState,
    *,
    additional_iterations: int,
) -> AlternatingRepresentationState:
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec, maps)
    if additional_iterations == 0:
        return state
    infosets = _abstract_infosets(spec, maps)
    for offset in range(1, additional_iterations + 1):
        iteration = state.iterations + offset
        strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
        _accumulate_player_average(spec, maps, state, strategies, player=0, iteration=iteration)
        delta0 = _full_regret_delta(spec, maps, strategies)
        _apply_player_update(state, delta0, player=0, iteration=iteration)

        strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
        _accumulate_player_average(spec, maps, state, strategies, player=1, iteration=iteration)
        delta1 = _full_regret_delta(spec, maps, strategies)
        _apply_player_update(state, delta1, player=1, iteration=iteration)

    state.iterations += additional_iterations
    state.validate(spec, maps)
    return state


def alternating_representation_result(
    spec: RiverGameSpec,
    maps: RiverBucketMaps,
    state: AlternatingRepresentationState,
) -> RiverSolveResult:
    state.validate(spec, maps)
    if state.iterations <= 0:
        raise ValueError("cannot evaluate an untrained abstract alternating solver")
    infosets = _abstract_infosets(spec, maps)
    abstract_policy = _normalize_abstract_policy(spec, infosets, state.strategy_sum, state.regrets)
    policy = _expand_policy(spec, maps, abstract_policy)
    policy_ev = evaluate_policy(spec, policy)
    br0, br1 = bucket_constrained_best_response_values(spec, maps, policy)
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
        raise ValueError(f"invalid abstract alternating infoset key: {text!r}")
    return int(parts[0]), parts[1], int(parts[2])


def _deep_tuple(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_deep_tuple(v) for v in value)
    return value


def alternating_representation_state_to_dict(state: AlternatingRepresentationState) -> dict[str, Any]:
    return {
        "schema": "DEEPCASH_RIVER_REPRESENTATION_ALTERNATING_DCFR_STATE_V1",
        "spec_signature": state.spec_signature,
        "variant": state.variant.value,
        "iterations": state.iterations,
        "regrets": {_encode_key(key): list(values) for key, values in sorted(state.regrets.items())},
        "strategy_sum": {_encode_key(key): list(values) for key, values in sorted(state.strategy_sum.items())},
    }


def alternating_representation_state_from_dict(
    spec: RiverGameSpec,
    maps: RiverBucketMaps,
    payload: Mapping[str, Any],
    *,
    expected_variant: AlternatingVariant | str | None = None,
) -> AlternatingRepresentationState:
    if payload.get("schema") != "DEEPCASH_RIVER_REPRESENTATION_ALTERNATING_DCFR_STATE_V1":
        raise ValueError("unsupported abstract alternating checkpoint schema")
    variant = AlternatingVariant(payload["variant"])
    if expected_variant is not None and variant != AlternatingVariant(expected_variant):
        raise ValueError("abstract alternating checkpoint variant mismatch")
    state = AlternatingRepresentationState(
        spec_signature=_deep_tuple(payload["spec_signature"]),
        variant=variant,
        iterations=int(payload["iterations"]),
        regrets={_decode_key(key): [float(x) for x in values] for key, values in payload["regrets"].items()},
        strategy_sum={_decode_key(key): [float(x) for x in values] for key, values in payload["strategy_sum"].items()},
    )
    state.validate(spec, maps, variant=variant)
    return state
