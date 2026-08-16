from __future__ import annotations

"""Compatibility shim for the first no-private-leak baseline API.

The original v1 implementation imported a non-existent private helper from
``river_lab`` and therefore never passed its CI gate.  The self-contained v2
implementation replaces it.  Keeping this module as a thin alias preserves old
tests/imports without maintaining two independent baseline implementations.
"""

from .river_vr_infoset_baseline_v2 import exact_infoset_action_baselines_v2


def exact_infoset_action_baselines(*args, **kwargs):
    return exact_infoset_action_baselines_v2(*args, **kwargs)
