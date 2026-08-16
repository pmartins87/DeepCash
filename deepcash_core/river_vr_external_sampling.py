from __future__ import annotations

from enum import Enum
from typing import Mapping

from .river_external_sampling import (
    InfoKey,
    RiverExternalSamplingState,
    WeightedDealSampler,
    _accumulate_exact_average,
    _sample_deal,
    _weighted_choice_index,
)
from .river_lab import (
    P1_AFTER_CHECK,
    ROOT,
    RiverGameSpec,
    _actions,
    _all_infosets,
    _bet_amount,
    _regret_strategy,
    _terminal_showdown,
    p0_vs_bet_node,
    p1_vs_bet_node,
)
from .river_vr_infoset_baseline_v2 import exact_infoset_action_baselines_v2
from .vr_mccfr_baseline import baseline_enhanced_node_value


class VRBaselineMode(str, Enum):
    ZERO = "ZERO"
    INFOSET_EXACT = "INFOSET_EXACT"
    PERFECT_HISTORY = "PERFECT_HISTORY"


def _vr_external_traverse(
    spec: RiverGameSpec,
    *,
    i: int,
    j: int,
    traverser: int,
    rng,
    strategies: Mapping[InfoKey, tuple[float, ...]],
    regret_delta: dict[InfoKey, list[float]],
    counter: list[int],
    baseline_mode: VRBaselineMode,
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
                return _vr_external_traverse(
                    spec,
                    i=i,
                    j=j,
                    traverser=traverser,
                    rng=rng,
                    strategies=strategies,
                    regret_delta=regret_delta,
                    counter=counter,
                    baseline_mode=baseline_mode,
                    node=P1_AFTER_CHECK,
                    player=1,
                )
            return _vr_external_traverse(
                spec,
                i=i,
                j=j,
                traverser=traverser,
                rng=rng,
                strategies=strategies,
                regret_delta=regret_delta,
                counter=counter,
                baseline_mode=baseline_mode,
                node=p1_vs_bet_node(_bet_amount(action)),
                player=1,
            )

        if player == 1 and node == P1_AFTER_CHECK:
            if action == "CHECK":
                counter[0] += 1
                return _terminal_showdown(spec, i, j)
            return _vr_external_traverse(
                spec,
                i=i,
                j=j,
                traverser=traverser,
                rng=rng,
                strategies=strategies,
                regret_delta=regret_delta,
                counter=counter,
                baseline_mode=baseline_mode,
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
    if baseline_mode == VRBaselineMode.ZERO:
        # ZERO is the identity control, not merely an algebraically equivalent
        # formulation. Returning the sampled child directly preserves the exact
        # IEEE-754/RNG path of ordinary external sampling.
        return descend(actions[sampled])

    if baseline_mode == VRBaselineMode.INFOSET_EXACT:
        # The sampled child follows the realized hidden history as ordinary
        # external sampling does.  The control variate, however, may use only
        # the traverser's private combo plus public history/current policy.  The
        # baseline API deliberately has no realized-opponent-hand parameter.
        sampled_child = descend(actions[sampled])
        own_hand_index = i if traverser == 0 else j
        baselines = exact_infoset_action_baselines_v2(
            spec,
            traverser=traverser,
            own_hand_index=own_hand_index,
            player=player,
            node=node,
            policy=strategies,
        )
        return baseline_enhanced_node_value(
            target_policy=sigma,
            sampling_policy=sigma,
            baselines=baselines,
            sampled_action=sampled,
            sampled_child_value=sampled_child,
        )

    if baseline_mode == VRBaselineMode.PERFECT_HISTORY:
        # Deliberately privileged oracle: full hidden history (i,j) is known here,
        # and every action continuation is enumerated. It is a variance lower
        # bound / implementation oracle, never a legal production baseline.
        exact_children = tuple(descend(action) for action in actions)
        return baseline_enhanced_node_value(
            target_policy=sigma,
            sampling_policy=sigma,
            baselines=exact_children,
            sampled_action=sampled,
            sampled_child_value=exact_children[sampled],
        )

    raise AssertionError(baseline_mode)  # pragma: no cover


def advance_vr_external_sampling(
    spec: RiverGameSpec,
    state: RiverExternalSamplingState,
    *,
    additional_iterations: int,
    baseline_mode: VRBaselineMode | str,
) -> RiverExternalSamplingState:
    """Advance an existing ES CFR state using the chosen VR baseline oracle.

    ZERO is the exact ordinary-external-sampling identity control. INFOSET_EXACT
    is the expensive no-private-leak conditional oracle. PERFECT_HISTORY is a
    privileged hidden-state lower bound and is never production eligible.
    """
    import random

    mode = VRBaselineMode(baseline_mode)
    if additional_iterations < 0:
        raise ValueError("additional_iterations cannot be negative")
    state.validate(spec)
    if additional_iterations == 0:
        return state

    infosets = _all_infosets(spec)
    deal_sampler = WeightedDealSampler.from_spec(spec)
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

        for traverser in (0, 1):
            i, j = _sample_deal(spec, rng, deal_sampler)
            _vr_external_traverse(
                spec,
                i=i,
                j=j,
                traverser=traverser,
                rng=rng,
                strategies=strategies,
                regret_delta=regret_delta,
                counter=counter,
                baseline_mode=mode,
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
