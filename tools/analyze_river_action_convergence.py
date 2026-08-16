from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def dominates(a: dict, b: dict) -> bool:
    """Pareto dominance on training cost + mean/worst exact exploitability."""
    weak = (
        a["training_seconds"] <= b["training_seconds"]
        and a["mean_exploitability_per_pot"] <= b["mean_exploitability_per_pot"]
        and a["worst_exploitability_per_pot"] <= b["worst_exploitability_per_pot"]
    )
    strict = (
        a["training_seconds"] < b["training_seconds"]
        or a["mean_exploitability_per_pot"] < b["mean_exploitability_per_pot"]
        or a["worst_exploitability_per_pot"] < b["worst_exploitability_per_pot"]
    )
    return weak and strict


def aggregate(payload: dict) -> list[dict]:
    by_key: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in payload["rows"]:
        by_key[(row["candidate"], int(row["checkpoint"]))].append(row)

    out = []
    for (candidate, checkpoint), rows in sorted(by_key.items()):
        expected_boards = {r["board"] for r in payload["rows"]}
        boards = {r["board"] for r in rows}
        if boards != expected_boards:
            raise ValueError(f"incomplete board coverage for {candidate}@{checkpoint}")
        errors = [float(r["exploitability_per_pot"]) for r in rows]
        # A complete battery is conceptually sequential work here; physical
        # parallelism will be calibrated later on the Ryzen and must not be
        # smuggled into this engineering metric.
        training_seconds = sum(float(r["cumulative_training_seconds"]) for r in rows)
        evaluation_seconds = sum(float(r["evaluation_seconds"]) for r in rows)
        out.append(
            {
                "candidate": candidate,
                "checkpoint": checkpoint,
                "boards": len(rows),
                "training_seconds": training_seconds,
                "evaluation_seconds": evaluation_seconds,
                "mean_exploitability_per_pot": sum(errors) / len(errors),
                "worst_exploitability_per_pot": max(errors),
                "best_exploitability_per_pot": min(errors),
                "infosets_per_board": int(rows[0]["infosets"]),
                "action_slots_per_board": int(rows[0]["action_slots"]),
            }
        )
    return out


def pareto_frontier(rows: list[dict]) -> list[dict]:
    frontier = []
    for row in rows:
        if not any(dominates(other, row) for other in rows if other is not row):
            frontier.append(row)
    return sorted(frontier, key=lambda r: (r["training_seconds"], r["mean_exploitability_per_pot"]))


def equal_budget_snapshots(rows: list[dict], budgets: list[float]) -> list[dict]:
    by_candidate: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_candidate[row["candidate"]].append(row)
    for values in by_candidate.values():
        values.sort(key=lambda r: r["training_seconds"])

    out = []
    for budget in budgets:
        for candidate, values in sorted(by_candidate.items()):
            eligible = [r for r in values if r["training_seconds"] <= budget]
            if not eligible:
                continue
            chosen = eligible[-1]
            out.append(
                {
                    "budget_seconds": budget,
                    "candidate": candidate,
                    "checkpoint": chosen["checkpoint"],
                    "training_seconds": chosen["training_seconds"],
                    "mean_exploitability_per_pot": chosen["mean_exploitability_per_pot"],
                    "worst_exploitability_per_pot": chosen["worst_exploitability_per_pot"],
                }
            )
    return out


def default_budgets(rows: list[dict]) -> list[float]:
    by_candidate: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_candidate[row["candidate"]].append(float(row["training_seconds"]))
    # Only budgets at which every candidate has at least one checkpoint are
    # useful for equal-compute comparison. Use observed cost landmarks rather
    # than inventing hardware-independent seconds.
    floor_cost = max(min(v) for v in by_candidate.values())
    ceiling = min(max(v) for v in by_candidate.values())
    candidates = sorted({float(r["training_seconds"]) for r in rows if floor_cost <= float(r["training_seconds"]) <= ceiling})
    if len(candidates) <= 6:
        return candidates
    idxs = {0, len(candidates) - 1}
    idxs.update(round(i * (len(candidates) - 1) / 5) for i in range(1, 5))
    return [candidates[i] for i in sorted(idxs)]


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze DeepCash river action convergence evidence")
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, default=Path("river_action_convergence_analysis.json"))
    ap.add_argument("--budgets", default="", help="optional comma-separated training-second budgets")
    args = ap.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if payload.get("schema") != "DEEPCASH_RIVER_ACTION_CONVERGENCE_V1":
        raise SystemExit("unsupported convergence schema")

    aggregated = aggregate(payload)
    frontier = pareto_frontier(aggregated)
    budgets = (
        [float(x) for x in args.budgets.split(",") if x.strip()]
        if args.budgets
        else default_budgets(aggregated)
    )
    equal_budget = equal_budget_snapshots(aggregated, budgets)

    result = {
        "schema": "DEEPCASH_RIVER_ACTION_CONVERGENCE_ANALYSIS_V1",
        "source": str(args.input),
        "timing_warning": "wall-clock values are machine-specific; CI results are engineering evidence, not Ryzen selection evidence",
        "aggregated": aggregated,
        "pareto_frontier": frontier,
        "equal_budget_snapshots": equal_budget,
    }
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("Pareto frontier (training cost / mean error / worst error):")
    for row in frontier:
        print(
            f"- {row['candidate']} iter={row['checkpoint']} "
            f"train_s={row['training_seconds']:.4f} "
            f"mean={row['mean_exploitability_per_pot']:.6f} "
            f"worst={row['worst_exploitability_per_pot']:.6f}"
        )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
