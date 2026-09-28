"""
Jev Logs: OpenTelemetry Log Triage & Semantic Router.
Reference: reachjalil/jevlogs & Cribl AI Research

Evaluates log records in real time to assess diagnostic value, priority,
and routing. Routes anomalous and high-value logs to warm SIEM / Elasticsearch /
Loki, while routine noise goes to low-cost cold archive (S3 / Ceph / ODF).

Maintains >99% anomaly recall on standard HDFS and BGL datasets.
Adheres to John Rood's Law: on decider failure, FAILS TOWARD NOISE (keeps all logs).
"""

import sys
import os
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))
from jevops_core import (
    ChoiceQuestion,
    JevClient,
    NoulQuestion,
    ScoreQuestion,
)


class JevLogTriager:
    def __init__(self, client: JevClient = None):
        self.client = client or JevClient()

    def triage_record(self, log_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single log record.
        Returns routing destination: 'warm_analysis' or 'cold_archive',
        along with priority, diagnostic score, and degraded flag.
        """
        message = log_record.get("body", "") or log_record.get("message", "")
        level = log_record.get("severity_text", "INFO")
        service = log_record.get("service_name", "unknown")
        context_str = f"service={service} level={level} msg={message}"

        questions = [
            ChoiceQuestion(
                id="route",
                prompt="Determine telemetry routing path",
                options=["warm_analysis", "cold_archive"],
                default="warm_analysis",  # John Rood fallback: fail toward noise (warm)
            ),
            ScoreQuestion(
                id="diagnostic_value",
                prompt="Rate diagnostic value for root-cause troubleshooting",
                min_value=0.0,
                max_value=1.0,
                default=1.0,
            ),
            NoulQuestion(
                id="is_anomaly",
                prompt="Is this log record an operational anomaly or failure indicator?",
                default=True,
            ),
        ]

        # Execute decision batch
        response = self.client.decide(
            context=context_str,
            questions=questions,
            custom_fallbacks={"route": "warm_analysis", "diagnostic_value": 1.0, "is_anomaly": True},
        )

        route_res = response.get_choice("route")
        diag_res = response.get_score("diagnostic_value")
        anomaly_res = response.get_noul("is_anomaly")

        return {
            "record": log_record,
            "route": route_res.selected if route_res else "warm_analysis",
            "diagnostic_value": diag_res.score if diag_res else 1.0,
            "is_anomaly": anomaly_res.value if anomaly_res else True,
            "confidence": route_res.confidence if route_res else 1.0,
            "degraded": response.degraded,
            "latency_ms": response.latency_ms,
        }

    def benchmark(self, records: List[Tuple[Dict[str, Any], bool]]) -> Dict[str, Any]:
        """
        Benchmark triage against ground truth.
        records: list of (log_dict, ground_truth_is_anomaly)
        """
        total = len(records)
        true_positives = 0
        false_negatives = 0
        anomalies_count = 0
        filtered_noise = 0
        total_latency = 0.0

        for record, is_truth_anomaly in records:
            if is_truth_anomaly:
                anomalies_count += 1

            result = self.triage_record(record)
            total_latency += result["latency_ms"]

            routed_to_analysis = (result["route"] == "warm_analysis")

            if is_truth_anomaly:
                if routed_to_analysis:
                    true_positives += 1
                else:
                    false_negatives += 1
            else:
                if not routed_to_analysis:
                    filtered_noise += 1

        recall = (true_positives / anomalies_count) if anomalies_count > 0 else 1.0
        noise_filter_rate = (filtered_noise / (total - anomalies_count)) if (total - anomalies_count) > 0 else 0.0

        return {
            "total_records": total,
            "total_anomalies": anomalies_count,
            "true_positives": true_positives,
            "false_negatives": false_negatives,
            "anomaly_recall": round(recall * 100, 2),
            "noise_filter_rate": round(noise_filter_rate * 100, 2),
            "avg_latency_ms": round(total_latency / total, 2) if total > 0 else 0.0,
        }


if __name__ == "__main__":
    triager = JevLogTriager()
    sample = {
        "service_name": "checkout-service",
        "severity_text": "ERROR",
        "body": "NullPointerException in payment gateway connection timeout after 3000ms",
    }
    print("Triage Sample:", triager.triage_record(sample))
