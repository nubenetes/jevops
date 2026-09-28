"""
Unified Resilient Decision Client for JevOps.

Supports:
- Cloud mode (TypeSafe API endpoint)
- Air-gapped mode (Local decision container or in-process LocalDecisionEngine)
- Automatic circuit breaking & degraded defaults (John Rood's Law)
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Union
from .fallback import CircuitBreaker, DegradedFallbackHandler
from .local_engine import LocalDecisionEngine
from .primitives import (
    ChoiceQuestion,
    ChoiceResult,
    DecisionBatchRequest,
    DecisionBatchResponse,
    DecisionQuestion,
    NoulQuestion,
    NoulResult,
    ScoreQuestion,
    ScoreResult,
)


class JevClient:
    """
    Resilient Decision Model Client for Cloud-Native and Air-Gapped DevOps.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        mode: Optional[str] = None,  # "cloud", "airgap", or "mock"
        timeout_sec: float = 0.5,     # 500ms default SLA
        latency_sla_ms: float = 250.0,
        max_failures: int = 3,
        circuit_reset_sec: float = 10.0,
    ):
        self.api_key = api_key or os.getenv("TYPESAFE_API_KEY", "")
        self.endpoint = endpoint or os.getenv("TYPESAFE_ENDPOINT", "https://api.typesafe.ai/v1/systemone")
        
        # Determine mode: default to airgap if in airgap env or no api key
        env_mode = os.getenv("JEVOPS_MODE", "").lower()
        if mode:
            self.mode = mode.lower()
        elif env_mode:
            self.mode = env_mode
        elif not self.api_key or os.getenv("AIRGAPPED", "").lower() in ("true", "1", "yes"):
            self.mode = "airgap"
        else:
            self.mode = "cloud"

        self.timeout_sec = timeout_sec
        self.circuit_breaker = CircuitBreaker(
            max_failures=max_failures,
            latency_sla_ms=latency_sla_ms,
            reset_timeout_sec=circuit_reset_sec,
        )
        self.local_engine = LocalDecisionEngine()

    def decide(
        self,
        context: Union[str, Dict[str, Any]],
        questions: List[DecisionQuestion],
        custom_fallbacks: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DecisionBatchResponse:
        """
        Execute a batch of decision questions against unstructured context.
        """
        request = DecisionBatchRequest(
            context=context,
            questions=questions,
            metadata=metadata or {},
        )

        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            return DegradedFallbackHandler.resolve_degraded_response(
                request=request,
                reason="Circuit Breaker OPEN - failing toward noise",
                custom_fallbacks=custom_fallbacks,
            )

        start_time = time.perf_counter()

        # Airgap mode: in-process local engine or local sidecar URL
        if self.mode == "airgap":
            # If endpoint is custom local http server (e.g. sidecar), try HTTP first
            if self.endpoint.startswith("http://") or self.endpoint.startswith("https://"):
                if "api.typesafe.ai" not in self.endpoint:
                    try:
                        resp = self._http_call(request)
                        latency_ms = (time.perf_counter() - start_time) * 1000.0
                        self.circuit_breaker.record_success(latency_ms)
                        return resp
                    except Exception as e:
                        # Fallback to in-process local engine if sidecar is unreachable
                        pass
            
            # In-process execution (ideal for air-gapped container workloads)
            resp = self.local_engine.execute_batch(request)
            self.circuit_breaker.record_success(resp.latency_ms)
            return resp

        # Cloud mode: remote HTTPS call
        try:
            resp = self._http_call(request)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.circuit_breaker.record_success(latency_ms)
            return resp
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.circuit_breaker.record_failure(str(e))
            
            # When remote fails, attempt local engine fallback before falling back to degraded defaults
            try:
                local_resp = self.local_engine.execute_batch(request)
                local_resp.error = f"Cloud failed ({e}); used local engine fallback."
                return local_resp
            except Exception:
                return DegradedFallbackHandler.resolve_degraded_response(
                    request=request,
                    reason=f"Decider error: {e}",
                    latency_ms=latency_ms,
                    custom_fallbacks=custom_fallbacks,
                )

    def _http_call(self, request: DecisionBatchRequest) -> DecisionBatchResponse:
        data = json.dumps(request.to_dict()).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "jevops-client/0.1.0 (CloudNative)",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(self.endpoint, data=data, headers=headers, method="POST")
        start = time.perf_counter()
        
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as response:
            latency_ms = (time.perf_counter() - start) * 1000.0
            body = response.read().decode("utf-8")
            payload = json.loads(body)

        results: Dict[str, Any] = {}
        for q in request.questions:
            res_dict = payload.get("results", {}).get(q.id, {})
            if isinstance(q, ChoiceQuestion):
                results[q.id] = ChoiceResult(
                    id=q.id,
                    selected=res_dict.get("selected", q.options[0]),
                    confidence=float(res_dict.get("confidence", 0.9)),
                    probabilities=res_dict.get("probabilities", {}),
                    degraded=False,
                )
            elif isinstance(q, ScoreQuestion):
                results[q.id] = ScoreResult(
                    id=q.id,
                    score=float(res_dict.get("score", q.min_value)),
                    confidence=float(res_dict.get("confidence", 0.9)),
                    degraded=False,
                )
            elif isinstance(q, NoulQuestion):
                results[q.id] = NoulResult(
                    id=q.id,
                    value=bool(res_dict.get("value", True)),
                    probability=float(res_dict.get("probability", 1.0)),
                    confidence=float(res_dict.get("confidence", 0.9)),
                    degraded=False,
                )

        return DecisionBatchResponse(
            results=results,
            latency_ms=round(latency_ms, 2),
            degraded=False,
            error=None,
        )
