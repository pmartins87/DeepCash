from __future__ import annotations

import argparse
import json
from pathlib import Path

from deepcash_core.representation_selection import aggregate_candidate_metrics


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Summarize R4 development representation cells under the frozen Pareto rule"
    )
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=Path("r4_dev_summary.json"))
    args = ap.parse_args()

    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in args.inputs]
    summary = aggregate_candidate_metrics(payloads)
    summary["input_files"] = [str(path) for path in args.inputs]
    args.out.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"shared_checkpoint={summary['shared_checkpoint']}")
    print(f"development_payloads={summary['development_payloads']}")
    for name in sorted(summary["metrics"]):
        row = summary["metrics"][name]
        mark = "*" if name in summary["pareto_frontier"] else " "
        print(
            f"{mark} {name:22s} "
            f"worst={row['worst_upper']:.6f} mean={row['mean_upper']:.6f} "
            f"p90={row['p90_upper']:.6f} interval={row['worst_interval']:.6f} "
            f"compression={row['mean_compression']:.3f} "
            f"slots={row['mean_joint_action_slot_ratio']:.3f} "
            f"seconds={row['mean_joint_train_seconds']:.3f}"
        )
    print("pareto_frontier=" + ",".join(summary["pareto_frontier"]))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
