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
from deepcash_core.river_vr_infoset_baseline_v2 import (
    exact_infoset_action_baselines_v2,
)


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


def test_p0_baseline_equals_independent_hidden_p1_weighted_average():
    spec = fixture_spec()
    policy = uniform_policy(spec)
    node = p1_vs_bet_node(25)
    observed = exact_infoset_action_baselines_v2(
        spec,
        traverser=0,
        own_hand_index=0,
        player=1,
        node=node,
        policy=policy,
    )
    deals = [(i, j, w) for i, j, w in _valid_deals(spec) if i == 0]
    total = sum(w for _, _, w in deals)
    expected = (
        float(spec.pot) / 2.0,
        sum((w / total) * _terminal_showdown(spec, i, j, 25) for i, j, w in deals),
    )
    assert observed == pytest.approx(expected, abs=1e-12)


def test_p1_late_baseline_conditions_hidden_p0_on_public_check():
    spec = fixture_spec()
    policy = uniform_policy(spec)
    root_actions = _actions(spec, 0, ROOT)
    check_index = root_actions.index("CHECK")
    check_probs = (0.1, 0.5, 0.9)
    for i, check_prob in enumerate(check_probs):
        other = (1.0 - check_prob) / (len(root_actions) - 1)
        probs = [other] * len(root_actions)
        probs[check_index] = check_prob
        policy[(0, ROOT, i)] = tuple(probs)

    node = p0_vs_bet_node(25)
    observed = exact_infoset_action_baselines_v2(
        spec,
        traverser=1,
        own_hand_index=0,
        player=0,
        node=node,
        policy=policy,
    )
    weighted = [
        (i, j, w * check_probs[i])
        for i, j, w in _valid_deals(spec)
        if j == 0
    ]
    total = sum(w for _, _, w in weighted)
    expected = (
        -float(spec.pot) / 2.0,
        sum((w / total) * _terminal_showdown(spec, i, j, 25) for i, j, w in weighted),
    )
    assert observed == pytest.approx(expected, abs=1e-12)


def test_api_has_no_realized_opponent_hand_dependency():
    spec = fixture_spec()
    policy = uniform_policy(spec)
    kwargs = dict(
        traverser=0,
        own_hand_index=1,
        player=1,
        node=p1_vs_bet_node(50),
        policy=policy,
    )
    assert exact_infoset_action_baselines_v2(spec, **kwargs) == (
        exact_infoset_action_baselines_v2(spec, **kwargs)
    )


def test_no_leak_baseline_preserves_hole_card_order_invariance():
    normal = fixture_spec(reverse_holes=False)
    reversed_spec = fixture_spec(reverse_holes=True)
    normal_policy = uniform_policy(normal)
    reversed_policy = uniform_policy(reversed_spec)
    fixtures = (
        (0, 0, 1, p1_vs_bet_node(25)),
        (0, 2, 1, p1_vs_bet_node(100)),
        (1, 0, 0, ROOT),
        (1, 2, 0, p0_vs_bet_node(50)),
    )
    for traverser, own, player, node in fixtures:
        a = exact_infoset_action_baselines_v2(
            normal,
            traverser=traverser,
            own_hand_index=own,
            player=player,
            node=node,
            policy=normal_policy,
        )
        b = exact_infoset_action_baselines_v2(
            reversed_spec,
            traverser=traverser,
            own_hand_index=own,
            player=player,
            node=node,
            policy=reversed_policy,
        )
        assert a == pytest.approx(b, abs=1e-12)


def test_zero_visible_posterior_mass_fails_closed():
    spec = fixture_spec()
    policy = uniform_policy(spec)
    root_actions = _actions(spec, 0, ROOT)
    check_index = root_actions.index("CHECK")
    for i in range(len(spec.p0_range)):
        probs = [1.0 / (len(root_actions) - 1)] * len(root_actions)
        probs[check_index] = 0.0
        policy[(0, ROOT, i)] = tuple(probs)

    with pytest.raises(ValueError, match="no positive"):
        exact_infoset_action_baselines_v2(
            spec,
            traverser=1,
            own_hand_index=0,
            player=0,
            node=p0_vs_bet_node(25),
            policy=policy,
        )
