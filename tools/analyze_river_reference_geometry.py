from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def analyze(payload: dict) -> dict:
    if payload.get("schema") != "DEEPCASH_RIVER_REFERENCE_GEOMETRY_DP_V1":
        raise ValueError("unsupported geometry benchmark schema")
    by_candidate: dict[str, list[dict]] = defaultdict(list)
    for row in payload["rows"]:
        by_candidate[str(row["candidate"])].append(row)

    summary = []
    expected_cells = {
        (str(r["geometry"]), str(r["board"])) for r in payload["rows"]
    }
    for candidate, rows in sorted(by_candidate.items()):
        cells = {(str(r["geometry"]), str(r["board"])) for r in rows}
        if cells != expected_cells:
            raise ValueError(
                f"incomplete geometry/board coverage for {candidate}: "
                f"got={len(cells)} expected={len(expected_cells)}"
            )
        upper = [float(r["worst_loss_upper_per_pot"]) for r in rows]
        intervals = [float(r["max_value_interval_width_per_pot"]) for r in rows]
        total_train = sum(
            float(r["reference_train_seconds"])
            + float(r["p0_train_seconds"])
            + float(r["p1_train_seconds"])
            for r in rows
        )
        worst_row = max(rows, key=lambda r: float(r["worst_loss_upper_per_pot"]))
        widest_row = max(rows, key=lambda r: float(r["max_value_interval_width_per_pot"]))
        summary.append(
            {
                "candidate": candidate,
                "cells": len(rows),
                "mean_loss_upper_per_pot": sum(upper) / len(upper),
                "worst_loss_upper_per_pot": max(upper),
                "worst_loss_geometry": str(worst_row["geometry"]),
                "worst_loss_board": str(worst_row["board"]),
                "mean_value_interval_width_per_pot": sum(intervals) / len(intervals),
                "worst_value_interval_width_per_pot": max(intervals),
                "widest_interval_geometry": str(widest_row["geometry"]),
                "widest_interval_board": str(widest_row["board"]),
                "total_train_seconds_sum": total_train,
            }
        )

    return {
        "schema": "DEEPCASH_RIVER_REFERENCE_GEOMETRY_ANALYSIS_V1",
        "methodology_note": (
            "This is a conservative common-reference restriction-loss summary. "
            "No production winner or acceptance threshold is inferred from hosted-CI timing."
        ),
        "candidate_summary": summary,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Aggregate DeepCash multi-SPR reference restriction evidence")
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, default=Path("river_reference_geometry_analysis.json"))
    args = ap.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyze(payload)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for row in result["candidate_summary"]:
        print(
            f"{row['candidate']}: mean_upper={row['mean_loss_upper_per_pot']:.6f} "
            f"worst_upper={row['worst_loss_upper_per_pot']:.6f} "
            f"worst={row['worst_loss_geometry']}/{row['worst_loss_board']} "
            f"worst_interval={row['worst_value_interval_width_per_pot']:.6f}"
        )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
