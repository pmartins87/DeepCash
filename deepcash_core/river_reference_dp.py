from __future__ import annotations

from typing import Mapping

from .river_lab import RiverSolveResult
from .river_reference_lab import (
    AsymmetricRiverGameSpec,
    P1_AFTER_CHECK,
    ROOT,
    actions,
    deal_value,
    normalize_policy,
    p0_vs_p1_bet_node,
    p1_vs_p0_bet_node,
    showdown_value,
    valid_deals,
)
from .river_reference_training import AsymmetricRiverCFRState

Policy = Mapping[tuple[int, str, int], tuple[float, ...]]


def _index(spec: AsymmetricRiverGameSpec, player: int, node: str, action: str) -> int:
    return actions(spec, player, node).index(action)


def exact_best_response_values_dp(
    spec: AsymmetricRiverGameSpec,
    policy: Policy,
) -> tuple[float, float]:
    """Dynamic exact BR for the one-bet asymmetric river game.

    The older enumerator is intentionally retained as an independent oracle on
    tiny games.  This routine exploits the tree structure instead of enumerating
    `(1+S)*2^S` pure plans per hand, making rich common-reference evaluation far
    cheaper without changing the game being measured.

    Returns `(P0 best-response value, P0 value versus P1 best response)`.
    """
    deals = valid_deals(spec)
    total_chance = sum(w for _, _, w in deals)
    if total_chance <= 0.0:
        raise ValueError("river game has no chance mass")

    by_i: dict[int, list[tuple[int, float]]] = {i: [] for i in range(len(spec.p0_range))}
    by_j: dict[int, list[tuple[int, float]]] = {j: [] for j in range(len(spec.p1_range))}
    for i, j, weight in deals:
        by_i[i].append((j, weight))
        by_j[j].append((i, weight))

    # ------------------------------------------------------------------
    # P0 best response.
    # ------------------------------------------------------------------
    br0_num = 0.0
    half_pot = float(spec.pot) / 2.0

    for i, compatible in by_i.items():
        if not compatible:
            continue

        root_candidates: list[float] = []

        # P0 CHECK. P1's after-check strategy is fixed, but every later P0
        # fold/call decision is optimized on the correct posterior chance mass.
        check_value = 0.0
        p1_check_idx = _index(spec, 1, P1_AFTER_CHECK, "CHECK")
        for j, weight in compatible:
            sigma1 = policy[(1, P1_AFTER_CHECK, j)]
            check_value += weight * sigma1[p1_check_idx] * showdown_value(spec, i, j)

        for bet in spec.p1_bet_sizes:
            p1_bet_idx = _index(spec, 1, P1_AFTER_CHECK, f"BET_{bet}")
            fold_value = 0.0
            call_value = 0.0
            for j, weight in compatible:
                prob = policy[(1, P1_AFTER_CHECK, j)][p1_bet_idx]
                mass = weight * prob
                fold_value += mass * (-half_pot)
                call_value += mass * showdown_value(spec, i, j, bet)
            check_value += max(fold_value, call_value)
        root_candidates.append(check_value)

        # P0 BET b. P1's response strategy is fixed.
        for bet in spec.p0_bet_sizes:
            node = p1_vs_p0_bet_node(bet)
            fold_idx = _index(spec, 1, node, "FOLD")
            call_idx = _index(spec, 1, node, "CALL")
            value = 0.0
            for j, weight in compatible:
                sigma1 = policy[(1, node, j)]
                value += weight * (
                    sigma1[fold_idx] * half_pot
                    + sigma1[call_idx] * showdown_value(spec, i, j, bet)
                )
            root_candidates.append(value)

        br0_num += max(root_candidates)

    # ------------------------------------------------------------------
    # P1 best response.  We accumulate P0 value; P1 minimizes it.
    # ------------------------------------------------------------------
    br1_num = 0.0
    for j, compatible in by_j.items():
        if not compatible:
            continue

        p0_value = 0.0

        # P0 opening bets. Each faced-bet infoset is independent for P1.
        for bet in spec.p0_bet_sizes:
            p0_root_bet_idx = _index(spec, 0, ROOT, f"BET_{bet}")
            fold_value = 0.0
            call_value = 0.0
            for i, weight in compatible:
                prob = policy[(0, ROOT, i)][p0_root_bet_idx]
                mass = weight * prob
                fold_value += mass * half_pot
                call_value += mass * showdown_value(spec, i, j, bet)
            p0_value += min(fold_value, call_value)

        # P0 CHECK reaches one P1 opening decision. For each candidate P1
        # action, P0's downstream response is fixed by the supplied policy.
        p0_check_idx = _index(spec, 0, ROOT, "CHECK")
        after_check_candidates: list[float] = []

        check_back_value = 0.0
        for i, weight in compatible:
            prob = policy[(0, ROOT, i)][p0_check_idx]
            check_back_value += weight * prob * showdown_value(spec, i, j)
        after_check_candidates.append(check_back_value)

        for bet in spec.p1_bet_sizes:
            node = p0_vs_p1_bet_node(bet)
            fold_idx = _index(spec, 0, node, "FOLD")
            call_idx = _index(spec, 0, node, "CALL")
            value = 0.0
            for i, weight in compatible:
                root_prob = policy[(0, ROOT, i)][p0_check_idx]
                sigma0 = policy[(0, node, i)]
                value += weight * root_prob * (
                    sigma0[fold_idx] * (-half_pot)
                    + sigma0[call_idx] * showdown_value(spec, i, j, bet)
                )
            after_check_candidates.append(value)

        p0_value += min(after_check_candidates)
        br1_num += p0_value

    return br0_num / total_chance, br1_num / total_chance


def asymmetric_result_from_state_dp(
    spec: AsymmetricRiverGameSpec,
    state: AsymmetricRiverCFRState,
) -> RiverSolveResult:
    """Evaluate a resumable reference state using dynamic exact BR."""
    state.validate(spec)
    if state.iterations <= 0:
        raise ValueError("cannot evaluate an untrained CFR state")
    infosets = tuple(state.regrets)
    policy = normalize_policy(spec, state.strategy_sum, state.regrets)
    deals = valid_deals(spec)
    total = sum(w for _, _, w in deals)
    policy_ev = sum(w * deal_value(spec, i, j, policy) for i, j, w in deals) / total
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
