"""Aggregate the precommitted held-out-v2 opening-size validation artifacts.

This reporter never changes the forwarded champions and never declares a
production winner. It only combines the three SPR analyses into generalization
metrics after the cardinality champions were selected without seeing v2.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXPECTED_STACKS = {100, 200, 400}
EXPECTED_CHECKPOINT = 3600
EXPECTED_RANGE_COMBOS = 8
EXPECTED_PHASES = (0.31, 0.79)


def cardinality(name: str) -> int:
    match = re.fullmatch(r"L([123])_.+", name)
    if not match:
        raise ValueError(f"unexpected champion name: {name}")
    return int(match.group(1))


def main() -> None:
    ap = argparse.ArgumentParser(description="Summarize unseen held-out-v2 opening evidence")
    ap.add_argument("input_dir", type=Path)
    ap.add_argument("--out", type=Path, default=Path("opening_heldout_v2_summary.json"))
    args = ap.parse_args()

    paths = sorted(args.input_dir.rglob("*_analysis.json"))
    if len(paths) != 3:
        raise ValueError(f"expected exactly three held-out-v2 analysis files, found {len(paths)}")

    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    stacks = set()
    expected_candidates: set[str] | None = None
    rows: dict[str, dict] = {}

    for payload in payloads:
        geometry = payload.get("source_geometry", {})
        if geometry.get("board_set") != "heldout_v2":
            raise ValueError(f"non-v2 board set in held-out summary: {geometry}")
        stack = int(geometry["stack"])
        stacks.add(stack)
        if int(geometry["range_combos"]) != EXPECTED_RANGE_COMBOS:
            raise ValueError("held-out-v2 range combo count changed")
        phases = (float(geometry["p0_phase"]), float(geometry["p1_phase"]))
        if phases != EXPECTED_PHASES:
            raise ValueError(f"held-out-v2 range phases changed: {phases}")
        if int(payload["latest_checkpoint"]) != EXPECTED_CHECKPOINT:
            raise ValueError("held-out-v2 analysis did not reach checkpoint 3600")

        candidates = {curve["candidate"] for curve in payload["curves"]}
        if len(candidates) != 3 or {cardinality(c) for c in candidates} != {1, 2, 3}:
            raise ValueError(f"held-out-v2 must contain one champion per cardinality: {sorted(candidates)}")
        if expected_candidates is None:
            expected_candidates = candidates
        elif candidates != expected_candidates:
            raise ValueError("held-out-v2 SPR jobs evaluated different champion sets")

        aggregates = {
            row["candidate"]: row for row in payload["latest_checkpoint_aggregate"]
        }
        for curve in payload["curves"]:
            candidate = str(curve["candidate"])
            item = rows.setdefault(
                candidate,
                {
                    "candidate": candidate,
                    "cardinality": cardinality(candidate),
                    "loss_uppers": [],
                    "interval_widths": [],
                    "training_seconds": 0.0,
                    "board_rows": 0,
                    "spr_rows": [],
                },
            )
            item["loss_uppers"].append(float(curve["last_loss_upper_per_pot"]))
            item["interval_widths"].append(float(curve["last_interval_width_per_pot"]))
            item["board_rows"] += 1
        for candidate, aggregate in aggregates.items():
            item = rows[candidate]
            item["training_seconds"] += float(aggregate["total_cumulative_training_seconds"])
            item["spr_rows"].append(
                {
                    "stack": stack,
                    "spr": stack / 100.0,
                    "mean_loss_upper_per_pot": float(aggregate["mean_loss_upper_per_pot"]),
                    "worst_loss_upper_per_pot": float(aggregate["worst_board_loss_upper_per_pot"]),
                    "mean_interval_width_per_pot": float(aggregate["mean_value_interval_width_per_pot"]),
                    "worst_interval_width_per_pot": float(aggregate["worst_value_interval_width_per_pot"]),
                }
            )

    if stacks != EXPECTED_STACKS:
        raise ValueError(f"held-out-v2 stacks changed: {stacks}")

    summary = []
    for candidate, item in sorted(rows.items(), key=lambda kv: kv[1]["cardinality"]):
        summary.append(
            {
                "candidate": candidate,
                "cardinality": item["cardinality"],
                "heldout_board_rows": item["board_rows"],
                "mean_loss_upper_per_pot": sum(item["loss_uppers"]) / len(item["loss_uppers"]),
                "worst_loss_upper_per_pot": max(item["loss_uppers"]),
                "mean_exact_br_interval_width_per_pot": sum(item["interval_widths"]) / len(item["interval_widths"]),
                "worst_exact_br_interval_width_per_pot": max(item["interval_widths"]),
                "total_cumulative_training_seconds": item["training_seconds"],
                "by_spr": sorted(item["spr_rows"], key=lambda row: row["stack"]),
            }
        )

    output = {
        "schema": "DEEPCASH_R3_OPENING_HELDOUT_V2_SUMMARY_V1",
        "precommit": "docs/R3_HELDOUT_V2_PRECOMMIT_20260816.md",
        "checkpoint": EXPECTED_CHECKPOINT,
        "range_combos": EXPECTED_RANGE_COMBOS,
        "range_phases": list(EXPECTED_PHASES),
        "sprs": [1.0, 2.0, 4.0],
        "summary": summary,
        "interpretation_note": (
            "This artifact reports unseen-v2 generalization only. It does not "
            "freeze an action family; target-Ryzen equal-compute evidence remains required."
        ),
    }
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("Held-out-v2 opening-size generalization:")
    for row in summary:
        print(
            f"- {row['candidate']}: mean_upper={row['mean_loss_upper_per_pot']:.8f} "
            f"worst_upper={row['worst_loss_upper_per_pot']:.8f} "
            f"worst_interval={row['worst_exact_br_interval_width_per_pot']:.8f}"
        )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
