import itertools

import pytest

from deepcash_core.vr_mccfr_baseline import (
    baseline_enhanced_action_values,
    baseline_enhanced_node_value,
)


def exact_value(sigma, child_values):
    return sum(p * v for p, v in zip(sigma, child_values))


def expected_sampled_value(*, sigma, q, baselines, child_values):
    return sum(
        q[a]
        * baseline_enhanced_node_value(
            target_policy=sigma,
            sampling_policy=q,
            baselines=baselines,
            sampled_action=a,
            sampled_child_value=child_values[a],
        )
        for a in range(len(q))
        if q[a] > 0.0
    )


@pytest.mark.parametrize(
    "sigma,q,baselines,child_values",
    [
        ((0.2, 0.3, 0.5), (0.2, 0.3, 0.5), (0.0, 0.0, 0.0), (7.0, -2.0, 4.0)),
        ((0.1, 0.6, 0.3), (0.5, 0.2, 0.3), (3.0, -1.0, 8.0), (9.0, 5.0, -4.0)),
        ((0.0, 0.25, 0.75), (0.2, 0.3, 0.5), (100.0, -7.0, 1.5), (-3.0, 4.0, 10.0)),
    ],
)
def test_baseline_estimator_is_exactly_unbiased_by_sample_enumeration(
    sigma, q, baselines, child_values
):
    observed = expected_sampled_value(
        sigma=sigma,
        q=q,
        baselines=baselines,
        child_values=child_values,
    )
    assert observed == pytest.approx(exact_value(sigma, child_values), abs=1e-12)


def test_zero_baseline_on_policy_reduces_to_ordinary_sampled_node_value():
    sigma = q = (0.2, 0.3, 0.5)
    child_values = (7.0, -2.0, 4.0)
    for sampled in range(3):
        estimate = baseline_enhanced_node_value(
            target_policy=sigma,
            sampling_policy=q,
            baselines=(0.0, 0.0, 0.0),
            sampled_action=sampled,
            sampled_child_value=child_values[sampled],
        )
        # On-policy q=sigma makes sigma[a*]/q[a*] == 1. Zero baselines
        # therefore reproduce the ordinary sampled child return exactly.
        assert estimate == pytest.approx(child_values[sampled])


def test_perfect_baseline_has_zero_variance_for_every_sampled_action():
    sigma = (0.15, 0.35, 0.50)
    q = (0.4, 0.2, 0.4)
    child_values = (12.0, -5.0, 3.0)
    expected = exact_value(sigma, child_values)
    for sampled in range(3):
        estimate = baseline_enhanced_node_value(
            target_policy=sigma,
            sampling_policy=q,
            baselines=child_values,
            sampled_action=sampled,
            sampled_child_value=child_values[sampled],
        )
        assert estimate == pytest.approx(expected, abs=1e-12)


def test_action_vector_matches_source_control_variate_formula():
    estimates = baseline_enhanced_action_values(
        sampling_policy=(0.25, 0.75),
        baselines=(4.0, -1.0),
        sampled_action=0,
        sampled_child_value=10.0,
    )
    assert estimates == pytest.approx((4.0 + (10.0 - 4.0) / 0.25, -1.0))


def test_off_policy_unbiasedness_for_many_small_rational_cases():
    child = (3.0, -1.0)
    baseline_sets = ((0.0, 0.0), (7.0, -4.0), child)
    probability_pairs = (
        ((0.25, 0.75), (0.5, 0.5)),
        ((0.5, 0.5), (0.25, 0.75)),
        ((0.75, 0.25), (0.1, 0.9)),
    )
    for (sigma, q), baselines in itertools.product(probability_pairs, baseline_sets):
        assert expected_sampled_value(
            sigma=sigma, q=q, baselines=baselines, child_values=child
        ) == pytest.approx(exact_value(sigma, child), abs=1e-12)


@pytest.mark.parametrize(
    "kwargs,match",
    [
        (
            dict(
                target_policy=(0.5, 0.5),
                sampling_policy=(1.0, 0.0),
                baselines=(0.0, 0.0),
                sampled_action=0,
                sampled_child_value=1.0,
            ),
            "target-positive",
        ),
        (
            dict(
                target_policy=(0.5, 0.5),
                sampling_policy=(0.5, 0.5),
                baselines=(0.0,),
                sampled_action=0,
                sampled_child_value=1.0,
            ),
            "baseline length",
        ),
        (
            dict(
                target_policy=(0.5, 0.5),
                sampling_policy=(0.5, 0.5),
                baselines=(0.0, 0.0),
                sampled_action=2,
                sampled_child_value=1.0,
            ),
            "outside action support",
        ),
    ],
)
def test_invalid_support_and_shape_fail_closed(kwargs, match):
    with pytest.raises(ValueError, match=match):
        baseline_enhanced_node_value(**kwargs)
