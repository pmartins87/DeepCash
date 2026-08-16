from __future__ import annotations

import argparse
import json
from pathlib import Path

from deepcash_core.raise_size_summary import summarize_directory


def _parse_sprs(text: str) -> tuple[float, ...]:
    vals = tuple(float(v.strip()) for v in text.split(",") if v.strip())
    if not vals:
        raise argparse.ArgumentTypeError("at least one SPR is required")
    return vals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="directory containing held-out analysis JSON files")
    parser.add_argument("--out", required=True)
    parser.add_argument("--require-sprs", type=_parse_sprs, default=None)
    args = parser.parse_args()

    summary = summarize_directory(args.root, required_sprs=args.require_sprs)
    out = Path(args.out)
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"R3 raise-size heldout summary PASS: sprs={summary['sprs']}")
    print(f"descriptive Pareto front={summary['descriptive_pareto_front']}")
    for row in summary["candidate_summary"]:
        print(
            f"{row['candidate']}: mean_upper={row['mean_loss_upper_per_pot']:.8f} "
            f"worst_upper={row['worst_board_loss_upper_per_pot']:.8f} "
            f"max_resolved_excess={row['max_worst_resolved_excess_per_pot']:.8f} "
            f"seconds={row['total_cumulative_training_seconds']:.2f} "
            f"pareto={row['pareto']}"
        )


if __name__ == "__main__":
    main()
