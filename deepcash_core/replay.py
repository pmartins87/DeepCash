from __future__ import annotations

import hashlib
import json
from typing import Iterable

from .hand import HandActionRecord, HandSetup, HandState


def replay_hand(setup: HandSetup, actions: Iterable[HandActionRecord]) -> HandState:
    state = HandState.new(setup)
    for expected in actions:
        if state.street != expected.street:
            raise ValueError(f"replay street mismatch: expected {expected.street}, got {state.street}")
        if state.actor != expected.actor:
            raise ValueError(f"replay actor mismatch: expected {expected.actor}, got {state.actor}")
        state = state.apply(expected.action)
        generated = state.actions[-1]
        # Geometry is deterministic.  Detect corrupted logs immediately instead
        # of accepting an action label that happens to replay to a valid state.
        if generated != expected:
            raise ValueError(f"replay action geometry mismatch: expected={expected!r} generated={generated!r}")
    return state


def state_fingerprint(state: HandState) -> str:
    betting = None
    if state.betting is not None:
        betting = {
            "current_bet": state.betting.current_bet,
            "last_full_raise": state.betting.last_full_raise,
            "pending": sorted(state.betting.pending),
            "actor": state.betting.actor,
            "players": {
                str(s): {
                    "committed": p.committed,
                    "stack": p.stack,
                    "folded": p.folded,
                    "all_in": p.all_in,
                    "last_faced_bet": p.last_faced_bet,
                }
                for s, p in sorted(state.betting.players.items())
            },
        }
    payload = {
        "street": state.street.value,
        "visible_board": list(state.visible_board),
        "remaining": {str(k): v for k, v in sorted(state.remaining.items())},
        "total_contributed": {str(k): v for k, v in sorted(state.total_contributed.items())},
        "folded": sorted(state.folded),
        "betting": betting,
        "actions": [
            {
                "street": r.street.value,
                "actor": r.actor,
                "kind": r.action.kind.value,
                "raise_to": r.action.raise_to,
                "paid": r.paid,
                "pot_before": r.pot_before,
                "to_call_before": r.to_call_before,
                "current_bet_before": r.current_bet_before,
                "actor_committed_before": r.actor_committed_before,
                "min_full_raise_to_before": r.min_full_raise_to_before,
            }
            for r in state.actions
        ],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
