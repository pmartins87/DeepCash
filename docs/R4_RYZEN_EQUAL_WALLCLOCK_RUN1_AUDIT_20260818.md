# R4 physical Ryzen equal-wall-clock run-1 audit — 2026-08-18

Status: **STRATEGIC/THROUGHPUT EVIDENCE VALID / MEMORY+AFFINITY INSTRUMENTATION INCOMPLETE / R4 NOT YET PASS**

Source artifact uploaded from the target Ryzen 9: `r4_ryzen_equal_wallclock_20260818_111633.zip`.

Artifact ZIP SHA-256: `136810b601a01449fdfcf1725b25dd357f9309f3f0c3d25e0496d170097e4909`.

The archive contains 628 files. `SHA256SUMS.txt` lists 627 payload files; every listed file was present and every digest revalidated with zero mismatches. There were no unlisted payload files.

## Execution integrity

- git head recorded by the physical run: `ce77926692fb4a1918dd12b6a7c439af751b6675`;
- Python: 3.11.9 x64;
- Windows 10 build 26200;
- CPU identity: `AMD64 Family 26 Model 68 Stepping 0, AuthenticAMD`;
- logical CPUs: 32;
- 48 physical cells = 8 frozen heldout-v2 boards × phases A/B × SPR 1/2/4;
- 144 candidate runs = exactly 48 each for `matchup_cluster8`, `equity8`, `matchup_cluster4`;
- all candidate budgets were exactly 20.0 s;
- max budget overshoot was 0.094875 s and mean overshoot 0.035184 s;
- 144/144 logs were present with empty STDERR and no ERROR/TRACEBACK/EXCEPTION/WARNING/FAILED/FATAL token;
- 48 exact-reference payloads were present and each candidate input reused the exact reference for its physical cell;
- 144 checkpoints were present and their per-row checkpoint SHA-256 values agree with the archive digest manifest;
- intended physical action geometries were preserved in every row: SPR1 `[25,50,100]`, SPR2 `[25,50,100,200]`, SPR4 `[25,50,100,200,400]`.

CPU-time / wall-time ratios were ~0.999 for all three candidates, which is consistent with an essentially uninterrupted single-process CPU-bound measurement.

## Equal-wall-clock results

| candidate | mean upper/pot | p90 upper/pot | worst upper/pot | median iters/state | mean joint it/s | mean action-slot ratio |
|---|---:|---:|---:|---:|---:|---:|
| `matchup_cluster8` | **0.00040445** | **0.00070123** | **0.00088263** | 2635 | 136.9407 | 0.886719 |
| `equity8` | 0.00226666 | 0.00899675 | 0.01141806 | 2640 | 137.0100 | 0.855469 |
| `matchup_cluster4` | 0.01581024 | 0.02901545 | 0.07429504 | 2690 | **138.8264** | **0.500000** |

`matchup_cluster8` and `equity8` have effectively identical physical throughput at this scale: mean joint throughput differs by only ~0.05%. `matchup_cluster4` is only ~1.38% faster than `equity8` despite halving the action-slot footprint, while suffering a much larger fidelity loss.

By SPR, `matchup_cluster8` mean upper/pot is approximately 0.000328 / 0.000398 / 0.000487 for SPR1/2/4; `equity8` is approximately 0.002181 / 0.002260 / 0.002360; `matchup_cluster4` is approximately 0.011207 / 0.015237 / 0.020986.

At equal wall clock, `matchup_cluster8` is strictly better than `equity8` in 29/48 cells, exactly tied within 1e-9 in 10/48, and nominally worse in 9/48. All nine adverse differences are tiny relative to the solver/reference interval width; the largest nominal adverse difference is only `3.8225e-05` upper-loss/pot while that cell's interval widths are ~`3.9e-04` to `4.3e-04`. The aggregate and worst-case physical evidence therefore still strongly favors `matchup_cluster8`.

`matchup_cluster4` is worse than `equity8` in 45/48 cells and better in only 3/48 at this physical checkpoint. Its retained role remains aggressive compression control.

## Instrumentation defect discovered during audit

Every one of the 144 candidate payloads has:

- `peak_rss_bytes = null`;
- `affinity = null`.

The parent machine metadata also records `affinity = null`.

This violates the precommitted physical-gate requirement to retain peak RSS/memory footprint and to hold constant or record process affinity. The strategic fidelity and equal-wall-clock throughput evidence remain usable because their source fields are complete and internally consistent, but this run alone cannot close the R4 physical gate or authorize the production representation freeze.

The defect is in the Windows instrumentation path, not in candidate training. No rerun of heldout-v2 strategic selection and no Generation-3 candidate search is justified.

## Frozen repair policy

Before looking at any new physical memory result, repair the missing instrumentation as a **separate orthogonal diagnostic** over the same already-consumed 48 physical cells and exactly the same three frozen candidates. The repair run must:

1. create each candidate/cell in a fresh subprocess;
2. use the same board/phase/SPR geometry and deterministic rotation policy;
3. perform a fixed warm-up of all three representation states (p0-restricted, p1-restricted, joint) solely to materialize the runtime footprint;
4. record Windows peak working set/RSS and process affinity using explicit native function signatures;
5. fail closed before the full diagnostic if either metric is unavailable on the target Windows machine;
6. use the repair result only for memory/affinity evidence, not to retune strategic ranking;
7. preserve the run-1 20-second equal-wall-clock artifact as the authoritative physical fidelity/throughput evidence.

After that instrumentation repair is audited, R4 may advance to the already-required R5 traversal / first R6 street compatibility gate. R4 remains **IN_PROGRESS** until that compatibility evidence resolves the production freeze.