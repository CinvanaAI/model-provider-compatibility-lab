"""Observed-attempt runner connecting adapters to the evidence ledger."""

from __future__ import annotations

from .adapters import ProviderAdapter
from .evidence import CompatibilityLedger, evidence_from_failure, evidence_from_success
from .types import AnalysisResponse, ModelRef


def attempt_task(
    adapter: ProviderAdapter,
    model: ModelRef,
    task_name: str,
    text: str,
    ledger: CompatibilityLedger,
    *,
    can_list_models: bool | None = None,
) -> AnalysisResponse:
    """Run one real attempt, persist normalized truth, and preserve the failure."""

    try:
        response = adapter.analyze(model, text)
    except Exception as exc:
        ledger.upsert(
            evidence_from_failure(
                model.provider_key,
                model.model_id,
                task_name,
                exc,
                can_list_models=can_list_models,
            )
        )
        raise
    ledger.upsert(evidence_from_success(model.provider_key, model.model_id, task_name, can_list_models=can_list_models))
    return response

