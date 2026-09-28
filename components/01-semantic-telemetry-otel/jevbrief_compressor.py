"""
JevBrief: Operational Context Compressor & Incident Synthesizer.
Reference: jevbrief (PyPI: jevbrief/0.1.0)

DevOps incidents flood operators and LLMs with thousands of repetitive log lines.
JevBrief compresses massive operational context:
1. Clusters thousands of raw log records into distinct semantic clusters.
2. Identifies top candidate root causes.
3. Uses Jev to select the single best explanatory hypothesis in <100ms.
"""

import hashlib
import re
import sys
import os
from collections import defaultdict
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))
from jevops_core import (
    ChoiceQuestion,
    JevClient,
    ScoreQuestion,
)


class JevBriefCompressor:
    def __init__(self, client: JevClient = None):
        self.client = client or JevClient()

    def _fingerprint_log(self, message: str) -> str:
        """Strip variable tokens (UUIDs, IPs, timestamps, numbers) to form cluster template."""
        clean = re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", "<UUID>", message)
        clean = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<IP>", clean)
        clean = re.sub(r"\b\d+\b", "<NUM>", clean)
        return clean.strip()

    def cluster_logs(self, raw_logs: List[str]) -> List[Dict[str, Any]]:
        """Cluster raw logs into semantic templates."""
        clusters = defaultdict(list)
        for log in raw_logs:
            fp = self._fingerprint_log(log)
            clusters[fp].append(log)

        sorted_clusters = sorted(
            [{"template": k, "count": len(v), "samples": v[:2]} for k, v in clusters.items()],
            key=lambda c: c["count"],
            reverse=True,
        )
        return sorted_clusters

    def explain_incident(self, incident_title: str, raw_logs: List[str]) -> Dict[str, Any]:
        """
        Compresses logs into clusters and queries Jev to identify primary root explanation.
        """
        # Step 1: Cluster logs (e.g. 1,447 logs -> clusters)
        clusters = self.cluster_logs(raw_logs)

        # Step 2: Extract top candidate explanations (up to 5)
        candidates = []
        for i, c in enumerate(clusters[:5]):
            cand_id = f"candidate_{i+1}"
            candidates.append((cand_id, f"[{c['count']} occurrences] {c['template']}"))

        if not candidates:
            return {"error": "No log records provided"}

        options = [c[0] for c in candidates]
        candidate_summary = "\n".join([f"{c[0]}: {c[1]}" for c in candidates])

        context = (
            f"INCIDENT: {incident_title}\n"
            f"CLUSTERED LOG EVIDENCE ({len(raw_logs)} raw records clustered into {len(clusters)} patterns):\n"
            f"{candidate_summary}"
        )

        questions = [
            ChoiceQuestion(
                id="root_cause_explanation",
                prompt="Which clustered evidence candidate best explains the incident?",
                options=options,
                default=options[0],
            ),
            ScoreQuestion(
                id="evidence_sufficiency",
                prompt="Rate whether the evidence is sufficient to confirm root cause without further inspection",
                min_value=0.0,
                max_value=1.0,
                default=0.8,
            ),
        ]

        resp = self.client.decide(context=context, questions=questions)
        choice_res = resp.get_choice("root_cause_explanation")
        score_res = resp.get_score("evidence_sufficiency")

        winning_id = choice_res.selected if choice_res else options[0]
        winning_candidate = next((c[1] for c in candidates if c[0] == winning_id), "")

        return {
            "incident": incident_title,
            "raw_log_count": len(raw_logs),
            "cluster_count": len(clusters),
            "winning_candidate_id": winning_id,
            "winning_explanation": winning_candidate,
            "confidence": choice_res.confidence if choice_res else 1.0,
            "evidence_sufficiency": score_res.score if score_res else 0.8,
            "latency_ms": resp.latency_ms,
        }


if __name__ == "__main__":
    compressor = JevBriefCompressor()
    # Simulate 1,447 log records dominated by routine pings and a critical database connection leak
    mock_logs = ["GET /healthz 200 OK from 10.0.2.14" for _ in range(1200)]
    mock_logs += ["Processing order batch 4829" for _ in range(200)]
    mock_logs += ["FATAL: HikariPool-1 - Connection is not available, request timed out after 30005ms" for _ in range(47)]

    summary = compressor.explain_incident("Checkout Service 503 Outage", mock_logs)
    print("JevBrief Incident Explanation:\n", summary)
