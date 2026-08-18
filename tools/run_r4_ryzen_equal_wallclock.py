from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from deepcash_core.r4_representation_gen2_freeze import load_generation2_finalist_freeze
from deepcash_core.river_benchmark_fixtures import parse_cards, quantile_range, restriction_loss_bounds
from deepcash_core.river_lab import RiverGameSpec, materialize_bet_sizes
from deepcash_core.river_representation_gen2 import (
    GEN2_REFERENCE_FRACTIONS,
    gen2_candidate_bucket_maps,
)
from deepcash_core.river_representation_gen2_fixtures import gen2_board_registry
from deepcash_core.river_representation_lab import exact_bucket_maps, one_sided_bucket_maps
from deepcash_core.river_representation_training import (
    advance_representation_cfr_plus,
    init_representation_cfr_plus,
    representation_result_from_state,
    state_to_dict,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "deepcash_core" / "data" / "r4_ryzen_equal_wallclock_v1.json"
FINALIST_FREEZE = ROOT / "deepcash_core" / "data" / "r4_representation_generation2_finalists_v1.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_git(*args: str) -> str:
    try:
        cp = subprocess.run(
            ["git", *args], cwd=ROOT, text=True, capture_output=True, check=True
        )
        return cp.stdout.strip()
    except Exception:
        return ""


def process_affinity() -> list[int] | None:
    if hasattr(os, "sched_getaffinity"):
        try:
            return sorted(int(x) for x in os.sched_getaffinity(0))
        except Exception:
            pass
    if os.name == "nt":
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            process = kernel32.GetCurrentProcess()
            process_mask = ctypes.c_size_t()
            system_mask = ctypes.c_size_t()
            ok = kernel32.GetProcessAffinityMask(
                process, ctypes.byref(process_mask), ctypes.byref(system_mask)
            )
            if ok:
                mask = int(process_mask.value)
                return [i for i in range(mask.bit_length()) if mask & (1 << i)]
        except Exception:
            pass
    return None


def peak_rss_bytes() -> int | None:
    if os.name == "nt":
        try:
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.c_uint32),
                    ("PageFaultCount", ctypes.c_uint32),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(counters)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            ok = psapi.GetProcessMemoryInfo(
                kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
            )
            if ok:
                return int(counters.PeakWorkingSetSize)
        except Exception:
            return None
    try:
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return value if sys.platform == "darwin" else value * 1024
    except Exception:
        return None


def load_average() -> list[float] | None:
    try:
        return [float(x) for x in os.getloadavg()]
    except Exception:
        return None


def machine_metadata() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "processor_identifier": os.environ.get("PROCESSOR_IDENTIFIER", ""),
        "python": sys.version,
        "logical_cpu_count": os.cpu_count(),
        "affinity": process_affinity(),
        "load_average": load_average(),
        "git_head": run_git("rev-parse", "HEAD"),
        "git_status_porcelain": run_git("status", "--porcelain"),
    }


def build_spec(
    *, board_text: str, p0_phase: float, p1_phase: float, range_combos: int,
    pot: int, stack: int, min_bet: int,
) -> RiverGameSpec:
    board = parse_cards(board_text)
    p0_range = quantile_range(board, range_combos, p0_phase)
    p1_range = quantile_range(board, range_combos, p1_phase)
    bet_sizes = materialize_bet_sizes(
        pot=pot,
        stack=stack,
        min_bet=min_bet,
        fractions=GEN2_REFERENCE_FRACTIONS,
    )
    return RiverGameSpec(board, p0_range, p1_range, pot, bet_sizes)


def train_exact_reference(spec: RiverGameSpec, iterations: int) -> dict[str, Any]:
    maps = exact_bucket_maps(spec)
    state = init_representation_cfr_plus(spec, maps)
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    advance_representation_cfr_plus(spec, maps, state, additional_iterations=iterations)
    train_wall = time.perf_counter() - started_wall
    train_cpu = time.process_time() - started_cpu
    result = representation_result_from_state(spec, maps, state)
    return {
        "iterations": result.iterations,
        "br0_value": result.br0_value,
        "br1_value": result.br1_value,
        "policy_ev": result.policy_ev,
        "exploitability": result.exploitability,
        "exploitability_per_pot": result.exploitability_per_pot,
        "infosets": result.infosets,
        "action_slots": result.action_slots,
        "train_wall_seconds": train_wall,
        "train_cpu_seconds": train_cpu,
    }


def write_checkpoint(path: Path, state_payload: dict[str, Any]) -> dict[str, Any]:
    encoded = (json.dumps(state_payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    started = time.perf_counter()
    path.write_bytes(encoded)
    write_seconds = time.perf_counter() - started
    started = time.perf_counter()
    reread = path.read_bytes()
    read_seconds = time.perf_counter() - started
    if reread != encoded:
        raise RuntimeError("checkpoint readback mismatch")
    size = len(encoded)
    return {
        "checkpoint_file": path.name,
        "checkpoint_bytes": size,
        "checkpoint_sha256": sha256_bytes(encoded),
        "checkpoint_write_seconds": write_seconds,
        "checkpoint_read_seconds": read_seconds,
        "checkpoint_write_mib_s": (size / 1048576.0) / max(write_seconds, 1e-12),
        "checkpoint_read_mib_s": (size / 1048576.0) / max(read_seconds, 1e-12),
    }


def worker_run(payload: dict[str, Any], output_path: Path) -> None:
    spec = build_spec(
        board_text=payload["board_text"],
        p0_phase=float(payload["p0_phase"]),
        p1_phase=float(payload["p1_phase"]),
        range_combos=int(payload["range_combos"]),
        pot=int(payload["pot"]),
        stack=int(payload["stack"]),
        min_bet=int(payload["min_bet"]),
    )
    candidate_name = str(payload["candidate"])
    candidate = gen2_candidate_bucket_maps(spec, candidate_name)
    p0_maps = one_sided_bucket_maps(spec, candidate, 0)
    p1_maps = one_sided_bucket_maps(spec, candidate, 1)
    p0_state = init_representation_cfr_plus(spec, p0_maps)
    p1_state = init_representation_cfr_plus(spec, p1_maps)
    joint_state = init_representation_cfr_plus(spec, candidate)

    budget = float(payload["budget_seconds"])
    chunk = int(payload["chunk_iterations"])
    if budget <= 0.0 or chunk <= 0:
        raise ValueError("budget and chunk must be positive")

    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    cycles = 0
    while True:
        advance_representation_cfr_plus(spec, p0_maps, p0_state, additional_iterations=chunk)
        advance_representation_cfr_plus(spec, p1_maps, p1_state, additional_iterations=chunk)
        advance_representation_cfr_plus(spec, candidate, joint_state, additional_iterations=chunk)
        cycles += 1
        if time.perf_counter() - started_wall >= budget:
            break
    train_wall = time.perf_counter() - started_wall
    train_cpu = time.process_time() - started_cpu

    eval_started = time.perf_counter()
    p0_result = representation_result_from_state(spec, p0_maps, p0_state)
    p1_result = representation_result_from_state(spec, p1_maps, p1_state)
    joint_result = representation_result_from_state(spec, candidate, joint_state)
    eval_wall = time.perf_counter() - eval_started

    ref = SimpleNamespace(
        br0_value=float(payload["reference"]["br0_value"]),
        br1_value=float(payload["reference"]["br1_value"]),
    )
    bounds = restriction_loss_bounds(ref, p0_result, p1_result, int(payload["pot"]))
    interval_width = max(
        ref.br0_value - ref.br1_value,
        p0_result.br0_value - p0_result.br1_value,
        p1_result.br0_value - p1_result.br1_value,
    ) / float(payload["pot"])

    exact_buckets = len(spec.p0_range) + len(spec.p1_range)
    materialized_buckets = candidate.p0_bucket_count + candidate.p1_bucket_count
    checkpoint_path = output_path.with_suffix(".checkpoint.json")
    checkpoint = write_checkpoint(checkpoint_path, state_to_dict(joint_state))

    result = {
        "schema": "DEEPCASH_R4_RYZEN_EQUAL_WALLCLOCK_CELL_V1",
        "cell_index": int(payload["cell_index"]),
        "phase": payload["phase"],
        "board": payload["board"],
        "candidate": candidate_name,
        "p0_phase": float(payload["p0_phase"]),
        "p1_phase": float(payload["p1_phase"]),
        "pot": int(payload["pot"]),
        "stack": int(payload["stack"]),
        "spr": float(payload["stack"]) / float(payload["pot"]),
        "bet_sizes": list(spec.bet_sizes),
        "range_combos_per_player": int(payload["range_combos"]),
        "budget_seconds": budget,
        "chunk_iterations": chunk,
        "cycles": cycles,
        "iterations_each_state": int(joint_state.iterations),
        "train_wall_seconds": train_wall,
        "train_cpu_seconds": train_cpu,
        "budget_overshoot_seconds": train_wall - budget,
        "joint_iterations_per_second": joint_state.iterations / max(train_wall, 1e-12),
        "p0_buckets": candidate.p0_bucket_count,
        "p1_buckets": candidate.p1_bucket_count,
        "bucket_compression_ratio": materialized_buckets / exact_buckets,
        "reference_infosets": int(payload["reference"]["infosets"]),
        "reference_action_slots": int(payload["reference"]["action_slots"]),
        "joint_infosets": joint_result.infosets,
        "joint_action_slots": joint_result.action_slots,
        "joint_action_slot_ratio": joint_result.action_slots / float(payload["reference"]["action_slots"]),
        "joint_exploitability_per_pot": joint_result.exploitability_per_pot,
        "max_value_interval_width_per_pot": interval_width,
        "evaluation_wall_seconds": eval_wall,
        "peak_rss_bytes": peak_rss_bytes(),
        "affinity": process_affinity(),
        "load_average_at_end": load_average(),
        "reference": payload["reference"],
        **bounds,
        **checkpoint,
    }
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate": candidate_name,
        "board": payload["board"],
        "phase": payload["phase"],
        "spr": result["spr"],
        "iterations": result["iterations_each_state"],
        "train_wall_seconds": round(train_wall, 6),
        "worst_loss_upper_per_pot": result["worst_loss_upper_per_pot"],
        "peak_rss_bytes": result["peak_rss_bytes"],
    }, sort_keys=True))


def percentile(values: list[float], q: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    if lo == hi:
        return ordered[lo]
    frac = position - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def summarize(rows: list[dict[str, Any]], candidates: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for candidate in candidates:
        selected = [r for r in rows if r["candidate"] == candidate]
        losses = [float(r["worst_loss_upper_per_pot"]) for r in selected]
        iterations = [int(r["iterations_each_state"]) for r in selected]
        throughput = [float(r["joint_iterations_per_second"]) for r in selected]
        rss = [int(r["peak_rss_bytes"]) for r in selected if r.get("peak_rss_bytes") is not None]
        slots = [float(r["joint_action_slot_ratio"]) for r in selected]
        out[candidate] = {
            "cells": len(selected),
            "worst_loss_upper_per_pot": max(losses),
            "mean_loss_upper_per_pot": statistics.fmean(losses),
            "p90_loss_upper_per_pot": percentile(losses, 0.90),
            "median_iterations_each_state": statistics.median(iterations),
            "mean_joint_iterations_per_second": statistics.fmean(throughput),
            "mean_action_slot_ratio": statistics.fmean(slots),
            "peak_rss_bytes_max": max(rss) if rss else None,
            "peak_rss_bytes_mean": statistics.fmean(rss) if rss else None,
        }
    return out


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != "DEEPCASH_R4_RYZEN_EQUAL_WALLCLOCK_V1":
        raise ValueError("unexpected physical config schema")
    expected = ["matchup_cluster8", "equity8", "matchup_cluster4"]
    if config.get("candidates") != expected:
        raise ValueError("physical candidate freeze drift")
    if config.get("board_set") != "heldout_v2":
        raise ValueError("physical board set drift")
    if config.get("spr_to_stack") != {"1": 100, "2": 200, "4": 400}:
        raise ValueError("physical SPR geometry drift")
    if int(config.get("parallel_candidate_workers", 0)) != 1:
        raise ValueError("official R4 physical comparison must be sequential")


def parent_run(config_path: Path, out_root: Path) -> Path:
    config = load_json(config_path)
    validate_config(config)
    freeze = load_generation2_finalist_freeze(FINALIST_FREEZE)
    if set(config["candidates"]) != set(freeze["selection"]["finalists"]):
        raise RuntimeError("physical config candidates do not match immutable finalist freeze")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / f"r4_ryzen_equal_wallclock_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "cells").mkdir()
    (run_dir / "logs").mkdir()
    (run_dir / "references").mkdir()

    metadata = machine_metadata()
    manifest = {
        "schema": "DEEPCASH_R4_RYZEN_EQUAL_WALLCLOCK_RUN_V1",
        "started_unix": time.time(),
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "finalist_freeze_sha256": sha256_file(FINALIST_FREEZE),
        "config": config,
        "machine": metadata,
    }
    (run_dir / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    boards = gen2_board_registry(str(config["board_set"]))
    candidates = list(config["candidates"])
    rows: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    physical_cells: list[tuple[dict[str, Any], str, int, str]] = []
    for phase in config["phases"]:
        for spr_text, stack in config["spr_to_stack"].items():
            for board_name, board_text in boards.items():
                physical_cells.append((phase, spr_text, int(stack), board_name))

    total = len(physical_cells) * len(candidates)
    completed = 0
    for cell_index, (phase, spr_text, stack, board_name) in enumerate(physical_cells):
        board_text = boards[board_name]
        spec = build_spec(
            board_text=board_text,
            p0_phase=float(phase["p0_phase"]),
            p1_phase=float(phase["p1_phase"]),
            range_combos=int(config["range_combos_per_player"]),
            pot=int(config["pot"]),
            stack=stack,
            min_bet=int(config["min_bet"]),
        )
        print(f"[reference] cell={cell_index+1}/{len(physical_cells)} phase={phase['name']} spr={spr_text} board={board_name}", flush=True)
        reference = train_exact_reference(spec, int(config["reference_iterations"]))
        ref_row = {
            "cell_index": cell_index,
            "phase": phase["name"],
            "spr": float(spr_text),
            "stack": stack,
            "board": board_name,
            "bet_sizes": list(spec.bet_sizes),
            **reference,
        }
        references.append(ref_row)
        ref_path = run_dir / "references" / f"ref_{cell_index:03d}_{phase['name']}_spr{spr_text}_{board_name}.json"
        ref_path.write_text(json.dumps(ref_row, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        offset = cell_index % len(candidates)
        order = candidates[offset:] + candidates[:offset]
        for candidate in order:
            completed += 1
            stem = f"cell_{cell_index:03d}_{phase['name']}_spr{spr_text}_{board_name}_{candidate}"
            input_path = run_dir / "cells" / f"{stem}.input.json"
            output_path = run_dir / "cells" / f"{stem}.json"
            log_path = run_dir / "logs" / f"{stem}.log"
            payload = {
                "cell_index": cell_index,
                "phase": phase["name"],
                "board": board_name,
                "board_text": board_text,
                "candidate": candidate,
                "p0_phase": phase["p0_phase"],
                "p1_phase": phase["p1_phase"],
                "pot": config["pot"],
                "stack": stack,
                "range_combos": config["range_combos_per_player"],
                "min_bet": config["min_bet"],
                "budget_seconds": config["candidate_wall_budget_seconds_per_board_phase_spr"],
                "chunk_iterations": config["candidate_chunk_iterations"],
                "reference": reference,
            }
            input_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"[candidate {completed}/{total}] {candidate} phase={phase['name']} spr={spr_text} board={board_name}", flush=True)
            cp = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--worker-input", str(input_path), "--worker-output", str(output_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            log_path.write_text(
                "STDOUT\n======\n" + cp.stdout + "\nSTDERR\n======\n" + cp.stderr,
                encoding="utf-8",
            )
            if cp.returncode != 0:
                raise RuntimeError(f"candidate worker failed: {stem}; inspect {log_path}")
            row = load_json(output_path)
            rows.append(row)

    summary = summarize(rows, candidates)
    payload = {
        "schema": "DEEPCASH_R4_RYZEN_EQUAL_WALLCLOCK_SUMMARY_V1",
        "config_sha256": sha256_file(config_path),
        "machine": metadata,
        "physical_cells": len(physical_cells),
        "candidate_cell_runs": len(rows),
        "candidates": candidates,
        "summary": summary,
        "production_warning": config["production_warning"],
    }
    (run_dir / "SUMMARY.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    fieldnames = [
        "cell_index", "phase", "board", "candidate", "spr", "stack", "bet_sizes",
        "budget_seconds", "train_wall_seconds", "budget_overshoot_seconds",
        "iterations_each_state", "joint_iterations_per_second", "peak_rss_bytes",
        "joint_infosets", "joint_action_slots", "joint_action_slot_ratio",
        "bucket_compression_ratio", "joint_exploitability_per_pot",
        "max_value_interval_width_per_pot", "worst_loss_upper_per_pot",
        "checkpoint_bytes", "checkpoint_write_mib_s", "checkpoint_read_mib_s",
        "checkpoint_sha256",
    ]
    with (run_dir / "RESULTS.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            flat = {key: row.get(key) for key in fieldnames}
            flat["bet_sizes"] = ",".join(str(x) for x in row["bet_sizes"])
            writer.writerow(flat)

    hashes = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            hashes.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    (run_dir / "SHA256SUMS.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")

    zip_path = run_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(run_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=f"{run_dir.name}/{path.relative_to(run_dir).as_posix()}")
    print("\nR4 physical Ryzen run complete")
    print(f"RUN_DIR={run_dir}")
    print(f"UPLOAD_ME={zip_path}")
    print(f"ZIP_SHA256={sha256_file(zip_path)}")
    return zip_path


def main() -> int:
    ap = argparse.ArgumentParser(description="DeepCash R4 physical Ryzen equal-wall-clock runner")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--out-root", type=Path, default=ROOT / "r4_ryzen_runs")
    ap.add_argument("--worker-input", type=Path)
    ap.add_argument("--worker-output", type=Path)
    args = ap.parse_args()
    if args.worker_input or args.worker_output:
        if not args.worker_input or not args.worker_output:
            ap.error("worker mode requires both --worker-input and --worker-output")
        worker_run(load_json(args.worker_input), args.worker_output)
        return 0
    parent_run(args.config.resolve(), args.out_root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
