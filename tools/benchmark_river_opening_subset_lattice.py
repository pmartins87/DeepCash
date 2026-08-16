"""Run the one-raise opening benchmark over every proper subset of 25/50/75/100.

This deliberately reuses the already-gated common-reference benchmark engine.
Only the candidate registry is replaced. The rich four-size reference, exact-BR
interval accounting, all-in clipping and output schema remain unchanged.
"""

from __future__ import annotations

import benchmark_river_raise_reference_convergence as benchmark
from deepcash_core.river_benchmark_fixtures import ONE_RAISE_OPEN_SUBSET_LATTICE


def main() -> None:
    benchmark.ONE_RAISE_OPEN_CANDIDATES = ONE_RAISE_OPEN_SUBSET_LATTICE
    benchmark.main()


if __name__ == "__main__":
    main()
