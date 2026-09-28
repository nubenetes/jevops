"""
Jev Metrics: OpenTelemetry Metric Metadata Evaluator & Churn Reducer.
Reference: ishantanu/jevmetrics

Queries the decision model to infer operational value of metric instruments
based on metadata (name, description, unit, label keys) before history or
dashboard usage is even established.

Modes:
- annotate: Tags metrics with semantic labels without altering pipeline.
- route: Directs high-value metrics to Prometheus/Mimir and low-value to rollups.
- reduce: Drops redundant high-cardinality instruments to prevent TSDB explosions.
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


class JevMetricsProcessor:
    def __init__(self, mode: str = "annotate", client: JevClient = None):
        self.mode = mode  # "annotate", "route", or "reduce"
        self.client = client or JevClient()
        self.cache: Dict[str, Dict[str, Any]] = {}

    def process_metric(self, metric: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a metric instrument.
        metric format: {
            "name": "http_requests_total",
            "description": "Total count of HTTP requests",
            "unit": "1",
            "type": "counter",
            "attributes": {"handler": "/api/v1/checkout", "code": "500", "client_ip": "10.0.1.5"}
        }
        """
        metric_name = metric.get("name", "")
        # Check cache to minimize evaluation latency
        if metric_name in self.cache:
            return self._apply_policy(metric, self.cache[metric_name])

        desc = metric.get("description", "")
        unit = metric.get("unit", "")
        attr_keys = list(metric.get("attributes", {}).keys())

        context = (
            f"metric={metric_name} desc='{desc}' unit='{unit}' "
            f"attributes={attr_keys}"
        )

        questions = [
            ChoiceQuestion(
                id="tier",
                prompt="Categorize metric operational storage tier",
                options=["primary_tsdb", "downsample_rollup", "drop_noise"],
                default="primary_tsdb",  # John Rood rule: fail toward noise (retain)
            ),
            ScoreQuestion(
                id="cardinality_risk",
                prompt="Score cardinality explosion risk based on attributes",
                min_value=0.0,
                max_value=1.0,
                default=0.0,
            ),
            NoulQuestion(
                id="is_slo_critical",
                prompt="Is this metric critical for Service Level Objectives (SLO/SLA)?",
                default=True,
            ),
        ]

        resp = self.client.decide(context=context, questions=questions)

        tier_res = resp.get_choice("tier")
        card_res = resp.get_score("cardinality_risk")
        slo_res = resp.get_noul("is_slo_critical")

        decision = {
            "tier": tier_res.selected if tier_res else "primary_tsdb",
            "cardinality_risk": card_res.score if card_res else 0.0,
            "is_slo_critical": slo_res.value if slo_res else True,
            "confidence": tier_res.confidence if tier_res else 1.0,
            "degraded": resp.degraded,
        }

        self.cache[metric_name] = decision
        return self._apply_policy(metric, decision)

    def _apply_policy(self, metric: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(metric)
        attrs = dict(result.get("attributes", {}))

        if self.mode == "annotate":
            attrs["jev.tier"] = decision["tier"]
            attrs["jev.slo_critical"] = str(decision["is_slo_critical"])
            attrs["jev.cardinality_risk"] = f"{decision['cardinality_risk']:.2f}"
            result["attributes"] = attrs
            result["action"] = "pass"

        elif self.mode == "route":
            result["target_destination"] = decision["tier"]
            result["action"] = "route"

        elif self.mode == "reduce":
            # If high cardinality risk and not SLO critical, sanitize high-cardinality attributes
            if decision["cardinality_risk"] > 0.7 and not decision["is_slo_critical"]:
                for volatile_key in ["client_ip", "user_id", "session_id", "container_id"]:
                    attrs.pop(volatile_key, None)
                attrs["jev.reduced"] = "true"
                result["attributes"] = attrs
            result["action"] = "pass"

        return result


if __name__ == "__main__":
    proc = JevMetricsProcessor(mode="annotate")
    sample_metric = {
        "name": "jvm_memory_pool_bytes_used",
        "description": "Used bytes in JVM memory pool",
        "unit": "By",
        "type": "gauge",
        "attributes": {"pool": "G1 Old Gen", "service": "payment-api"},
    }
    print("Metrics Processor Output:", proc.process_metric(sample_metric))
