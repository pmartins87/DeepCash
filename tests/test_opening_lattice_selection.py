from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from deepcash_core.river_benchmark_fixtures import ONE_RAISE_OPEN_SUBSET_LATTICE


def _analysis_payload(board_set, stack, combos, p0_phase, p1_phase, losses):
    curves = []
    aggregates = []
    for idx, candidate in enumerate(sorted(ONE_RAISE_OPEN_SUBSET_LATTICE)):
        loss = float(losses[candidate])
        curves.append(
            {
                "board": f"board_{board_set}_{stack}",
                "candidate": candidate,
                "last_loss_upper_per_pot": loss,
                "last_interval_width_per_pot": 0.001 + idx * 1e-6,
            }
        )
        aggregates.append(
            {
                "candidate": candidate,
                "total_cumulative_training_seconds": 100.0 + idx,
            }
        )
    return {
        "source_geometry": {
            "board_set": board_set,
            "stack": stack,
            "range_combos": combos,
            "p0_phase": p0_phase,
            "p1_phase": p1_phase,
        },
        "latest_checkpoint": 3000,
        "curves": curves,
        "latest_checkpoint_aggregate": aggregates,
    }


def test_precommitted_lattice_selector_forwards_one_champion_per_cardinality(tmp_path: Path):
    candidates = sorted(ONE_RAISE_OPEN_SUBSET_LATTICE)
    base = {name: 0.1 + 0.001 * i for i, name in enumerate(candidates)}
    base["L1_25"] = 0.010
    base["L2_25_50"] = 0.005
    base["L3_25_50_75"] = 0.002

    cells = (
        ("control", 100, 4, 0.00, 0.27),
        ("control", 400, 4, 0.00, 0.27),
        ("heldout", 100, 6, 0.13, 0.61),
        ("heldout", 400, 6, 0.13, 0.61),
    )
    for i, cell in enumerate(cells):
        payload = _analysis_payload(*cell, base)
        (tmp_path / f"cell_{i}_analysis.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    out = tmp_path / "champions.json"
    subprocess.run(
        [
            sys.executable,
            "tools/select_opening_lattice_champions.py",
            str(tmp_path),
            "--out",
            str(out),
        ],
        check=True,
    )
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["champions"]["1"]["candidate"] == "L1_25"
    assert result["champions"]["2"]["candidate"] == "L2_25_50"
    assert result["champions"]["3"]["candidate"] == "L3_25_50_75"
    assert len(result["rankings"]["1"]) == 4
    assert len(result["rankings"]["2"]) == 6
    assert len(result["rankings"]["3"]) == 4


def _heldout_v2_analysis(stack: int):
    candidates = ("L1_25", "L2_25_50", "L3_25_50_75")
    curves = []
    aggregates = []
    for i, candidate in enumerate(candidates):
        for board_idx in range(2):
            curves.append(
                {
                    "board": f"v2_{board_idx}",
                    "candidate": candidate,
                    "last_loss_upper_per_pot": 0.01 / (i + 1) + board_idx * 0.0001,
                    "last_interval_width_per_pot": 0.001 + board_idx * 0.0001,
                }
            )
        aggregates.append(
            {
                "candidate": candidate,
                "mean_loss_upper_per_pot": 0.01 / (i + 1),
                "worst_board_loss_upper_per_pot": 0.011 / (i + 1),
                "mean_value_interval_width_per_pot": 0.001,
                "worst_value_interval_width_per_pot": 0.0011,
                "total_cumulative_training_seconds": float(stack + i),
            }
        )
    return {
        "source_geometry": {
            "board_set": "heldout_v2",
            "stack": stack,
            "range_combos": 8,
            "p0_phase": 0.31,
            "p1_phase": 0.79,
        },
        "latest_checkpoint": 3600,
        "curves": curves,
        "latest_checkpoint_aggregate": aggregates,
    }


def test_heldout_v2_summary_requires_three_precommitted_sprs_and_preserves_cardinality(tmp_path: Path):
    for stack in (100, 200, 400):
        (tmp_path / f"heldout_v2_{stack}_analysis.json").write_text(
            json.dumps(_heldout_v2_analysis(stack)), encoding="utf-8"
        )

    out = tmp_path / "summary.json"
    subprocess.run(
        [
            sys.executable,
            "tools/summarize_opening_heldout_v2.py",
            str(tmp_path),
            "--out",
            str(out),
        ],
        check=True,
    )
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["sprs"] == [1.0, 2.0, 4.0]
    assert [row["cardinality"] for row in result["summary"]] == [1, 2, 3]
    assert all(row["heldout_board_rows"] == 6 for row in result["summary"])
