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


class PaperDCFRVariant(str, Enum):
    PAPER_DCFR_150_0_2 = "PAPER_DCFR_150_0_2"
    HS_DCFR_30 = "HS_DCFR_30"
    HS_DCFR_15 = "HS_DCFR_15"


@dataclass(frozen=True)
class DCFRParameters:
    alpha: float
    beta: float
    gamma: float

    def validate(self) -> None:
        if not all(math.isfinite(v) for v in (self.alpha, self.beta, self.gamma)):
            raise ValueError("DCFR parameters must be finite")


@dataclass
class PaperDCFRState:
    spec_signature: tuple
    variant: PaperDCFRVariant
    horizon: int
    iterations: int
    regrets: dict[InfoKey, list[float]]
    strategy_sum: dict[InfoKey, list[float]]

    def validate(
        self,
        spec: RiverGameSpec,
        *,
        variant: PaperDCFRVariant | None = None,
        horizon: int | None = None,
    ) -> None:
        if self.spec_signature != river_spec_signature(spec):
            raise ValueError("paper-DCFR checkpoint belongs to another river game")
        if variant is not None and self.variant != variant:
            raise ValueError("paper-DCFR checkpoint belongs to another variant")
        if horizon is not None and self.horizon != int(horizon):
            raise ValueError("paper-DCFR checkpoint belongs to another horizon")
        if self.horizon <= 0:
            raise ValueError("paper-DCFR horizon must be positive")
        if not 0 <= self.iterations <= self.horizon:
            raise ValueError("paper-DCFR iterations must lie inside horizon")
        expected = set(_all_infosets(spec))
        if set(self.regrets) != expected or set(self.strategy_sum) != expected:
            raise ValueError("paper-DCFR checkpoint infosets do not match game")
        for key in expected:
            n = len(_actions(spec, key[0], key[1]))
            if len(self.regrets[key]) != n or len(self.strategy_sum[key]) != n:
                raise ValueError(f"paper-DCFR action shape mismatch at {key}")
            for value in (*self.regrets[key], *self.strategy_sum[key]):
                if not math.isfinite(value):
                    raise ValueError("paper-DCFR checkpoint contains non-finite values")
            if any(value < 0.0 for value in self.strategy_sum[key]):
                raise ValueError("paper-DCFR average-strategy sums cannot be negative")


def parameters_for(
    variant: PaperDCFRVariant | str,
    *,
    iteration: int,
    horizon: int,
) -> DCFRParameters:
    variant = PaperDCFRVariant(variant)
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if not 1 <= iteration <= horizon:
        raise ValueError("iteration must be in [1, horizon]")
    if variant == PaperDCFRVariant.PAPER_DCFR_150_0_2:
        out = DCFRParameters(1.5, 0.0, 2.0)
    else:
        ratio = float(iteration) / float(horizon)
        alpha = 1.0 + 3.0 * ratio
        beta = -1.0 - 2.0 * ratio
        gamma0 = 30.0 if variant == PaperDCFRVariant.HS_DCFR_30 else 15.0
        out = DCFRParameters(alpha, beta, gamma0 - 5.0 * ratio)
    out.validate()
    return out


def regret_discount_factor(iteration: int, exponent: float) -> float:
    if iteration <= 0 or not math.isfinite(exponent):
        raise ValueError("invalid regret discount coordinate")
    powered = float(iteration) ** exponent
    if not math.isfinite(powered) or powered < 0.0:
        raise ValueError("invalid powered regret discount")
    return powered / (powered + 1.0)


def average_discount_factor(iteration: int, gamma: float) -> float:
    if iteration <= 0 or not math.isfinite(gamma):
        raise ValueError("invalid average discount coordinate")
    return (float(iteration) / float(iteration + 1)) ** gamma


def init_paper_dcfr(
    spec: RiverGameSpec,
    variant: PaperDCFRVariant | str,
    *,
    horizon: int,
) -> PaperDCFRState:
    variant = PaperDCFRVariant(variant)
    infosets = _all_infosets(spec)
    state = PaperDCFRState(
        spec_signature=river_spec_signature(spec),
        variant=variant,
        horizon=int(horizon),
        iterations=0,
        regrets={key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets},
        strategy_sum={key: [0.0] * len(_actions(spec, key[0], key[1])) for key in infosets},
    )
    state.validate(spec, variant=variant, horizon=horizon)
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


def _discount_then_add_player_average(
    spec: RiverGameSpec,
    state: PaperDCFRState,
    strategies: Mapping[InfoKey, tuple[float, ...]],
    *,
    player: int,
    iteration: int,
    gamma: float,
) -> None:
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    factor = average_discount_factor(iteration, gamma)
    for key, values in state.strategy_sum.items():
        if key[0] == player:
            for a in range(len(values)):
                values[a] *= factor

    if player == 0:
        root_actions = _actions(spec, 0, ROOT)
        check_index = root_actions.index("CHECK")
        for i in range(len(spec.p0_range)):
            root = (0, ROOT, i)
            root_sigma = strategies[root]
            for a, probability in enumerate(root_sigma):
                state.strategy_sum[root][a] += probability
            check_reach = root_sigma[check_index]
            for bet in spec.bet_sizes:
                key = (0, p0_vs_bet_node(bet), i)
                for a, probability in enumerate(strategies[key]):
                    state.strategy_sum[key][a] += check_reach * probability
        return

    for j in range(len(spec.p1_range)):
        key = (1, P1_AFTER_CHECK, j)
        for a, probability in enumerate(strategies[key]):
            state.strategy_sum[key][a] += probability
        for bet in spec.bet_sizes:
            key = (1, p1_vs_bet_node(bet), j)
            for a, probability in enumerate(strategies[key]):
                state.strategy_sum[key][a] += probability


def _discount_old_then_add_regrets(
    state: PaperDCFRState,
    regret_delta: Mapping[InfoKey, list[float]],
    *,
    player: int,
    iteration: int,
    alpha: float,
    beta: float,
) -> None:
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    positive_factor = regret_discount_factor(iteration, alpha)
    negative_factor = regret_discount_factor(iteration, beta)
    for key, values in state.regrets.items():
        if key[0] != player:
            continue
        for a, old in enumerate(tuple(values)):
            factor = positive_factor if old > 0.0 else negative_factor
            values[a] = old * factor + regret_delta[key][a]


def advance_paper_dcfr(
    spec: RiverGameSpec,
    state: PaperDCFRState,
    *,
    additional_iterations: int,
) -> PaperDCFRState:
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec)
    if state.iterations + additional_iterations > state.horizon:
        raise ValueError("training would exceed frozen paper-DCFR horizon")
    if additional_iterations == 0:
        return state

    infosets = _all_infosets(spec)
    for offset in range(1, additional_iterations + 1):
        iteration = state.iterations + offset
        params = parameters_for(state.variant, iteration=iteration, horizon=state.horizon)

        for player in (0, 1):
            strategies = {key: _regret_strategy(state.regrets[key]) for key in infosets}
            _discount_then_add_player_average(
                spec,
                state,
                strategies,
                player=player,
                iteration=iteration,
                gamma=params.gamma,
            )
            regret_delta = _full_regret_delta(spec, strategies)
            _discount_old_then_add_regrets(
                state,
                regret_delta,
                player=player,
                iteration=iteration,
                alpha=params.alpha,
                beta=params.beta,
            )

    state.iterations += additional_iterations
    state.validate(spec)
    return state


def paper_dcfr_result(spec: RiverGameSpec, state: PaperDCFRState) -> RiverSolveResult:
    state.validate(spec)
    if state.iterations <= 0:
        raise ValueError("cannot evaluate an untrained paper-DCFR state")
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


def paper_dcfr_state_to_dict(state: PaperDCFRState) -> dict[str, Any]:
    return {
        "schema": "DEEPCASH_RIVER_PAPER_HS_DCFR_STATE_V1",
        "spec_signature": state.spec_signature,
        "variant": state.variant.value,
        "horizon": state.horizon,
        "iterations": state.iterations,
        "regrets": {_encode_key(k): list(v) for k, v in sorted(state.regrets.items())},
        "strategy_sum": {
            _encode_key(k): list(v) for k, v in sorted(state.strategy_sum.items())
        },
    }


def paper_dcfr_state_from_dict(
    spec: RiverGameSpec,
    payload: Mapping[str, Any],
    *,
    expected_variant: PaperDCFRVariant | str | None = None,
    expected_horizon: int | None = None,
) -> PaperDCFRState:
    if payload.get("schema") != "DEEPCASH_RIVER_PAPER_HS_DCFR_STATE_V1":
        raise ValueError("unsupported paper-DCFR checkpoint schema")
    variant = PaperDCFRVariant(payload["variant"])
    state = PaperDCFRState(
        spec_signature=_deep_tuple(payload["spec_signature"]),
        variant=variant,
        horizon=int(payload["horizon"]),
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
    state.validate(
        spec,
        variant=PaperDCFRVariant(expected_variant) if expected_variant is not None else None,
        horizon=expected_horizon,
    )
    return state
