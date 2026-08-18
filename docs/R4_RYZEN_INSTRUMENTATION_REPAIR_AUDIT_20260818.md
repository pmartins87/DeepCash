# R4 Ryzen instrumentation-repair audit — 2026-08-18

Status: **VALID / MEMORY+AFFINITY GAP CLOSED / R4 STRATEGIC LEADER UNCHANGED / R5-R6 COMPATIBILITY NEXT**

Source artifact uploaded from the target Ryzen 9: `r4_ryzen_instrumentation_repair_20260818_130319.zip`.

Artifact ZIP SHA-256: `5bbf592b2f53e76cb650d7a336cc016a23f227392a3fcc6008b114f4dffabaf7`.

The archive contains 436 files. `SHA256SUMS.txt` lists 435 payload files; every listed file was present, every digest revalidated, there were zero mismatches, and there were no unlisted payload files.

## Execution identity and completeness

- git head recorded by the repair run: `f48cff9d9f87eda5ff4e0bd119512a2c1bf0b19d`;
- Python: 3.11.9 x64;
- Windows 10 build 26200;
- CPU: `AMD64 Family 26 Model 68 Stepping 0, AuthenticAMD`;
- logical CPUs: 32;
- process affinity at parent preflight: all logical CPUs `[0..31]`;
- 48 physical cells = 8 already-consumed Generation-2 heldout-v2 boards × phases A/B × SPR 1/2/4;
- 144 candidate diagnostics = exactly 48 each for `matchup_cluster8`, `equity8`, `matchup_cluster4`;
- every worker used a fresh subprocess;
- every diagnostic used exactly 100 warm-up iterations for each of the p0-restricted, p1-restricted and joint states;
- all intended physical action geometries were preserved: SPR1 `[25,50,100]`, SPR2 `[25,50,100,200]`, SPR4 `[25,50,100,200,400]`;
- all 144 logs were present and contained no ERROR/TRACEBACK/EXCEPTION/FAILED/FATAL token.

This repair used only already-consumed physical coordinates and was frozen to fill instrumentation fields. It is not new strategic held-out evidence and is not allowed to retune the strategic ranking established by the 20-second equal-wall-clock run.

## Instrumentation result

The Windows native instrumentation repair succeeded fail-closed:

- parent preflight peak working set: `24,608,768` bytes;
- parent affinity width: 32 logical CPUs;
- `peak_working_set_bytes`: non-null and positive in 144/144 candidate payloads;
- `affinity`: non-null and exactly 32 CPUs in 144/144 candidate payloads.

Candidate aggregates:

| candidate | cells | mean peak working set | max peak working set | mean warm-up wall s | mean action-slot ratio from run-1 context |
|---|---:|---:|---:|---:|---:|
| `matchup_cluster8` | 48 | 25,589,163 B | 25,784,320 B | 0.749211 | 0.886719 |
| `equity8` | 48 | 25,582,592 B | 25,821,184 B | 0.747089 | 0.855469 |
| `matchup_cluster4` | 48 | 25,553,408 B | 25,735,168 B | 0.740192 | 0.500000 |

At this microgame scale the three candidates have effectively indistinguishable process-level memory footprints. The large action-slot reduction of `matchup_cluster4` does not translate into a meaningful working-set advantage in the current Python process envelope. This is consistent with the run-1 result where `matchup_cluster4` was only about 1.38% faster despite its 50% action-slot footprint.

## Combined physical judgment

The authoritative strategic/throughput evidence remains the 20-second equal-wall-clock run audited in `docs/R4_RYZEN_EQUAL_WALLCLOCK_RUN1_AUDIT_20260818.md`:

- `matchup_cluster8`: mean/worst conservative upper loss per pot `0.00040445 / 0.00088263`, mean joint throughput `136.9407 it/s`;
- `equity8`: `0.00226666 / 0.01141806`, `137.0100 it/s`;
- `matchup_cluster4`: `0.01581024 / 0.07429504`, `138.8264 it/s`.

The repair closes the only instrumentation defect found in run-1. It does not change the strategic ranking.

Therefore:

1. **`matchup_cluster8` remains the leading R4 production candidate.**
2. `equity8` remains the exact/equity anchor for compatibility checks.
3. `matchup_cluster4` remains an aggressive compression control and is no longer a serious fidelity candidate at the current scale.
4. The R4 physical river evidence package is now complete for fidelity, throughput, memory and affinity.
5. R4 is still **IN_PROGRESS** because the production freeze was precommitted to require compatibility with the intended R5 traversal and the first R6 street/public-state architecture.

## Next finite gate

Do not open Generation-3 from this result. The next gate is a separately versioned compatibility bridge:

- prove the selected R4 representation works with the leading exact R5 alternating post-update discounted control without changing solver semantics;
- prove deterministic checkpoint/resume on the combined representation+solver path;
- create the first R6 turn-to-river public-state transfer contract with exact card removal/range conditioning;
- run a small frozen physical Ryzen compatibility battery comparing `matchup_cluster8` to the `equity8` anchor under that bridge;
- only then decide whether the R4 production representation can be frozen or whether a concrete compatibility failure requires reopening candidate engineering.

No strategic production training is authorized by this audit.