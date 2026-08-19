from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "run_r5_physical_ryzen_crossover.py"
CONFIG = ROOT / "deepcash_core" / "data" / "r5_physical_ryzen_crossover_v1.json"
_spec = importlib.util.spec_from_file_location("r5_physical_runner", SCRIPT)
assert _spec is not None and _spec.loader is not None
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)


def load_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_frozen_config_and_public_cell_count():
    config = load_config()
    runner.validate_config(config)
    cells = runner.expected_public_coordinates(config)
    assert len(cells) == 24
    assert len({(x["board"], x["support"], x["phase"]) for x in cells}) == 24


def test_config_drift_fails_closed():
    config = load_config()
    config["budget_seconds_per_cell"] = 29.0
    with pytest.raises(ValueError, match="budget"):
        runner.validate_config(config)


def test_build_spec_uses_frozen_geometry():
    spec = runner.build_spec(load_config(), "physical_ace_mid", 8, "P_A")
    assert len(spec.p0_range) == 8
    assert len(spec.p1_range) == 8
    assert spec.pot == 100
    assert spec.bet_sizes == (25, 50, 100)


def test_chunk_estimator_is_bounded_and_deterministic():
    assert runner.next_chunk_iterations(
        completed_iterations=0,
        cumulative_train_seconds=0.0,
        remaining_seconds=30.0,
        initial=64,
        minimum=1,
        maximum=4096,
    ) == 64
    assert runner.next_chunk_iterations(
        completed_iterations=1000,
        cumulative_train_seconds=10.0,
        remaining_seconds=5.0,
        initial=64,
        minimum=1,
        maximum=4096,
    ) == 500
    assert runner.next_chunk_iterations(
        completed_iterations=100000,
        cumulative_train_seconds=1.0,
        remaining_seconds=30.0,
        initial=64,
        minimum=1,
        maximum=4096,
    ) == 4096


def synthetic_support_summary(*, exact_mean=0.01, ccs_mean=0.02, zero_mean=0.03, exact_wins=6):
    names = runner.ALGORITHMS
    means = {
        "ALT_DCFR_150_0_2": exact_mean,
        "CCS_CFR_PLUS_LINEAR": ccs_mean,
        "ES_ZERO": zero_mean,
    }
    pairwise = {name: {} for name in names}
    for left in names:
        for right in names:
            if left == right:
                continue
            wins = exact_wins if left == "ALT_DCFR_150_0_2" else 2
            if right == "ALT_DCFR_150_0_2" and left != "ALT_DCFR_150_0_2":
                wins = 8 - exact_wins
            pairwise[left][right] = {"strict_wins": wins}
    return {
        "algorithms": {
            name: {"mean_exploitability_per_pot": means[name]} for name in names
        },
        "pairwise": pairwise,
    }


def test_support_leader_requires_mean_and_majority_pairwise_wins():
    resolved = runner.classify_support(synthetic_support_summary(exact_wins=6))
    assert resolved == {
        "status": "RESOLVED",
        "leader": "ALT_DCFR_150_0_2",
        "required_paired_wins": 5,
    }

    unresolved = runner.classify_support(synthetic_support_summary(exact_wins=4))
    assert unresolved["status"] == "UNRESOLVED"
    assert unresolved["leader"] is None


def test_algorithm_initializers_start_clean():
    config = load_config()
    spec = runner.build_spec(config, "physical_connected", 8, "P_B")
    for algorithm in runner.ALGORITHMS:
        state = runner.init_algorithm(spec, algorithm, 809)
        assert state.iterations == 0
