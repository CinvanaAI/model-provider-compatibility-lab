"""Evidence-backed provider compatibility primitives."""

from .adapters import OllamaAdapter, OpenAIAdapter, ProviderAdapter
from .evidence import CompatibilityLedger, classify_failure
from .lab import attempt_task
from .pricing import CostEstimate, PricingRecord, estimate_cost, is_stale
from .selection import allowed_models, models_with_status
from .types import AnalysisResponse, AttemptEvidence, ModelRef, ProviderConfig, ProviderError

__all__ = [
    "AnalysisResponse",
    "AttemptEvidence",
    "CompatibilityLedger",
    "CostEstimate",
    "ModelRef",
    "OllamaAdapter",
    "OpenAIAdapter",
    "PricingRecord",
    "ProviderAdapter",
    "ProviderConfig",
    "ProviderError",
    "allowed_models",
    "attempt_task",
    "classify_failure",
    "estimate_cost",
    "is_stale",
    "models_with_status",
]

