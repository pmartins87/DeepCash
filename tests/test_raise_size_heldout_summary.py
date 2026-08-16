import json

import pytest

from deepcash_core.raise_size_summary import (
    EXPECTED_ANALYSIS_SCHEMA,
    EXPECTED_CANDIDATES,
    summarize_directory,
)


def _analysis(spr: float, rows: dict[str, tuple[float, float, float]]) -> dict:
    aggregate = []
    for candidate in EXPECTED_CANDIDATES:
        mean_loss, worst_loss, seconds = rows[candidate]
        aggregate.append(
            {
                "candidate": candidate,
                "checkpoint": 3600,
                "mean_loss_upper_per_pot": mean_loss,
                "worst_board_loss_upper_per_pot": worst_loss,
                "mean_value_interval_width_per_pot": mean_loss / 2.0,
                "worst_value_interval_width_per_pot": worst_loss / 2.0,
                "total_cumulative_training_seconds": seconds,
            }
        )
    return {
        "schema": EXPECTED_ANALYSIS_SCHEMA,
        "latest_checkpoint": 3600,
        "latest_checkpoint_aggregate": aggregate,
        "source_geometry": {
            "restriction_dimension": "raise_size",
            "spr": spr,
            "stack": int(100 * spr),
            "pot": 100,
            "range_combos": 6,
            "p0_phase": 0.22,
            "p1_phase": 0.68,
        },
    }


def test_summary_is_fail_closed_and_builds_descriptive_pareto_front(tmp_path):
    base = {
        "Q1_100": (0.0040, 0.0100, 100.0),
        "Q2_50_100": (0.0010, 0.0020, 110.0),
        "Q2_100_150": (0.0045, 0.0110, 105.0),
        "Q3_50_100_150": (0.0011, 0.0021, 120.0),
    }
    for spr in (1.0, 2.0, 4.0):
        payload = _analysis(spr, base)
        path = tmp_path / f"river_raise_size_heldout_{int(spr * 100)}_analysis.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

    summary = summarize_directory(tmp_path, required_sprs=(1.0, 2.0, 4.0))
    assert summary["sprs"] == [1.0, 2.0, 4.0]
    assert summary["descriptive_pareto_front"] == ["Q1_100", "Q2_50_100"]

    rows = {row["candidate"]: row for row in summary["candidate_summary"]}
    assert rows["Q3_50_100_150"]["dominated_by"] == ["Q2_50_100"]
    assert "Q1_100" in rows["Q2_100_150"]["dominated_by"]
    assert rows["Q2_50_100"]["max_worst_resolved_excess_per_pot"] == pytest.approx(0.001)


def test_summary_rejects_missing_candidate(tmp_path):
    rows = {
        "Q1_100": (0.0040, 0.0100, 100.0),
        "Q2_50_100": (0.0010, 0.0020, 110.0),
        "Q2_100_150": (0.0045, 0.0110, 105.0),
        "Q3_50_100_150": (0.0011, 0.0021, 120.0),
    }
    payload = _analysis(1.0, rows)
    payload["latest_checkpoint_aggregate"].pop()
    path = tmp_path / "river_raise_size_heldout_100_analysis.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="candidate set mismatch"):
        summarize_directory(tmp_path)


def test_summary_rejects_duplicate_spr(tmp_path):
    rows = {
        "Q1_100": (0.0040, 0.0100, 100.0),
        "Q2_50_100": (0.0010, 0.0020, 110.0),
        "Q2_100_150": (0.0045, 0.0110, 105.0),
        "Q3_50_100_150": (0.0011, 0.0021, 120.0),
    }
    payload = _analysis(2.0, rows)
    for suffix in ("200", "201"):
        (tmp_path / f"river_raise_size_heldout_{suffix}_analysis.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    with pytest.raises(ValueError, match="duplicate SPR"):
        summarize_directory(tmp_path)
