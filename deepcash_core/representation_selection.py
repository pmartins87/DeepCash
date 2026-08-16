from __future__ import annotations

import math
from collections import defaultdict
from statistics import fmean
from typing import Iterable, Mapping, Sequence


_REQUIRED_ROW_FIELDS = (
    "candidate",
    "checkpoint",
    "worst_loss_upper_per_pot",
    "max_value_interval_width_per_pot",
    "bucket_compression_ratio",
    "joint_infosets",
    "reference_infosets",
    "joint_action_slots",
    "reference_action_slots",
    "joint_cumulative_train_seconds",
)


def _nearest_rank(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("cannot take quantile of empty values")
    if not 0.0 < q <= 1.0:
        raise ValueError("q must be in (0, 1]")
    ordered = sorted(float(v) for v in values)
    index = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return ordered[index]


def _validate_row(row: Mapping[str, object]) -> None:
    missing = [key for key in _REQUIRED_ROW_FIELDS if key not in row]
    if missing:
        raise ValueError(f"representation row missing fields: {missing}")
    if float(row["reference_infosets"]) <= 0:
        raise ValueError("reference_infosets must be positive")
    if float(row["reference_action_slots"]) <= 0:
        raise ValueError("reference_action_slots must be positive")


def largest_shared_checkpoint(payloads: Sequence[Mapping[str, object]]) -> int:
    """Largest checkpoint present for every candidate in every supplied cell."""
    if not payloads:
        raise ValueError("at least one development payload is required")

    shared: set[int] | None = None
    canonical_candidates: set[str] | None = None
    for payload in payloads:
        rows = list(payload.get("rows", []))
        if not rows:
            raise ValueError("development payload contains no rows")
        by_candidate: dict[str, set[int]] = defaultdict(set)
        for raw in rows:
            row = dict(raw)
            _validate_row(row)
            by_candidate[str(row["candidate"])].add(int(row["checkpoint"]))
        candidates = set(by_candidate)
        if canonical_candidates is None:
            canonical_candidates = candidates
        elif candidates != canonical_candidates:
            raise ValueError("candidate set differs across development payloads")
        payload_shared = set.intersection(*(by_candidate[c] for c in sorted(candidates)))
        if not payload_shared:
            raise ValueError("no checkpoint is shared by every candidate in a payload")
        shared = payload_shared if shared is None else shared & payload_shared
    if not shared:
        raise ValueError("no checkpoint is shared by every candidate in every payload")
    return max(shared)


def aggregate_candidate_metrics(
    payloads: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    checkpoint = largest_shared_checkpoint(payloads)
    rows_by_candidate: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    cell_count = 0

    for payload in payloads:
        cell_rows = [
            row
            for row in payload["rows"]
            if int(row["checkpoint"]) == checkpoint
        ]
        seen: set[str] = set()
        for row in cell_rows:
            _validate_row(row)
            candidate = str(row["candidate"])
            if candidate in seen:
                raise ValueError(
                    "payload contains duplicate candidate row at shared checkpoint"
                )
            seen.add(candidate)
            rows_by_candidate[candidate].append(row)
        cell_count += 1

    if not rows_by_candidate:
        raise ValueError("no rows at shared checkpoint")
    expected = set(rows_by_candidate)
    for candidate, rows in rows_by_candidate.items():
        if len(rows) != cell_count:
            raise ValueError(
                f"candidate {candidate} missing from one or more development cells"
            )
    if any(set(str(r["candidate"]) for r in [row for row in payload["rows"] if int(row["checkpoint"]) == checkpoint]) != expected for payload in payloads):
        raise ValueError("candidate set mismatch at shared checkpoint")

    metrics: dict[str, dict[str, float | int | str]] = {}
    for candidate, rows in sorted(rows_by_candidate.items()):
        uppers = [float(r["worst_loss_upper_per_pot"]) for r in rows]
        intervals = [float(r["max_value_interval_width_per_pot"]) for r in rows]
        compression = [float(r["bucket_compression_ratio"]) for r in rows]
        infoset_ratios = [
            float(r["joint_infosets"]) / float(r["reference_infosets"])
            for r in rows
        ]
        action_ratios = [
            float(r["joint_action_slots"]) / float(r["reference_action_slots"])
            for r in rows
        ]
        train_seconds = [float(r["joint_cumulative_train_seconds"]) for r in rows]
        metrics[candidate] = {
            "candidate": candidate,
            "cells": len(rows),
            "checkpoint": checkpoint,
            "worst_upper": max(uppers),
            "mean_upper": fmean(uppers),
            "p90_upper": _nearest_rank(uppers, 0.90),
            "worst_interval": max(intervals),
            "mean_compression": fmean(compression),
            "mean_joint_infoset_ratio": fmean(infoset_ratios),
            "mean_joint_action_slot_ratio": fmean(action_ratios),
            "mean_joint_train_seconds": fmean(train_seconds),
        }

    frontier = pareto_frontier(metrics)
    return {
        "schema": "DEEPCASH_R4_DEV_SELECTION_SUMMARY_V1",
        "shared_checkpoint": checkpoint,
        "development_payloads": len(payloads),
        "candidate_count": len(metrics),
        "metrics": metrics,
        "pareto_frontier": frontier,
        "selection_rule": "docs/R4_DEV_SELECTION_PRECOMMIT_20260816.md",
        "note": (
            "Pareto frontier is mechanical. If more than three candidates remain, "
            "apply the precommitted unresolved-interval complexity preference after "
            "inspecting convergence; do not invent a post-hoc scalar score."
        ),
    }


def _dominates(a: Mapping[str, object], b: Mapping[str, object]) -> bool:
    fields = (
        "worst_upper",
        "mean_upper",
        "mean_joint_action_slot_ratio",
        "mean_compression",
    )
    a_vals = [float(a[key]) for key in fields]
    b_vals = [float(b[key]) for key in fields]
    return all(x <= y for x, y in zip(a_vals, b_vals)) and any(
        x < y for x, y in zip(a_vals, b_vals)
    )


def pareto_frontier(metrics: Mapping[str, Mapping[str, object]]) -> list[str]:
    names = sorted(metrics)
    out = []
    for candidate in names:
        if any(
            other != candidate and _dominates(metrics[other], metrics[candidate])
            for other in names
        ):
            continue
        out.append(candidate)
    return out
