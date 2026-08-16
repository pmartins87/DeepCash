from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .river_lab import (
    P1_AFTER_CHECK,
    ROOT,
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
    p0_vs_bet_node,
    p1_vs_bet_node,
)
from .river_training import river_spec_signature

InfoKey = tuple[int, str, int]


class AlternatingVariant(str, Enum):
    ALT_CFR_PLUS_LINEAR = "ALT_CFR_PLUS_LINEAR"
    ALT_CFR_PLUS_QUADRATIC = "ALT_CFR_PLUS_QUADRATIC"
    ALT_DCFR_150_0_2 = "ALT_DCFR_150_0_2"
    ALT_DCFR_150_050_2 = "ALT_DCFR_150_050_2"

    @property
    def is_dcfr(self) -> bool:
        return self in {self.ALT_DCFR_150_0_2, self.ALT_DCFR_150_050_2}

    @property
    def beta(self) -> float | None:
        if self == self.ALT_DCFR_150_0_2:
            return 0.0
        if self == self.ALT_DCFR_150_050_2:
            return 0.5
        return None


@dataclass
class AlternatingRiverState:
    spec_signature: tuple
    variant: AlternatingVariant
    iterations: int
    regrets: dict[InfoKey, list[float]]
    strategy_sum: dict[InfoKey, list[float]]

    def validate(self, spec: RiverGameSpec, *, variant: AlternatingVariant | None = None) -> None:
        if self.spec_signature != river_spec_signature(spec):
            raise ValueError("alternating checkpoint belongs to another river game")
        if variant is not None and self.variant != variant:
            raise ValueError("alternating checkpoint belongs to another variant")
        if self.iterations < 0:
            raise ValueError("iterations cannot be negative")
        expected = set(_all_infosets(spec))
        if set(self.regrets) != expected or set(self.strategy_sum) != expected:
            raise ValueError("alternating checkpoint infosets do not match game")
        for key in expected:
            n = len(_actions(spec, key[0], key[1]))
            if len(self.regrets[key]) != n or len(self.strategy_sum[key]) != n:
                raise ValueError(f"alternating action shape mismatch at {key}")
            for value in (*self.regrets[key], *self.strategy_sum[key]):
                if not math.isfinite(value):
                    raise ValueError("alternating checkpoint contains non-finite values")
            if any(value < 0.0 for value in self.strategy_sum[key]):
                raise ValueError("average-strategy sums cannot be negative")
            if not self.variant.is_dcfr and any(value < 0.0 for value in self.regrets[key]):
                raise ValueError("CFR+ alternating regrets must remain non-negative")


def init_alternating_solver(
    spec: RiverGameSpec,
    variant: AlternatingVariant | str,
) -> AlternatingRiverState:
    variant = AlternatingVariant(variant)
    infosets = _all_infosets(spec)
    state = AlternatingRiverState(
        spec_signature=river_spec_signature(spec),
        variant=variant,
        iterations=0,
        regrets={key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets},
        strategy_sum={key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets},
    )
    state.validate(spec, variant=variant)
    return state


def _full_regret_delta(
    spec: RiverGameSpec,
    strategies: Mapping[InfoKey, tuple[float, ...]],
) -> dict[InfoKey, list[float]]:
    infosets = _all_infosets(spec)
    regret_delta = {key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets}
    strategy_dummy = {key: [0.0] * len(regret_delta[key]) for key in infosets}
    deals = _valid_deals(spec)
    total_chance = sum(weight for _, _, weight in deals)
    for i, j, raw_weight in deals:
        _traverse_cfr(
            spec,
            i=i,
            j=j,
            chance=raw_weight / total_chance,
            strategies=strategies,
            regret_delta=regret_delta,
            strategy_delta=strategy_dummy,
            average_weight=0.0,
        )
    return regret_delta


def dcfr_regret_factor(t: int, exponent: float) -> float:
    if t <= 0:
        raise ValueError("DCFR iteration must be positive")
    powered = float(t) ** exponent
    return powered / (powered + 1.0)


def dcfr_average_factor(t: int, gamma: float = 2.0) -> float:
    """Multiplicative form equivalent to relative t**gamma output weighting."""
    if t <= 0:
        raise ValueError("DCFR iteration must be positive")
    return (float(t) / float(t + 1)) ** gamma


def _apply_player_update(
    state: AlternatingRiverState,
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
        for a in range(len(values)):
            updated = values[a] + regret_delta[key][a]
            if state.variant.is_dcfr:
                exponent = 1.5 if updated >= 0.0 else float(state.variant.beta)
                updated *= dcfr_regret_factor(iteration, exponent)
            else:
                updated = max(0.0, updated)
            values[a] = updated


def _average_iteration_weight(variant: AlternatingVariant, iteration: int) -> float:
    if iteration <= 0:
        raise ValueError("average iteration must be positive")
    if variant == AlternatingVariant.ALT_CFR_PLUS_LINEAR:
        return float(iteration)
    # Quadratic CFR+ and both DCFR controls use gamma=2 output weighting.
    return float(iteration * iteration)


def _accumulate_player_average(
    spec: RiverGameSpec,
    state: AlternatingRiverState,
    strategies: Mapping[InfoKey, tuple[float, ...]],
    *,
    player: int,
    iteration: int,
) -> None:
    """Accumulate only the alternating player's current-profile average.

    This mirrors the player-local timing of alternating CFR: P0 contributes its
    policy before P0's regret refresh; P1 contributes after P0's refresh but
    before P1's own refresh. Fixed private/chance mass per infoset cancels under
    normalization, so only the player's own realization reach is required.
    """
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    weight = _average_iteration_weight(state.variant, iteration)

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
                    state.strategy_sum[key][a] += (
                        weight * check_reach * probability
                    )
        return

    for j in range(len(spec.p1_range)):
        key = (1, P1_AFTER_CHECK, j)
        for a, probability in enumerate(strategies[key]):
            state.strategy_sum[key][a] += weight * probability
        for bet in spec.bet_sizes:
            key = (1, p1_vs_bet_node(bet), j)
            for a, probability in enumerate(strategies[key]):
                state.strategy_sum[key][a] += weight * probability


def advance_alternating_solver(
    spec: RiverGameSpec,
    state: AlternatingRiverState,
    *,
    additional_iterations: int,
) -> AlternatingRiverState:
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec)
    if additional_iterations == 0:
        return state

    infosets = _all_infosets(spec)
    for offset in range(1, additional_iterations + 1):
        iteration = state.iterations + offset

        # P0 average/regret use the same pre-P0-update profile.
        strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
        _accumulate_player_average(
            spec, state, strategies, player=0, iteration=iteration
        )
        delta0 = _full_regret_delta(spec, strategies)
        _apply_player_update(state, delta0, player=0, iteration=iteration)

        # P1 sees the refreshed P0 strategy; its average is recorded before P1's
        # own regret refresh, exactly matching alternating traversal semantics.
        strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
        _accumulate_player_average(
            spec, state, strategies, player=1, iteration=iteration
        )
        delta1 = _full_regret_delta(spec, strategies)
        _apply_player_update(state, delta1, player=1, iteration=iteration)

    state.iterations += additional_iterations
    state.validate(spec)
    return state


def alternating_solver_result(
    spec: RiverGameSpec,
    state: AlternatingRiverState,
) -> RiverSolveResult:
    state.validate(spec)
    if state.iterations <= 0:
        raise ValueError("cannot evaluate an untrained alternating solver")
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


def alternating_state_to_dict(state: AlternatingRiverState) -> dict[str, Any]:
    return {
        "schema": "DEEPCASH_RIVER_ALTERNATING_DCFR_STATE_V1",
        "spec_signature": state.spec_signature,
        "variant": state.variant.value,
        "iterations": state.iterations,
        "regrets": {_encode_key(k): list(v) for k, v in sorted(state.regrets.items())},
        "strategy_sum": {
            _encode_key(k): list(v) for k, v in sorted(state.strategy_sum.items())
        },
    }


def alternating_state_from_dict(
    spec: RiverGameSpec,
    payload: Mapping[str, Any],
    *,
    expected_variant: AlternatingVariant | str | None = None,
) -> AlternatingRiverState:
    if payload.get("schema") != "DEEPCASH_RIVER_ALTERNATING_DCFR_STATE_V1":
        raise ValueError("unsupported alternating solver checkpoint schema")
    variant = AlternatingVariant(payload["variant"])
    if expected_variant is not None and variant != AlternatingVariant(expected_variant):
        raise ValueError("alternating checkpoint variant mismatch")
    state = AlternatingRiverState(
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
