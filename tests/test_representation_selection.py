import pytest

from deepcash_core.representation_selection import (
    aggregate_candidate_metrics,
    largest_shared_checkpoint,
    pareto_frontier,
)


def row(candidate: str, checkpoint: int, upper: float, compression: float, slots: int):
    return {
        "candidate": candidate,
        "checkpoint": checkpoint,
        "worst_loss_upper_per_pot": upper,
        "max_value_interval_width_per_pot": 0.002,
        "bucket_compression_ratio": compression,
        "joint_infosets": slots,
        "reference_infosets": 100,
        "joint_action_slots": slots,
        "reference_action_slots": 100,
        "joint_cumulative_train_seconds": float(slots) / 10.0,
    }


def payload(rows):
    return {"rows": rows}


def test_largest_shared_checkpoint_requires_every_candidate_in_every_payload():
    p1 = payload(
        [
            row("small", 100, 0.03, 0.3, 30),
            row("small", 400, 0.02, 0.3, 30),
            row("large", 100, 0.01, 0.8, 80),
            row("large", 400, 0.005, 0.8, 80),
        ]
    )
    p2 = payload(
        [
            row("small", 100, 0.04, 0.3, 30),
            row("small", 400, 0.025, 0.3, 30),
            row("large", 100, 0.012, 0.8, 80),
            row("large", 400, 0.006, 0.8, 80),
        ]
    )
    assert largest_shared_checkpoint([p1, p2]) == 400


def test_pareto_frontier_keeps_strategic_cost_tradeoff_and_drops_dominated():
    metrics = {
        "cheap_lossy": {
            "worst_upper": 0.03,
            "mean_upper": 0.02,
            "mean_joint_action_slot_ratio": 0.3,
            "mean_compression": 0.3,
        },
        "expensive_strong": {
            "worst_upper": 0.005,
            "mean_upper": 0.004,
            "mean_joint_action_slot_ratio": 0.8,
            "mean_compression": 0.8,
        },
        "dominated": {
            "worst_upper": 0.04,
            "mean_upper": 0.03,
            "mean_joint_action_slot_ratio": 0.5,
            "mean_compression": 0.5,
        },
    }
    assert pareto_frontier(metrics) == ["cheap_lossy", "expensive_strong"]


def test_aggregate_uses_only_largest_shared_checkpoint_and_reports_ratios():
    payloads = []
    for bump in (0.0, 0.002):
        payloads.append(
            payload(
                [
                    row("small", 100, 0.05 + bump, 0.3, 30),
                    row("small", 400, 0.020 + bump, 0.3, 30),
                    row("large", 100, 0.02 + bump, 0.8, 80),
                    row("large", 400, 0.005 + bump, 0.8, 80),
                ]
            )
        )
    summary = aggregate_candidate_metrics(payloads)
    assert summary["shared_checkpoint"] == 400
    assert summary["metrics"]["small"]["worst_upper"] == pytest.approx(0.022)
    assert summary["metrics"]["large"]["mean_joint_action_slot_ratio"] == pytest.approx(0.8)
    assert set(summary["pareto_frontier"]) == {"small", "large"}


def test_candidate_set_mismatch_fails_closed():
    p1 = payload([row("a", 100, 0.1, 0.5, 50), row("b", 100, 0.1, 0.5, 50)])
    p2 = payload([row("a", 100, 0.1, 0.5, 50)])
    with pytest.raises(ValueError):
        largest_shared_checkpoint([p1, p2])
