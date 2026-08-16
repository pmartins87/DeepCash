from __future__ import annotations

from typing import Mapping

from .river_raise_reference_lab import (
    AsymmetricRiverRaiseGameSpec,
    P1_AFTER_CHECK,
    ROOT,
    actions,
    p0_vs_p1_bet_node,
    p0_vs_p1_raise_node,
    p1_vs_p0_bet_node,
    p1_vs_p0_raise_node,
    showdown_value,
    valid_deals,
)

Policy = Mapping[tuple[int, str, int], tuple[float, ...]]


def _idx(spec: AsymmetricRiverRaiseGameSpec, player: int, node: str, action: str) -> int:
    return actions(spec, player, node).index(action)


def exact_best_response_values_dp(
    spec: AsymmetricRiverRaiseGameSpec,
    policy: Policy,
) -> tuple[float, float]:
    """Dynamic exact BR for the asymmetric one-raise river control.

    The implementation optimizes each best-responder infoset on its correct
    counterfactual chance/opponent-reach mass, working backward through final
    raise responses.  It is gated against the independent pure-plan enumerator
    on tractable fixtures before being used for richer reference games.
    """
    deals = valid_deals(spec)
    total_chance = sum(w for _, _, w in deals)
    if total_chance <= 0.0:
        raise ValueError("river game has no chance mass")
    half = float(spec.pot) / 2.0

    by_i: dict[int, list[tuple[int, float]]] = {i: [] for i in range(len(spec.p0_range))}
    by_j: dict[int, list[tuple[int, float]]] = {j: [] for j in range(len(spec.p1_range))}
    for i, j, weight in deals:
        by_i[i].append((j, weight))
        by_j[j].append((i, weight))

    # ------------------------------------------------------------------
    # P0 best response against fixed P1.
    # ------------------------------------------------------------------
    br0_num = 0.0
    for i, compatible in by_i.items():
        if not compatible:
            continue
        root_values: list[float] = []

        # P0 CHECK, then fixed P1 check/bet. Against each P1 bet, P0 chooses
        # fold/call/one raise. P1's response to a P0 raise is fixed.
        p1_check_idx = _idx(spec, 1, P1_AFTER_CHECK, "CHECK")
        check_root_value = sum(
            weight
            * policy[(1, P1_AFTER_CHECK, j)][p1_check_idx]
            * showdown_value(spec, i, j)
            for j, weight in compatible
        )

        for p1_bet in spec.p1_bet_sizes:
            p1_bet_idx = _idx(spec, 1, P1_AFTER_CHECK, f"BET_{p1_bet}")
            branch_action_values: list[float] = []

            fold_value = 0.0
            call_value = 0.0
            for j, weight in compatible:
                branch_mass = weight * policy[(1, P1_AFTER_CHECK, j)][p1_bet_idx]
                fold_value += branch_mass * (-half)
                call_value += branch_mass * showdown_value(spec, i, j, p1_bet)
            branch_action_values.extend((fold_value, call_value))

            for raise_to in spec.p0_targets(p1_bet):
                final_node = p1_vs_p0_raise_node(p1_bet, raise_to)
                f_idx = _idx(spec, 1, final_node, "FOLD")
                c_idx = _idx(spec, 1, final_node, "CALL")
                value = 0.0
                for j, weight in compatible:
                    branch_mass = weight * policy[(1, P1_AFTER_CHECK, j)][p1_bet_idx]
                    sigma1 = policy[(1, final_node, j)]
                    value += branch_mass * (
                        sigma1[f_idx] * (half + float(p1_bet))
                        + sigma1[c_idx] * showdown_value(spec, i, j, raise_to)
                    )
                branch_action_values.append(value)

            check_root_value += max(branch_action_values)
        root_values.append(check_root_value)

        # P0 BET. P1's immediate response is fixed. If P1 raises, P0's final
        # fold/call response is optimized at that separate infoset.
        for p0_bet in spec.p0_bet_sizes:
            node = p1_vs_p0_bet_node(p0_bet)
            f_idx = _idx(spec, 1, node, "FOLD")
            c_idx = _idx(spec, 1, node, "CALL")
            value = 0.0
            for j, weight in compatible:
                sigma1 = policy[(1, node, j)]
                value += weight * (
                    sigma1[f_idx] * half
                    + sigma1[c_idx] * showdown_value(spec, i, j, p0_bet)
                )

            for raise_to in spec.p1_targets(p0_bet):
                r_idx = _idx(spec, 1, node, f"RAISE_TO_{raise_to}")
                fold_value = 0.0
                call_value = 0.0
                for j, weight in compatible:
                    branch_mass = weight * policy[(1, node, j)][r_idx]
                    fold_value += branch_mass * (-(half + float(p0_bet)))
                    call_value += branch_mass * showdown_value(spec, i, j, raise_to)
                value += max(fold_value, call_value)
            root_values.append(value)

        br0_num += max(root_values)

    # ------------------------------------------------------------------
    # P1 best response. Accumulate P0 value; P1 minimizes.
    # ------------------------------------------------------------------
    br1_num = 0.0
    for j, compatible in by_j.items():
        if not compatible:
            continue
        p0_value = 0.0

        # P0 opening bets. At each faced bet P1 chooses fold/call/raise. P0's
        # final response to each candidate P1 raise is fixed.
        for p0_bet in spec.p0_bet_sizes:
            p0_root_bet_idx = _idx(spec, 0, ROOT, f"BET_{p0_bet}")
            action_values: list[float] = []

            fold_value = 0.0
            call_value = 0.0
            for i, weight in compatible:
                mass = weight * policy[(0, ROOT, i)][p0_root_bet_idx]
                fold_value += mass * half
                call_value += mass * showdown_value(spec, i, j, p0_bet)
            action_values.extend((fold_value, call_value))

            for raise_to in spec.p1_targets(p0_bet):
                final_node = p0_vs_p1_raise_node(p0_bet, raise_to)
                f_idx = _idx(spec, 0, final_node, "FOLD")
                c_idx = _idx(spec, 0, final_node, "CALL")
                value = 0.0
                for i, weight in compatible:
                    mass = weight * policy[(0, ROOT, i)][p0_root_bet_idx]
                    sigma0 = policy[(0, final_node, i)]
                    value += mass * (
                        sigma0[f_idx] * (-(half + float(p0_bet)))
                        + sigma0[c_idx] * showdown_value(spec, i, j, raise_to)
                    )
                action_values.append(value)

            p0_value += min(action_values)

        # P0 CHECK. P1 chooses check or a bet. If P0 raises that bet under its
        # fixed strategy, P1 optimizes its own final fold/call response.
        p0_check_idx = _idx(spec, 0, ROOT, "CHECK")
        after_check_values: list[float] = []

        check_value = sum(
            weight
            * policy[(0, ROOT, i)][p0_check_idx]
            * showdown_value(spec, i, j)
            for i, weight in compatible
        )
        after_check_values.append(check_value)

        for p1_bet in spec.p1_bet_sizes:
            node = p0_vs_p1_bet_node(p1_bet)
            f_idx = _idx(spec, 0, node, "FOLD")
            c_idx = _idx(spec, 0, node, "CALL")
            bet_value = 0.0
            for i, weight in compatible:
                root_mass = weight * policy[(0, ROOT, i)][p0_check_idx]
                sigma0 = policy[(0, node, i)]
                bet_value += root_mass * (
                    sigma0[f_idx] * (-half)
                    + sigma0[c_idx] * showdown_value(spec, i, j, p1_bet)
                )

            for raise_to in spec.p0_targets(p1_bet):
                r_idx = _idx(spec, 0, node, f"RAISE_TO_{raise_to}")
                fold_value = 0.0
                call_value = 0.0
                for i, weight in compatible:
                    root_mass = weight * policy[(0, ROOT, i)][p0_check_idx]
                    raise_mass = root_mass * policy[(0, node, i)][r_idx]
                    fold_value += raise_mass * (half + float(p1_bet))
                    call_value += raise_mass * showdown_value(spec, i, j, raise_to)
                bet_value += min(fold_value, call_value)

            after_check_values.append(bet_value)

        p0_value += min(after_check_values)
        br1_num += p0_value

    return br0_num / total_chance, br1_num / total_chance
