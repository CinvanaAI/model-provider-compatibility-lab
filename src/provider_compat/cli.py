"""Offline synthetic demonstration of compatibility evidence updates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from .evidence import CompatibilityLedger, evidence_from_failure, evidence_from_success
from .types import ProviderError


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    path = Path("evidence") / "synthetic-ledger.json"
    ledger = CompatibilityLedger(path)
    ledger.upsert(evidence_from_success("demo", "working-model", "text_analysis"))
    ledger.upsert(
        evidence_from_failure(
            "demo",
            "missing-model",
            "text_analysis",
            ProviderError("unknown model", status_code=404),
            can_list_models=True,
        )
    )
    print(json.dumps(ledger.load(), indent=2))
    print(f"Saved synthetic evidence: {path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

