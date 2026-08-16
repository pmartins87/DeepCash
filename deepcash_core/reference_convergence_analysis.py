from __future__ import annotations

from collections import defaultdict

_SUPPORTED_SCHEMAS = {
    "DEEPCASH_RIVER_REFERENCE_CONVERGENCE_V1": "DEEPCASH_RIVER_REFERENCE_CONVERGENCE_ANALYSIS_V1",
    "DEEPCASH_RIVER_RAISE_REFERENCE_CONVERGENCE_V1": "DEEPCASH_RIVER_RAISE_REFERENCE_CONVERGENCE_ANALYSIS_V1",
}


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
            row["max_value_interval_width_per_pot"],
            name="max_value_interval_width_per_pot",
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


def _source_geometry(payload: dict) -> dict:
    """Carry stable experiment coordinates into the analysis artifact.

    Keeping geometry here lets separate matrix jobs be aggregated later without
    reopening or reparsing their larger raw convergence files. Missing fields
    remain absent so older payloads stay backward compatible.
    """
    geometry = {}
    for key in (
        "pot",
        "stack",
        "spr",
        "range_combos",
        "restriction_dimension",
        "board_set",
        "p0_phase",
        "p1_phase",
    ):
        if key in payload:
            geometry[key] = payload[key]
    return geometry


def analyze(payload: dict) -> dict:
    source_schema = payload.get("schema")
    if source_schema not in _SUPPORTED_SCHEMAS:
        raise ValueError("unsupported reference convergence schema")

    grouped = _group_rows(payload)
    curves = [summarize_curve(rows) for _, rows in sorted(grouped.items())]
    latest = _latest_checkpoint(payload)
    latest_aggregate = aggregate_checkpoint(payload, latest)

    return {
        "schema": _SUPPORTED_SCHEMAS[source_schema],
        "source_schema": source_schema,
        "source_checkpoints": list(payload.get("checkpoints", [])),
        "source_geometry": _source_geometry(payload),
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
