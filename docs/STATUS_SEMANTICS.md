# DeepCash roadmap status semantics

These labels describe execution state, not confidence or strategic quality.

## PASS

The gate's exit criteria are satisfied by inspected evidence. A workflow merely being green is not enough if its artifact or methodology has not been accepted.

## IN_PROGRESS

The gate is actively being developed or validated. Sub-gates may be PASS, negative evidence, invalidated, or still running while the overall gate remains open.

## PENDING

The gate has not become an active critical-path gate yet. Preparatory work that cannot contaminate earlier evidence may still be done when useful. `PENDING` does not mean all prerequisites are already satisfied; it means there is no project-level instruction to begin the gate now.

## BLOCKED

A hard dependency explicitly prevents execution of the gate itself. Crossing the block would make the result invalid, wasteful, or both.

`R9` is intentionally `BLOCKED` until every required R1–R8 production exit gate passes. R9 is the expensive long production-training commitment. Starting it while rules, action abstraction, representation, solver/traversal, resolving/blueprint architecture, or physical Ryzen calibration can still change would risk training the wrong game/architecture for weeks or months.

Therefore `BLOCKED` is **not a failure state**. For R9 it is a healthy safety lock.

## INVALIDATED (evidence only)

Used for a run/artifact whose methodology or implementation was later shown to be unsuitable for the claimed conclusion. The evidence remains in history and is never silently converted into PASS. Fixes receive a new run/gate.

## RUNNING / UNACCEPTED (evidence only)

A workflow is executing or has not yet been inspected. It may not be cited as accepted evidence until completion and inspection.

## Current intended sequence

```text
R0 PASS
R1 IN_PROGRESS
R2 PASS
R3 IN_PROGRESS
R4 IN_PROGRESS
R5 IN_PROGRESS
R6-R8 PENDING
R9 BLOCKED
R10-R15 PENDING
READY FOR TABLES = NO
```

R6–R8 remain `PENDING`, rather than `BLOCKED`, because safe preparatory engineering can be performed before they become the active critical path. R9 is different: the production training itself is explicitly prohibited until the upstream architecture and physical budget are frozen.
