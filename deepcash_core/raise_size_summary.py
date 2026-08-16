from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable, Mapping


EXPECTED_CANDIDATES = (
    "Q1_100",
    "Q2_50_100",
    "Q2_100_150",
    "Q3_50_100_150",
)
EXPECTED_ANALYSIS_SCHEMA = "DEEPCASH_RIVER_RAISE_REFERENCE_CONVERGENCE_ANALYSIS_V1"
SUMMARY_SCHEMA = "DEEPCASH_R3_RAISE_SIZE_HELDOUT_SUMMARY_V1"


@dataclass(frozen=True)
class CellMetric:
    candidate: str
    mean_loss_upper_per_pot: float
    worst_board_loss_upper_per_pot: float
    mean_value_interval_width_per_pot: float
    worst_value_interval_width_per_pot: float
    total_cumulative_training_seconds: float

    @property
    def mean_resolved_excess_per_pot(self) -> float:
        return max(
            0.0,
            self.mean_loss_upper_per_pot - self.mean_value_interval_width_per_pot,
        )

    @property
    def worst_resolved_excess_per_pot(self) -> float:
        return max(
            0.0,
            self.worst_board_loss_upper_per_pot
            - self.worst_value_interval_width_per_pot,
        )

    def to_dict(self) -> dict[str, float | str]:
        return {
            "candidate": self.candidate,
            "mean_loss_upper_per_pot": self.mean_loss_upper_per_pot,
            "worst_board_loss_upper_per_pot": self.worst_board_loss_upper_per_pot,
            "mean_value_interval_width_per_pot": self.mean_value_interval_width_per_pot,
            "worst_value_interval_width_per_pot": self.worst_value_interval_width_per_pot,
            "mean_resolved_excess_per_pot": self.mean_resolved_excess_per_pot,
            "worst_resolved_excess_per_pot": self.worst_resolved_excess_per_pot,
            "total_cumulative_training_seconds": self.total_cumulative_training_seconds,
        }


def _finite_nonnegative(value: object, field: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(out) or out < 0.0:
        raise ValueError(f"{field} must be finite and non-negative")
    return out


def _candidate_rows(payload: Mapping[str, object]) -> tuple[CellMetric, ...]:
    rows = payload.get("latest_checkpoint_aggregate")
    if not isinstance(rows, list) or not rows:
        raise ValueError("analysis is missing latest_checkpoint_aggregate rows")

    by_name: dict[str, CellMetric] = {}
    checkpoint = payload.get("latest_checkpoint")
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("aggregate row must be an object")
        candidate = str(row.get("candidate", ""))
        if candidate in by_name:
            raise ValueError(f"duplicate candidate row: {candidate}")
        row_checkpoint = row.get("checkpoint")
        if checkpoint is not None and row_checkpoint != checkpoint:
            raise ValueError("aggregate row checkpoint differs from latest_checkpoint")
        by_name[candidate] = CellMetric(
            candidate=candidate,
            mean_loss_upper_per_pot=_finite_nonnegative(
                row.get("mean_loss_upper_per_pot"), "mean_loss_upper_per_pot"
            ),
            worst_board_loss_upper_per_pot=_finite_nonnegative(
                row.get("worst_board_loss_upper_per_pot"),
                "worst_board_loss_upper_per_pot",
            ),
            mean_value_interval_width_per_pot=_finite_nonnegative(
                row.get("mean_value_interval_width_per_pot"),
                "mean_value_interval_width_per_pot",
            ),
            worst_value_interval_width_per_pot=_finite_nonnegative(
                row.get("worst_value_interval_width_per_pot"),
                "worst_value_interval_width_per_pot",
            ),
            total_cumulative_training_seconds=_finite_nonnegative(
                row.get("total_cumulative_training_seconds"),
                "total_cumulative_training_seconds",
            ),
        )

    if set(by_name) != set(EXPECTED_CANDIDATES):
        raise ValueError(
            "candidate set mismatch: "
            f"expected={sorted(EXPECTED_CANDIDATES)} got={sorted(by_name)}"
        )
    return tuple(by_name[name] for name in EXPECTED_CANDIDATES)


def _load_analysis(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: analysis root must be an object")
    if payload.get("schema") != EXPECTED_ANALYSIS_SCHEMA:
        raise ValueError(f"{path}: unexpected analysis schema {payload.get('schema')!r}")
    geometry = payload.get("source_geometry")
    if not isinstance(geometry, Mapping):
        raise ValueError(f"{path}: missing source_geometry")
    if geometry.get("restriction_dimension") != "raise_size":
        raise ValueError(f"{path}: not a raise-size restriction analysis")
    _candidate_rows(payload)
    return payload


def discover_analyses(root: str | Path) -> tuple[tuple[Path, dict[str, object]], ...]:
    root_path = Path(root)
    paths = sorted(root_path.rglob("river_raise_size_heldout_*_analysis.json"))
    if not paths:
        raise ValueError(f"no raise-size heldout analysis files found under {root_path}")
    loaded = tuple((path, _load_analysis(path)) for path in paths)

    seen_sprs: dict[float, Path] = {}
    for path, payload in loaded:
        geometry = payload["source_geometry"]
        assert isinstance(geometry, Mapping)
        spr = float(geometry["spr"])
        if spr in seen_sprs:
            raise ValueError(
                f"duplicate SPR {spr}: {seen_sprs[spr]} and {path}"
            )
        seen_sprs[spr] = path
    return loaded


def _dominates(a: Mapping[str, float], b: Mapping[str, float], *, eps: float = 1e-15) -> bool:
    objectives = (
        "mean_loss_upper_per_pot",
        "worst_board_loss_upper_per_pot",
        "total_cumulative_training_seconds",
    )
    no_worse = all(a[key] <= b[key] + eps for key in objectives)
    strictly_better = any(a[key] < b[key] - eps for key in objectives)
    return no_worse and strictly_better


def summarize_payloads(
    loaded: Iterable[tuple[Path, Mapping[str, object]]],
    *,
    required_sprs: Iterable[float] | None = None,
) -> dict[str, object]:
    cells: list[dict[str, object]] = []
    candidate_acc: dict[str, list[CellMetric]] = {
        name: [] for name in EXPECTED_CANDIDATES
    }
    seen_sprs: set[float] = set()

    for path, payload in loaded:
        geometry = payload["source_geometry"]
        assert isinstance(geometry, Mapping)
        spr = float(geometry["spr"])
        if spr in seen_sprs:
            raise ValueError(f"duplicate SPR {spr} in summary input")
        seen_sprs.add(spr)
        metrics = _candidate_rows(payload)
        for metric in metrics:
            candidate_acc[metric.candidate].append(metric)
        cells.append(
            {
                "source": str(path),
                "spr": spr,
                "stack": int(geometry["stack"]),
                "pot": int(geometry["pot"]),
                "range_combos": int(geometry["range_combos"]),
                "p0_phase": float(geometry["p0_phase"]),
                "p1_phase": float(geometry["p1_phase"]),
                "latest_checkpoint": int(payload["latest_checkpoint"]),
                "candidates": [metric.to_dict() for metric in metrics],
            }
        )

    if required_sprs is not None:
        required = {float(v) for v in required_sprs}
        if seen_sprs != required:
            raise ValueError(
                f"SPR set mismatch: expected={sorted(required)} got={sorted(seen_sprs)}"
            )

    cells.sort(key=lambda row: float(row["spr"]))
    candidate_summary: list[dict[str, object]] = []
    for name in EXPECTED_CANDIDATES:
        rows = candidate_acc[name]
        if len(rows) != len(cells):
            raise ValueError(f"candidate {name} missing from one or more cells")
        candidate_summary.append(
            {
                "candidate": name,
                "cells": len(rows),
                "mean_loss_upper_per_pot": mean(
                    row.mean_loss_upper_per_pot for row in rows
                ),
                "worst_board_loss_upper_per_pot": max(
                    row.worst_board_loss_upper_per_pot for row in rows
                ),
                "max_mean_resolved_excess_per_pot": max(
                    row.mean_resolved_excess_per_pot for row in rows
                ),
                "max_worst_resolved_excess_per_pot": max(
                    row.worst_resolved_excess_per_pot for row in rows
                ),
                "resolution_limited_cells": sum(
                    row.worst_resolved_excess_per_pot <= 1e-15 for row in rows
                ),
                "total_cumulative_training_seconds": sum(
                    row.total_cumulative_training_seconds for row in rows
                ),
            }
        )

    numeric = {
        row["candidate"]: {
            "mean_loss_upper_per_pot": float(row["mean_loss_upper_per_pot"]),
            "worst_board_loss_upper_per_pot": float(
                row["worst_board_loss_upper_per_pot"]
            ),
            "total_cumulative_training_seconds": float(
                row["total_cumulative_training_seconds"]
            ),
        }
        for row in candidate_summary
    }
    pareto = []
    dominated_by: dict[str, list[str]] = {}
    for name in EXPECTED_CANDIDATES:
        dominators = [
            other
            for other in EXPECTED_CANDIDATES
            if other != name and _dominates(numeric[other], numeric[name])
        ]
        dominated_by[name] = sorted(dominators)
        if not dominators:
            pareto.append(name)

    for row in candidate_summary:
        name = str(row["candidate"])
        row["dominated_by"] = dominated_by[name]
        row["pareto"] = name in pareto

    return {
        "schema": SUMMARY_SCHEMA,
        "methodology_note": (
            "This summary applies no post-hoc strategic acceptance threshold. "
            "It aggregates the precommitted held-out cells, reports conservative "
            "restriction-loss upper bounds and exact-BR interval resolution, and "
            "computes a descriptive Pareto frontier over mean upper loss, worst "
            "upper loss and measured CI training seconds. Production selection "
            "still requires target-Ryzen equal-compute evidence."
        ),
        "sprs": sorted(seen_sprs),
        "cells": cells,
        "candidate_summary": candidate_summary,
        "descriptive_pareto_front": pareto,
    }


def summarize_directory(
    root: str | Path,
    *,
    required_sprs: Iterable[float] | None = None,
) -> dict[str, object]:
    return summarize_payloads(discover_analyses(root), required_sprs=required_sprs)
