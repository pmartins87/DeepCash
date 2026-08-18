from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

from deepcash_core.r4_representation_gen2_freeze import load_generation2_finalist_freeze
from deepcash_core.river_benchmark_fixtures import parse_cards, quantile_range
from deepcash_core.river_lab import RiverGameSpec, materialize_bet_sizes
from deepcash_core.river_representation_gen2 import GEN2_REFERENCE_FRACTIONS, gen2_candidate_bucket_maps
from deepcash_core.river_representation_gen2_fixtures import gen2_board_registry
from deepcash_core.river_representation_lab import one_sided_bucket_maps
from deepcash_core.river_representation_training import advance_representation_cfr_plus, init_representation_cfr_plus

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "deepcash_core" / "data" / "r4_ryzen_instrumentation_repair_v1.json"
FINALIST_FREEZE = ROOT / "deepcash_core" / "data" / "r4_representation_generation2_finalists_v1.json"
EXPECTED_CANDIDATES = ["matchup_cluster8", "equity8", "matchup_cluster4"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_git(*args: str) -> str:
    try:
        cp = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=True)
        return cp.stdout.strip()
    except Exception:
        return ""


def _windows_process_counters() -> dict[str, int] | None:
    if os.name != "nt":
        return None
    try:
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.argtypes = []
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        handle = kernel32.GetCurrentProcess()
        ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
        if not ok:
            return None
        return {
            "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
            "working_set_bytes": int(counters.WorkingSetSize),
            "pagefile_bytes": int(counters.PagefileUsage),
            "peak_pagefile_bytes": int(counters.PeakPagefileUsage),
        }
    except Exception:
        return None


def process_memory() -> dict[str, int] | None:
    win = _windows_process_counters()
    if win is not None:
        return win
    try:
        import resource

        peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if sys.platform == "darwin":
            peak_bytes = peak
        else:
            peak_bytes = peak * 1024
        return {
            "peak_working_set_bytes": peak_bytes,
            "working_set_bytes": peak_bytes,
            "pagefile_bytes": 0,
            "peak_pagefile_bytes": 0,
        }
    except Exception:
        return None


def process_affinity() -> list[int] | None:
    if hasattr(os, "sched_getaffinity"):
        try:
            return sorted(int(x) for x in os.sched_getaffinity(0))
        except Exception:
            pass
    if os.name == "nt":
        try:
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.GetCurrentProcess.argtypes = []
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            kernel32.GetProcessAffinityMask.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(ctypes.c_size_t),
                ctypes.POINTER(ctypes.c_size_t),
            ]
            kernel32.GetProcessAffinityMask.restype = wintypes.BOOL
            process_mask = ctypes.c_size_t()
            system_mask = ctypes.c_size_t()
            ok = kernel32.GetProcessAffinityMask(
                kernel32.GetCurrentProcess(), ctypes.byref(process_mask), ctypes.byref(system_mask)
            )
            if not ok:
                return None
            mask = int(process_mask.value)
            return [i for i in range(mask.bit_length()) if mask & (1 << i)]
        except Exception:
            return None
    return None


def validate_instrumentation(*, strict_windows: bool = True) -> dict[str, Any]:
    memory = process_memory()
    affinity = process_affinity()
    if memory is None or int(memory.get("peak_working_set_bytes", 0)) <= 0:
        raise RuntimeError("peak working-set/RSS instrumentation unavailable")
    if strict_windows and os.name == "nt" and not affinity:
        raise RuntimeError("Windows process-affinity instrumentation unavailable")
    return {"memory": memory, "affinity": affinity}


def machine_metadata() -> dict[str, Any]:
    instrumentation = validate_instrumentation(strict_windows=True)
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "processor_identifier": os.environ.get("PROCESSOR_IDENTIFIER", ""),
        "python": sys.version,
        "logical_cpu_count": os.cpu_count(),
        "affinity": instrumentation["affinity"],
        "preflight_memory": instrumentation["memory"],
        "git_head": run_git("rev-parse", "HEAD"),
        "git_status_porcelain": run_git("status", "--porcelain"),
    }


def build_spec(*, board_text: str, p0_phase: float, p1_phase: float, range_combos: int,
               pot: int, stack: int, min_bet: int) -> RiverGameSpec:
    board = parse_cards(board_text)
    p0_range = quantile_range(board, range_combos, p0_phase)
    p1_range = quantile_range(board, range_combos, p1_phase)
    bet_sizes = materialize_bet_sizes(
        pot=pot, stack=stack, min_bet=min_bet, fractions=GEN2_REFERENCE_FRACTIONS
    )
    return RiverGameSpec(board, p0_range, p1_range, pot, bet_sizes)


def worker_run(payload: dict[str, Any], output_path: Path) -> None:
    validate_instrumentation(strict_windows=True)
    spec = build_spec(
        board_text=str(payload["board_text"]),
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

    iterations = int(payload["warmup_iterations_each_state"])
    if iterations <= 0:
        raise ValueError("warmup iterations must be positive")
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    advance_representation_cfr_plus(spec, p0_maps, p0_state, additional_iterations=iterations)
    advance_representation_cfr_plus(spec, p1_maps, p1_state, additional_iterations=iterations)
    advance_representation_cfr_plus(spec, candidate, joint_state, additional_iterations=iterations)
    wall = time.perf_counter() - started_wall
    cpu = time.process_time() - started_cpu

    memory = process_memory()
    affinity = process_affinity()
    if memory is None or int(memory.get("peak_working_set_bytes", 0)) <= 0:
        raise RuntimeError("worker peak working-set/RSS measurement failed")
    if os.name == "nt" and not affinity:
        raise RuntimeError("worker Windows affinity measurement failed")

    exact_buckets = len(spec.p0_range) + len(spec.p1_range)
    materialized_buckets = candidate.p0_bucket_count + candidate.p1_bucket_count
    exact_slots = sum(len(v) for v in init_representation_cfr_plus(spec, one_sided_bucket_maps(spec, candidate, 0)).regrets.values())
    joint_slots = sum(len(v) for v in joint_state.regrets.values())

    result = {
        "schema": "DEEPCASH_R4_RYZEN_INSTRUMENTATION_REPAIR_CELL_V1",
        "cell_index": int(payload["cell_index"]),
        "phase": payload["phase"],
        "board": payload["board"],
        "candidate": candidate_name,
        "spr": float(payload["stack"]) / float(payload["pot"]),
        "stack": int(payload["stack"]),
        "pot": int(payload["pot"]),
        "bet_sizes": list(spec.bet_sizes),
        "warmup_iterations_each_state": iterations,
        "warmup_wall_seconds": wall,
        "warmup_cpu_seconds": cpu,
        "p0_buckets": candidate.p0_bucket_count,
        "p1_buckets": candidate.p1_bucket_count,
        "bucket_compression_ratio": materialized_buckets / exact_buckets,
        "joint_infosets": len(joint_state.regrets),
        "joint_action_slots": joint_slots,
        "diagnostic_p0_action_slots": exact_slots,
        "affinity": affinity,
        **memory,
    }
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate": candidate_name,
        "cell_index": result["cell_index"],
        "peak_working_set_bytes": result["peak_working_set_bytes"],
        "affinity_count": len(affinity or []),
    }, sort_keys=True))


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != "DEEPCASH_R4_RYZEN_INSTRUMENTATION_REPAIR_V1":
        raise ValueError("unexpected instrumentation-repair schema")
    if config.get("status") != "FROZEN_BEFORE_REPAIR_RESULT":
        raise ValueError("instrumentation-repair config is not frozen")
    if config.get("candidates") != EXPECTED_CANDIDATES:
        raise ValueError("candidate freeze drift")
    if config.get("board_set") != "heldout_v2":
        raise ValueError("board-set drift")
    if config.get("spr_to_stack") != {"1": 100, "2": 200, "4": 400}:
        raise ValueError("SPR geometry drift")
    if int(config.get("parallel_candidate_workers", 0)) != 1:
        raise ValueError("repair run must remain sequential")
    if int(config.get("warmup_iterations_each_state", 0)) <= 0:
        raise ValueError("warmup iterations must be positive")


def summarize(rows: list[dict[str, Any]], candidates: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for candidate in candidates:
        selected = [r for r in rows if r["candidate"] == candidate]
        peaks = [int(r["peak_working_set_bytes"]) for r in selected]
        current = [int(r["working_set_bytes"]) for r in selected]
        walls = [float(r["warmup_wall_seconds"]) for r in selected]
        out[candidate] = {
            "cells": len(selected),
            "peak_working_set_bytes_max": max(peaks),
            "peak_working_set_bytes_mean": statistics.fmean(peaks),
            "working_set_bytes_mean": statistics.fmean(current),
            "warmup_wall_seconds_mean": statistics.fmean(walls),
            "affinity_widths": sorted({len(r.get("affinity") or []) for r in selected}),
        }
    return out


def parent_run(config_path: Path, out_root: Path) -> Path:
    config = load_json(config_path)
    validate_config(config)
    freeze = load_generation2_finalist_freeze(FINALIST_FREEZE)
    if set(config["candidates"]) != set(freeze["selection"]["finalists"]):
        raise RuntimeError("repair candidates do not match immutable Generation-2 finalists")

    metadata = machine_metadata()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / f"r4_ryzen_instrumentation_repair_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "cells").mkdir()
    (run_dir / "logs").mkdir()
    manifest = {
        "schema": "DEEPCASH_R4_RYZEN_INSTRUMENTATION_REPAIR_RUN_V1",
        "started_unix": time.time(),
        "config_sha256": sha256_file(config_path),
        "finalist_freeze_sha256": sha256_file(FINALIST_FREEZE),
        "config": config,
        "machine": metadata,
    }
    (run_dir / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    boards = gen2_board_registry(str(config["board_set"]))
    candidates = list(config["candidates"])
    physical_cells: list[tuple[dict[str, Any], str, int, str]] = []
    for phase in config["phases"]:
        for spr_text, stack in config["spr_to_stack"].items():
            for board_name in boards:
                physical_cells.append((phase, spr_text, int(stack), board_name))

    rows: list[dict[str, Any]] = []
    total = len(physical_cells) * len(candidates)
    completed = 0
    for cell_index, (phase, spr_text, stack, board_name) in enumerate(physical_cells):
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
                "board_text": boards[board_name],
                "candidate": candidate,
                "p0_phase": phase["p0_phase"],
                "p1_phase": phase["p1_phase"],
                "pot": config["pot"],
                "stack": stack,
                "range_combos": config["range_combos_per_player"],
                "min_bet": config["min_bet"],
                "warmup_iterations_each_state": config["warmup_iterations_each_state"],
            }
            input_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"[repair {completed}/{total}] {candidate} phase={phase['name']} spr={spr_text} board={board_name}", flush=True)
            cp = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--worker-input", str(input_path), "--worker-output", str(output_path)],
                cwd=ROOT, text=True, capture_output=True,
            )
            log_path.write_text("STDOUT\n======\n" + cp.stdout + "\nSTDERR\n======\n" + cp.stderr, encoding="utf-8")
            if cp.returncode != 0:
                raise RuntimeError(f"repair worker failed: {stem}; inspect {log_path}")
            row = load_json(output_path)
            if row.get("peak_working_set_bytes") is None or not row.get("affinity"):
                raise RuntimeError(f"repair instrumentation incomplete: {stem}")
            rows.append(row)

    summary = {
        "schema": "DEEPCASH_R4_RYZEN_INSTRUMENTATION_REPAIR_SUMMARY_V1",
        "physical_cells": len(physical_cells),
        "candidate_cell_runs": len(rows),
        "candidates": candidates,
        "machine": metadata,
        "summary": summarize(rows, candidates),
        "decision_boundary": config["decision_boundary"],
    }
    (run_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    fieldnames = [
        "cell_index", "phase", "board", "candidate", "spr", "stack", "bet_sizes",
        "warmup_iterations_each_state", "warmup_wall_seconds", "warmup_cpu_seconds",
        "peak_working_set_bytes", "working_set_bytes", "peak_pagefile_bytes", "pagefile_bytes",
        "affinity", "p0_buckets", "p1_buckets", "bucket_compression_ratio",
        "joint_infosets", "joint_action_slots",
    ]
    with (run_dir / "RESULTS.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            flat = {key: row.get(key) for key in fieldnames}
            flat["bet_sizes"] = ",".join(str(x) for x in row["bet_sizes"])
            flat["affinity"] = ",".join(str(x) for x in row.get("affinity") or [])
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
    print("\nR4 Ryzen instrumentation repair complete")
    print(f"UPLOAD_ME={zip_path}")
    print(f"ZIP_SHA256={sha256_file(zip_path)}")
    return zip_path


def main() -> int:
    ap = argparse.ArgumentParser(description="DeepCash R4 Ryzen instrumentation repair")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--out-root", type=Path, default=ROOT / "r4_ryzen_runs")
    ap.add_argument("--worker-input", type=Path)
    ap.add_argument("--worker-output", type=Path)
    ap.add_argument("--preflight", action="store_true")
    args = ap.parse_args()
    if args.preflight:
        print(json.dumps(validate_instrumentation(strict_windows=True), sort_keys=True))
        return 0
    if args.worker_input or args.worker_output:
        if not args.worker_input or not args.worker_output:
            ap.error("worker mode requires both --worker-input and --worker-output")
        worker_run(load_json(args.worker_input), args.worker_output)
        return 0
    parent_run(args.config.resolve(), args.out_root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
