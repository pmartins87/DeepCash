#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deepcash_core.site_rule_evidence import (  # noqa: E402
    SiteRuleEvidenceError,
    load_evidence_file,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and fingerprint one anonymized DeepCash site-rule fixture."
    )
    parser.add_argument("evidence_file", type=Path)
    args = parser.parse_args()

    try:
        envelope = load_evidence_file(args.evidence_file)
    except SiteRuleEvidenceError as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "client_build": envelope.client_build,
                "fingerprint_sha256": envelope.fingerprint_sha256(),
                "scenario": envelope.scenario.value,
                "schema_version": envelope.schema_version,
                "site_name": envelope.site_name,
                "source_kind": envelope.source_kind.value,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
