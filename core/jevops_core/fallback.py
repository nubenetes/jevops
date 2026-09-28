"""
Resilience & Degraded Defaults Engine (John Rood's Law).

"What the pipeline does when the decider is down or slow:
pick the degraded default per decision, and pick it toward noise:
keep everything, page anyway. The only calls that get to fail quiet
are the reversible ones."
-- John Rood (@johnroodepic)
"""

import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from .primitives import (
    ChoiceQuestion,
    ChoiceResult,
    DecisionBatchRequest,
    DecisionBatchResponse,
    DecisionQuestion,
    DecisionResult,
    NoulQuestion,
    NoulResult,
    ScoreQuestion,
    ScoreResult,
)


class DegradedAction(str, Enum):
    """Degraded default strategies."""
    FAIL_TOWARD_NOISE = "fail_toward_noise"   # Keep logs/spans, retain metrics, page oncall
    FAIL_SAFE_BLOCK = "fail_safe_block"       # Block irreversible/destructive K8s actions
    FAIL_QUIET_ALLOW = "fail_quiet_allow"     # Allow reversible/benign optimizations
    FALLBACK_RULE = "fallback_rule"           # Execute deterministic heuristic rule


class CircuitState(str, Enum):
    CLOSED = "closed"         # Healthy: routing to decider
    OPEN = "open"             # Tripped: bypass decider, use degraded defaults
    HALF_OPEN = "half_open"   # Probing: test single request


class CircuitBreaker:
    """Production circuit breaker protecting operational pipelines."""

    def __init__(
        self,
        max_failures: int = 3,
        latency_sla_ms: float = 250.0,
        reset_timeout_sec: float = 15.0,
    ):
        self.max_failures = max_failures
        self.latency_sla_ms = latency_sla_ms
        self.reset_timeout_sec = reset_timeout_sec

        self.state: CircuitState = CircuitState.CLOSED
        self.failure_count: int = 0
        self.last_state_change: float = time.time()
        self.total_calls: int = 0
        self.tripped_count: int = 0

    def can_execute(self) -> bool:
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_state_change > self.reset_timeout_sec:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                return True
            return False
        return True

    def record_success(self, latency_ms: float):
        self.total_calls += 1
        if latency_ms > self.latency_sla_ms:
            # Latency SLA breach counts as operational failure
            self.record_failure(f"Latency SLA breached: {latency_ms:.1f}ms > {self.latency_sla_ms}ms")
            return

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_state_change = time.time()
        else:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self, reason: str = ""):
        self.total_calls += 1
        self.failure_count += 1
        if self.failure_count >= self.max_failures or self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            self.tripped_count += 1


class DegradedFallbackHandler:
    """
    Applies John Rood's degraded default policies per question type and reversibility.
    """

    @staticmethod
    def resolve_degraded_response(
        request: DecisionBatchRequest,
        reason: str,
        latency_ms: float = 0.0,
        custom_fallbacks: Optional[Dict[str, Any]] = None,
    ) -> DecisionBatchResponse:
        results: Dict[str, DecisionResult] = {}
        fallbacks = custom_fallbacks or {}

        for q in request.questions:
            custom = fallbacks.get(q.id)

            if isinstance(q, ChoiceQuestion):
                # If custom fallback provided, use it
                if custom is not None:
                    selected = custom
                elif q.default is not None:
                    selected = q.default
                else:
                    # John Rood rule: if options include 'keep'/'retain'/'page'/'investigate'/'block',
                    # pick toward noise/safety!
                    candidates = [opt.lower() for opt in q.options]
                    if "keep" in candidates:
                        selected = q.options[candidates.index("keep")]
                    elif "retain" in candidates:
                        selected = q.options[candidates.index("retain")]
                    elif "investigate" in candidates:
                        selected = q.options[candidates.index("investigate")]
                    elif "page" in candidates:
                        selected = q.options[candidates.index("page")]
                    elif "block" in candidates:
                        selected = q.options[candidates.index("block")]
                    elif "hold" in candidates:
                        selected = q.options[candidates.index("hold")]
                    else:
                        selected = q.options[0]

                results[q.id] = ChoiceResult(
                    id=q.id,
                    selected=selected,
                    confidence=1.0,
                    probabilities={opt: (1.0 if opt == selected else 0.0) for opt in q.options},
                    degraded=True,
                )

            elif isinstance(q, ScoreQuestion):
                if custom is not None:
                    score = float(custom)
                elif q.default is not None:
                    score = q.default
                else:
                    # Toward noise / caution: high priority / high retention = max score
                    score = q.max_value

                results[q.id] = ScoreResult(
                    id=q.id,
                    score=score,
                    confidence=1.0,
                    degraded=True,
                )

            elif isinstance(q, NoulQuestion):
                if custom is not None:
                    val = bool(custom)
                elif q.default is not None:
                    val = q.default
                else:
                    # Toward noise: assume True (e.g. is_anomalous=True, should_retain=True, requires_review=True)
                    val = True

                results[q.id] = NoulResult(
                    id=q.id,
                    value=val,
                    probability=1.0 if val else 0.0,
                    confidence=1.0,
                    degraded=True,
                )

        return DecisionBatchResponse(
            results=results,
            latency_ms=latency_ms,
            degraded=True,
            error=f"Degraded Default Triggered: {reason}",
        )
