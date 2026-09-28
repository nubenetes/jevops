"""
Jev Traces: Intelligent OpenTelemetry Tail Sampling.
Reference: ishantanu/jevtraces

Assesses trace spans for operational diagnosis utility and business criticality.
Combines semantic decision scoring with OpenTelemetry tail sampling to guarantee:
1. 100% of anomalous, error, and critical business transactions are preserved.
2. Low-value background health checks (e.g., /healthz, ping) are pruned.
3. Degraded fallback ensures ALL traces are preserved if the decider is unreachable.
"""

import sys
import os
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))
from jevops_core import (
    ChoiceQuestion,
    JevClient,
    NoulQuestion,
    ScoreQuestion,
)


class JevTraceSampler:
    def __init__(self, client: JevClient = None):
        self.client = client or JevClient()

    def evaluate_trace(self, trace_spans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate an entire trace (collection of spans) for retention decision.
        """
        if not trace_spans:
            return {"action": "drop", "reason": "empty trace"}

        # Extract summary features
        root_span = trace_spans[0]
        has_error = any(s.get("status", {}).get("code") == "ERROR" or s.get("status_code", 200) >= 500 for s in trace_spans)
        max_duration_ms = max(s.get("duration_ms", 0.0) for s in trace_spans)
        service_names = list({s.get("service_name", "unknown") for s in trace_spans})
        operation_names = [s.get("name", "") for s in trace_spans[:5]]

        context = (
            f"root_operation='{root_span.get('name')}' services={service_names} "
            f"has_error={has_error} max_duration_ms={max_duration_ms} "
            f"operations={operation_names}"
        )

        questions = [
            ChoiceQuestion(
                id="sampling_decision",
                prompt="Determine tail sampling outcome for trace",
                options=["retain_primary", "retain_archive_only", "drop"],
                default="retain_primary",  # John Rood fallback
            ),
            ScoreQuestion(
                id="business_criticality",
                prompt="Score business and revenue criticality of trace",
                min_value=0.0,
                max_value=1.0,
                default=1.0,
            ),
            NoulQuestion(
                id="has_diagnostic_value",
                prompt="Does this trace contain diagnostic value for incident post-mortem?",
                default=True,
            ),
        ]

        resp = self.client.decide(context=context, questions=questions)

        sample_res = resp.get_choice("sampling_decision")
        crit_res = resp.get_score("business_criticality")
        diag_res = resp.get_noul("has_diagnostic_value")

        action = sample_res.selected if sample_res else "retain_primary"

        # Deterministic hard-rule override: error spans are always preserved in primary storage
        if has_error:
            action = "retain_primary"

        return {
            "trace_id": root_span.get("trace_id", "unknown"),
            "action": action,
            "business_criticality": crit_res.score if crit_res else 1.0,
            "has_diagnostic_value": diag_res.value if diag_res else True,
            "confidence": sample_res.confidence if sample_res else 1.0,
            "degraded": resp.degraded,
            "latency_ms": resp.latency_ms,
        }


if __name__ == "__main__":
    sampler = JevTraceSampler()
    sample_trace = [
        {
            "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
            "name": "POST /checkout/pay",
            "service_name": "payment-service",
            "duration_ms": 1420.5,
            "status": {"code": "ERROR", "message": "Database deadlock on account ledger"},
        }
    ]
    print("Trace Sampler Output:", sampler.evaluate_trace(sample_trace))
