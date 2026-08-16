import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_lab import (
    ROOT,
    RangeCombo,
    RiverGameSpec,
    _actions,
    _all_infosets,
    _terminal_showdown,
    _valid_deals,
    p0_vs_bet_node,
    p1_vs_bet_node,
)
from deepcash_core.river_vr_infoset_baseline import exact_infoset_action_baselines


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str, weight: float = 1.0) -> RangeCombo:
    return RangeCombo((c(a), c(b)), weight)


def fixture_spec(*, reverse_holes: bool = False) -> RiverGameSpec:
    p0 = [("Qs", "Qh", 0.4), ("Jc", "Js", 1.3), ("8c", "8d", 0.8)]
    p1 = [("Qd", "Jh", 1.1), ("Jd", "Th", 0.5), ("6c", "6d", 1.7)]
    if reverse_holes:
        p0 = [(b, a, w) for a, b, w in p0]
        p1 = [(b, a, w) for a, b, w in p1]
    return RiverGameSpec(
        board=(c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h")),
        p0_range=tuple(combo(a, b, w) for a, b, w in p0),
        p1_range=tuple(combo(a, b, w) for a, b, w in p1),
        pot=100,
        bet_sizes=(25, 50, 100),
    )


def uniform_policy(spec):
    return {
        key: tuple(
            1.0 / len(_actions(spec, key[0], key[1]))
            for _ in _actions(spec, key[0], key[1])
        )
        for key in _all_infosets(spec)
    }


def test_p0_traverser_baseline_equals_independent_hidden_p1_average():
    spec = fixture_spec()
    policy = uniform_policy(spec)
    node = p1_vs_bet_node(25)
    observed = exact_infoset_action_baselines(
        spec,
        traverser=0,
        own_hand_index=0,
        player=1,
        node=node,
        policy=policy,
    )
    actions = _actions(spec, 1, node)
    assert actions == ("FOLD", "CALL")

    deals = [(i, j, w) for i, j, w in _valid_deals(spec) if i == 0]
    total = sum(w for _, _, w in deals)
    expected_fold = float(spec.pot) / 2.0
    expected_call = sum(
        (w / total) * _terminal_showdown(spec, i, j, 25)
        for i, j, w in deals
    )
    assert observed == pytest.approx((expected_fold, expected_call), abs=1e-12)


def test_p1_late_baseline_conditions_hidden_p0_posterior_on_observed_check():
    spec = fixture_spec()
    policy = uniform_policy(spec)
    root_actions = _actions(spec, 0, ROOT)
    check_idx = root_actions.index("CHECK")
    check_probs = (0.1, 0.5, 0.9)
    for i, check_prob in enumerate(check_probs):
        rest = (1.0 - check_prob) / (len(root_actions) - 1)
        probs = [rest] * len(root_actions)
        probs[check_idx] = check_prob
        policy[(0, ROOT, i)] = tuple(probs)

    node = p0_vs_bet_node(25)
    observed = exact_infoset_action_baselines(
        spec,
        traverser=1,
        own_hand_index=0,
        player=0,
        node=node,
        policy=policy,
    )
    actions = _actions(spec, 0, node)
    assert actions == ("FOLD", "CALL")

    weighted = []
    for i, j, raw_weight in _valid_deals(spec):
        if j != 0:
            continue
        weighted.append((i, j, raw_weight * check_probs[i]))
    total = sum(w for _, _, w in weighted)
    expected_fold = -float(spec.pot) / 2.0
    expected_call = sum(
        (w / total) * _terminal_showdown(spec, i, j, 25)
        for i, j, w in weighted
    )
    assert observed == pytest.approx((expected_fold, expected_call), abs=1e-12)


def test_baseline_api_and_value_do_not_depend_on_realized_opponent_hand():
    spec = fixture_spec()
    policy = uniform_policy(spec)
    # There is deliberately no opponent-hand argument. Repeating the same
    # traverser-visible information must return the same baseline even though in
    # actual sampled histories j could be any compatible hidden hand.
    a = exact_infoset_action_baselines(
        spec,
        traverser=0,
        own_hand_index=1,
        player=1,
        node=p1_vs_bet_node(50),
        policy=policy,
    )
    b = exact_infoset_action_baselines(
        spec,
        traverser=0,
        own_hand_index=1,
        player=1,
        node=p1_vs_bet_node(50),
        policy=policy,
    )
    assert a == b


def test_no_leak_baseline_ignores_hole_card_order():
    normal = fixture_spec(reverse_holes=False)
    reversed_spec = fixture_spec(reverse_holes=True)
    normal_policy = uniform_policy(normal)
    reversed_policy = uniform_policy(reversed_spec)
    for traverser, own, player, node in (
        (0, 0, 1, p1_vs_bet_node(25)),
        (0, 2, 1, p1_vs_bet_node(100)),
        (1, 0, 0, ROOT),
        (1, 2, 0, p0_vs_bet_node(50)),
    ):
        assert exact_infoset_action_baselines(
            normal,
            traverser=traverser,
            own_hand_index=own,
            player=player,
            node=node,
            policy=normal_policy,
        ) == pytest.approx(
            exact_infoset_action_baselines(
                reversed_spec,
                traverser=traverser,
                own_hand_index=own,
                player=player,
                node=node,
                policy=reversed_policy,
            ),
            abs=1e-12,
        )


def test_zero_visible_posterior_mass_fails_closed():
    spec = fixture_spec()
    policy = uniform_policy(spec)
    root_actions = _actions(spec, 0, ROOT)
    check_idx = root_actions.index("CHECK")
    for i in range(len(spec.p0_range)):
        probs = [1.0 / (len(root_actions) - 1)] * len(root_actions)
        probs[check_idx] = 0.0
        policy[(0, ROOT, i)] = tuple(probs)

    with pytest.raises(ValueError, match="no positive"):
        exact_infoset_action_baselines(
            spec,
            traverser=1,
            own_hand_index=0,
            player=0,
            node=p0_vs_bet_node(25),
            policy=policy,
        )
