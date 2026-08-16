from deepcash_core.reference_convergence_analysis import analyze


def payload():
    rows = []
    for board, base in (("dry", 0.20), ("paired", 0.24)):
        for candidate, bump in (("S1", 0.00), ("S2", 0.03)):
            for checkpoint, scale in ((20, 1.0), (80, 0.5), (200, 0.25)):
                width = (base + bump) * scale
                upper = (base + bump + 0.05) * scale
                rows.append(
                    {
                        "board": board,
                        "candidate": candidate,
                        "checkpoint": checkpoint,
                        "max_value_interval_width_per_pot": width,
                        "worst_loss_upper_per_pot": upper,
                        "reference_cumulative_train_seconds": checkpoint / 1000,
                        "p0_cumulative_train_seconds": checkpoint / 900,
                        "p1_cumulative_train_seconds": checkpoint / 800,
                    }
                )
    return {
        "schema": "DEEPCASH_RIVER_REFERENCE_CONVERGENCE_V1",
        "checkpoints": [20, 80, 200],
        "rows": rows,
    }


def test_analyzer_reports_tightening_without_inventing_threshold():
    result = analyze(payload())
    assert result["latest_checkpoint"] == 200
    assert result["all_curves_tightened_interval_vs_first"] is True
    assert len(result["curves"]) == 4
    assert len(result["latest_checkpoint_aggregate"]) == 2
    assert "No arbitrary strategic acceptance threshold" in result["methodology_note"]


def test_latest_aggregate_uses_all_boards_and_conservative_worst_values():
    result = analyze(payload())
    s1 = next(x for x in result["latest_checkpoint_aggregate"] if x["candidate"] == "S1")
    assert s1["boards"] == 2
    # paired board has larger synthetic uncertainty than dry board.
    assert s1["worst_value_interval_width_per_pot"] == 0.24 * 0.25
    assert s1["worst_board_loss_upper_per_pot"] == (0.24 + 0.05) * 0.25


def test_analyzer_rejects_negative_or_nonfinite_uncertainty():
    bad = payload()
    bad["rows"][0]["max_value_interval_width_per_pot"] = -0.1
    try:
        analyze(bad)
    except ValueError as exc:
        assert "finite and non-negative" in str(exc)
    else:
        raise AssertionError("negative uncertainty must fail closed")


def test_curve_can_report_nonmonotonic_noise_without_failing_or_relaxing_it():
    noisy = payload()
    target = [r for r in noisy["rows"] if r["board"] == "dry" and r["candidate"] == "S1"]
    target[1]["max_value_interval_width_per_pot"] = target[0]["max_value_interval_width_per_pot"] * 1.1
    result = analyze(noisy)
    curve = next(c for c in result["curves"] if c["board"] == "dry" and c["candidate"] == "S1")
    assert curve["interval_width_nonincreasing"] is False
    # Final point still tightened versus the first; diagnostic and acceptance are separate.
    assert curve["last_interval_width_per_pot"] < curve["first_interval_width_per_pot"]


def test_same_analyzer_accepts_one_raise_reference_schema_without_reinterpreting_rows():
    raised = payload()
    raised["schema"] = "DEEPCASH_RIVER_RAISE_REFERENCE_CONVERGENCE_V1"
    result = analyze(raised)
    assert result["source_schema"] == "DEEPCASH_RIVER_RAISE_REFERENCE_CONVERGENCE_V1"
    assert result["schema"] == "DEEPCASH_RIVER_RAISE_REFERENCE_CONVERGENCE_ANALYSIS_V1"
    assert result["latest_checkpoint"] == 200
    assert len(result["latest_checkpoint_aggregate"]) == 2


def test_analyzer_preserves_geometry_coordinates_for_matrix_aggregation():
    raised = payload()
    raised.update(
        {
            "schema": "DEEPCASH_RIVER_RAISE_REFERENCE_CONVERGENCE_V1",
            "pot": 100,
            "stack": 200,
            "spr": 2.0,
            "range_combos": 4,
            "restriction_dimension": "opening_size",
        }
    )
    result = analyze(raised)
    assert result["source_geometry"] == {
        "pot": 100,
        "stack": 200,
        "spr": 2.0,
        "range_combos": 4,
        "restriction_dimension": "opening_size",
    }
