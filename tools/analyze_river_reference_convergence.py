from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable


def _finite_nonnegative(value: float, *, name: str) -> float:
    x = float(value)
    if x < 0.0 or x != x or x in (float("inf"), float("-inf")):
        raise ValueError(f"{name} must be finite and non-negative: {value!r}")
    return x


def _group_rows(payload: dict) -> dict[tuple[str, str], list[dict]]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for raw in payload["rows"]:
        board = str(raw["board"])
        candidate = str(raw["candidate"])
        row = dict(raw)
        row["checkpoint"] = int(row["checkpoint"])
        row["worst_loss_upper_per_pot"] = _finite_nonnegative(
            row["worst_loss_upper_per_pot"], name="worst_loss_upper_per_pot"
        )
        row["max_value_interval_width_per_pot"] = _finite_nonnegative(
            row["max_value_interval_width_per_pot"], name="max_value_interval_width_per_pot"
        )
        grouped[(board, candidate)].append(row)

    for key, rows in grouped.items():
        rows.sort(key=lambda r: r["checkpoint"])
        checkpoints = [r["checkpoint"] for r in rows]
        if len(set(checkpoints)) != len(checkpoints):
            raise ValueError(f"duplicate checkpoint for {key}: {checkpoints}")
    return grouped


def summarize_curve(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("curve cannot be empty")
    first = rows[0]
    last = rows[-1]
    first_width = float(first["max_value_interval_width_per_pot"])
    last_width = float(last["max_value_interval_width_per_pot"])
    first_upper = float(first["worst_loss_upper_per_pot"])
    last_upper = float(last["worst_loss_upper_per_pot"])
    return {
        "board": str(first["board"]),
        "candidate": str(first["candidate"]),
        "first_checkpoint": int(first["checkpoint"]),
        "last_checkpoint": int(last["checkpoint"]),
        "first_interval_width_per_pot": first_width,
        "last_interval_width_per_pot": last_width,
        "interval_width_ratio_last_over_first": (
            last_width / first_width if first_width > 0.0 else 0.0
        ),
        "first_loss_upper_per_pot": first_upper,
        "last_loss_upper_per_pot": last_upper,
        "loss_upper_ratio_last_over_first": (
            last_upper / first_upper if first_upper > 0.0 else 0.0
        ),
        "minimum_interval_width_per_pot": min(
            float(r["max_value_interval_width_per_pot"]) for r in rows
        ),
        "minimum_loss_upper_per_pot": min(
            float(r["worst_loss_upper_per_pot"]) for r in rows
        ),
        "interval_width_nonincreasing": all(
            float(b["max_value_interval_width_per_pot"])
            <= float(a["max_value_interval_width_per_pot"]) + 1e-15
            for a, b in zip(rows, rows[1:])
        ),
        "loss_upper_nonincreasing": all(
            float(b["worst_loss_upper_per_pot"])
            <= float(a["worst_loss_upper_per_pot"]) + 1e-15
            for a, b in zip(rows, rows[1:])
        ),
    }


def aggregate_checkpoint(payload: dict, checkpoint: int) -> list[dict]:
    by_candidate: dict[str, list[dict]] = defaultdict(list)
    expected_boards = {str(r["board"]) for r in payload["rows"]}
    for row in payload["rows"]:
        if int(row["checkpoint"]) == int(checkpoint):
            by_candidate[str(row["candidate"])].append(row)

    out: list[dict] = []
    for candidate, rows in sorted(by_candidate.items()):
        boards = {str(r["board"]) for r in rows}
        if boards != expected_boards:
            raise ValueError(
                f"incomplete board coverage for {candidate}@{checkpoint}: "
                f"got={sorted(boards)} expected={sorted(expected_boards)}"
            )
        uppers = [float(r["worst_loss_upper_per_pot"]) for r in rows]
        widths = [float(r["max_value_interval_width_per_pot"]) for r in rows]
        out.append(
            {
                "candidate": candidate,
                "checkpoint": int(checkpoint),
                "boards": len(rows),
                "mean_loss_upper_per_pot": sum(uppers) / len(uppers),
                "worst_board_loss_upper_per_pot": max(uppers),
                "mean_value_interval_width_per_pot": sum(widths) / len(widths),
                "worst_value_interval_width_per_pot": max(widths),
                "total_cumulative_training_seconds": sum(
                    float(r["reference_cumulative_train_seconds"])
                    + float(r["p0_cumulative_train_seconds"])
                    + float(r["p1_cumulative_train_seconds"])
                    for r in rows
                ),
            }
        )
    return out


def _latest_checkpoint(payload: dict) -> int:
    checkpoints = {int(r["checkpoint"]) for r in payload["rows"]}
    if not checkpoints:
        raise ValueError("no convergence rows")
    return max(checkpoints)


def analyze(payload: dict) -> dict:
    if payload.get("schema") != "DEEPCASH_RIVER_REFERENCE_CONVERGENCE_V1":
        raise ValueError("unsupported reference convergence schema")

    grouped = _group_rows(payload)
    curves = [summarize_curve(rows) for _, rows in sorted(grouped.items())]
    latest = _latest_checkpoint(payload)
    latest_aggregate = aggregate_checkpoint(payload, latest)

    return {
        "schema": "DEEPCASH_RIVER_REFERENCE_CONVERGENCE_ANALYSIS_V1",
        "source_checkpoints": list(payload.get("checkpoints", [])),
        "latest_checkpoint": latest,
        "methodology_note": (
            "No arbitrary strategic acceptance threshold is applied here. "
            "The analyzer reports exact-BR interval tightening and conservative "
            "restriction-loss upper bounds; production thresholds must be "
            "precommitted later and validated on target Ryzen hardware."
        ),
        "curves": curves,
        "latest_checkpoint_aggregate": latest_aggregate,
        "all_curves_tightened_interval_vs_first": all(
            c["last_interval_width_per_pot"]
            <= c["first_interval_width_per_pot"] + 1e-15
            for c in curves
        ),
    }


def _format_float(x: float) -> str:
    return f"{float(x):.8f}"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Analyze common-reference restriction convergence without post-hoc thresholds"
    )
    ap.add_argument("input", type=Path)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("river_reference_convergence_analysis.json"),
    )
    args = ap.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyze(payload)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("Common-reference interval tightening:")
    for curve in result["curves"]:
        print(
            f"- {curve['board']} {curve['candidate']}: "
            f"iter {curve['first_checkpoint']}->{curve['last_checkpoint']} "
            f"interval {_format_float(curve['first_interval_width_per_pot'])}"
            f"->{_format_float(curve['last_interval_width_per_pot'])} "
            f"loss_upper {_format_float(curve['first_loss_upper_per_pot'])}"
            f"->{_format_float(curve['last_loss_upper_per_pot'])}"
        )
    print("Latest checkpoint aggregate:")
    for row in result["latest_checkpoint_aggregate"]:
        print(
            f"- {row['candidate']}: mean_upper={_format_float(row['mean_loss_upper_per_pot'])} "
            f"worst_upper={_format_float(row['worst_board_loss_upper_per_pot'])} "
            f"worst_interval={_format_float(row['worst_value_interval_width_per_pot'])}"
        )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
