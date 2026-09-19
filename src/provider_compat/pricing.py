"""Dated pricing records kept separate from compatibility evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class PricingRecord:
    provider_key: str
    model_id: str
    input_cost_per_million: float
    output_cost_per_million: float
    source: str
    updated_at: str
    cached_input_cost_per_million: float | None = None


@dataclass(frozen=True)
class CostEstimate:
    input_cost: float
    output_cost: float
    total_cost: float


def estimate_cost(record: PricingRecord, *, input_tokens: int, output_tokens: int) -> CostEstimate:
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must not be negative")
    input_cost = input_tokens / 1_000_000 * record.input_cost_per_million
    output_cost = output_tokens / 1_000_000 * record.output_cost_per_million
    return CostEstimate(input_cost, output_cost, input_cost + output_cost)


def is_stale(record: PricingRecord, *, max_age_days: int = 7, now: datetime | None = None) -> bool:
    try:
        updated = datetime.fromisoformat(record.updated_at)
    except ValueError:
        return True
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    reference = now or datetime.now(timezone.utc)
    return reference - updated > timedelta(days=max_age_days)

