import random

import pytest

from deepcash_core.cards import card_from_str
from deepcash_core.river_external_sampling import (
    WeightedDealSampler,
    _weighted_choice_index,
)
from deepcash_core.river_lab import RangeCombo, RiverGameSpec, _valid_deals


def c(text: str) -> int:
    return card_from_str(text)


def combo(a: str, b: str, weight: float = 1.0) -> RangeCombo:
    return RangeCombo((c(a), c(b)), weight)


def fixture_spec() -> RiverGameSpec:
    return RiverGameSpec(
        board=(c("Ah"), c("Kd"), c("9c"), c("7s"), c("2h")),
        p0_range=(
            combo("Qs", "Qh", 0.2),
            combo("Jc", "Js", 1.7),
            combo("8c", "8d", 0.9),
        ),
        p1_range=(
            combo("Qd", "Jh", 1.3),
            combo("Jd", "Th", 0.4),
            combo("6c", "6d", 2.1),
        ),
        pot=100,
        bet_sizes=(25, 50, 100),
    )


def test_precomputed_sampler_is_bit_sequence_equivalent_to_legacy_linear_choice():
    spec = fixture_spec()
    raw = _valid_deals(spec)
    weights = [weight for _, _, weight in raw]
    sampler = WeightedDealSampler.from_spec(spec)
    legacy_rng = random.Random(20260816)
    fast_rng = random.Random(20260816)

    for _ in range(10000):
        legacy_index = _weighted_choice_index(legacy_rng, weights)
        expected = raw[legacy_index][:2]
        assert sampler.sample(fast_rng) == expected

    assert fast_rng.getstate() == legacy_rng.getstate()


def test_quantile_matches_exact_legacy_cumulative_boundaries():
    spec = fixture_spec()
    raw = _valid_deals(spec)
    sampler = WeightedDealSampler.from_spec(spec)
    total = sum(weight for _, _, weight in raw)
    running = 0.0
    for index, (_, _, weight) in enumerate(raw[:-1]):
        running += weight
        boundary = running / total
        # Legacy selection is first cumulative mass strictly greater than target,
        # so an exact boundary belongs to the following bucket.
        assert sampler.quantile(boundary) == raw[index + 1][:2]


def test_sampler_rejects_invalid_quantiles():
    sampler = WeightedDealSampler.from_spec(fixture_spec())
    for value in (-0.1, 1.0, float("nan")):
        with pytest.raises(ValueError):
            sampler.quantile(value)
