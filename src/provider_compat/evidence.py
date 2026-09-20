"""Compatibility classification and JSON-backed evidence ledger."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .types import AttemptEvidence, ProviderError


STATUSES = ("supported", "unsupported", "fixable", "unknown")


def _validate_record(record: Any) -> None:
    if not isinstance(record, dict) or not all(isinstance(record.get(k), str) and record[k] for k in ("provider_key", "model_id", "task_name")) or record.get("status") not in STATUSES:
        raise ValueError("Compatibility ledger contains an invalid evidence record")


def classify_failure(error: BaseException) -> tuple[str, str, str | None]:
    """Classify a failed attempt without claiming more than the error proves."""

    text = f"{type(error).__name__}: {error}".casefold()
    if any(marker in text for marker in ("missing", "api key", "credential", "unauthorized", "401")):
        return ("fixable", "Provider credentials are missing or rejected.", "Configure valid credentials and retry the same task.")
    if any(marker in text for marker in ("not found", "unknown model", "404")):
        return ("fixable", "The selected model or endpoint was not found.", "Refresh inventory or correct the model/endpoint, then retry.")
    if any(marker in text for marker in ("not supported", "unsupported", "does not support")):
        return ("unsupported", "The provider reported that this task is unsupported.", None)
    if any(marker in text for marker in ("timeout", "timed out", "connection", "temporarily")):
        return ("unknown", "The attempt did not establish task compatibility.", "Retry when the provider is reachable.")
    return ("unknown", "The failed attempt is not enough to classify compatibility.", None)


def evidence_from_success(provider_key: str, model_id: str, task_name: str, *, can_list_models: bool | None = None) -> AttemptEvidence:
    return AttemptEvidence(
        provider_key=provider_key,
        model_id=model_id,
        task_name=task_name,
        status="supported",
        attempted_at=datetime.now(timezone.utc).isoformat(),
        can_list_models=can_list_models,
        can_execute_task=True,
    )


def evidence_from_failure(
    provider_key: str,
    model_id: str,
    task_name: str,
    error: BaseException,
    *,
    can_list_models: bool | None = None,
) -> AttemptEvidence:
    status, reason, hint = classify_failure(error)
    return AttemptEvidence(
        provider_key=provider_key,
        model_id=model_id,
        task_name=task_name,
        status=status,
        attempted_at=datetime.now(timezone.utc).isoformat(),
        can_list_models=can_list_models,
        can_execute_task=False,
        blocked_reason=reason,
        fix_hint=hint,
        error_type=getattr(error, "error_type", type(error).__name__),
        error_message=str(error),
    )


class CompatibilityLedger:
    """Latest evidence per provider/model/task, written atomically."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"records": []}
        # Existing evidence must never silently become an empty ledger.
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        records = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(records, list):
            raise ValueError("Compatibility ledger must contain a records list")
        keys = set()
        for record in records:
            _validate_record(record)
            key = (record["provider_key"], record["model_id"], record["task_name"])
            if key in keys:
                raise ValueError("Compatibility ledger contains duplicate evidence keys")
            keys.add(key)
        return {"records": records}

    def upsert(self, evidence: AttemptEvidence) -> None:
        incoming = asdict(evidence)
        _validate_record(incoming)
        payload = self.load()
        key = (evidence.provider_key, evidence.model_id, evidence.task_name)
        records = [
            record
            for record in payload["records"]
            if not (
                isinstance(record, dict)
                and (record.get("provider_key"), record.get("model_id"), record.get("task_name")) == key
            )
        ]
        records.append(incoming)
        records.sort(key=lambda item: (item["provider_key"], item["model_id"], item["task_name"]))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps({"records": records}, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)

