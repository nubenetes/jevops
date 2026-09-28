"""
Security Operations Pipeline (SecOps).
Reference: kenhuangus/jev-usecases

Applies decision models across staged security incident workflows:
1. Triage: Distinguishes between active security breaches and background internet noise.
2. Blast Radius: Scores potential exposure of sensitive customer/PII data.
3. Containment Gate: Selects safe automated containment vs human sign-off.
4. Closeout Verification: Confirms threat neutralization.
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


class SecOpsIncidentPipeline:
    def __init__(self, client: JevClient = None):
        self.client = client or JevClient()

    def evaluate_security_alert(self, alert_event: Dict[str, Any]) -> Dict[str, Any]:
        event_name = alert_event.get("event", "Unknown Alert")
        pod = alert_event.get("pod", "unknown")
        namespace = alert_event.get("namespace", "prod")
        indicators = alert_event.get("ioc_indicators", [])

        context = (
            f"SECURITY_EVENT: {event_name}\n"
            f"LOCATION: namespace={namespace} pod={pod}\n"
            f"INDICATORS: {indicators}"
        )

        questions = [
            ChoiceQuestion(
                id="containment_strategy",
                prompt="Select appropriate automated security containment strategy",
                options=["isolate_network_policy", "terminate_pod", "revoke_service_account", "observe_only"],
                default="isolate_network_policy",
            ),
            ScoreQuestion(
                id="blast_radius",
                prompt="Score data exfiltration and credential exposure risk",
                min_value=0.0,
                max_value=1.0,
                default=1.0,
            ),
            NoulQuestion(
                id="is_active_exploit",
                prompt="Is there high-confidence evidence of an active, weaponized exploit in progress?",
                default=True,
            ),
        ]

        resp = self.client.decide(context=context, questions=questions)

        contain_res = resp.get_choice("containment_strategy")
        blast_res = resp.get_score("blast_radius")
        exploit_res = resp.get_noul("is_active_exploit")

        return {
            "event": event_name,
            "target": f"{namespace}/{pod}",
            "is_active_exploit": exploit_res.value if exploit_res else True,
            "blast_radius": blast_res.score if blast_res else 1.0,
            "recommended_containment": contain_res.selected if contain_res else "isolate_network_policy",
            "confidence": contain_res.confidence if contain_res else 1.0,
            "latency_ms": resp.latency_ms,
        }


if __name__ == "__main__":
    pipeline = SecOpsIncidentPipeline()
    sample_alert = {
        "event": "Falco Runtime Alert: Outbound connection to known Tor exit node from container bash shell",
        "pod": "frontend-web-6d9b-x82m",
        "namespace": "ecommerce-prod",
        "ioc_indicators": ["IP 185.220.101.5", "Exec /bin/bash", "Curl download to /tmp/xmrig"],
    }
    print("SecOps Pipeline Assessment:\n", pipeline.evaluate_security_alert(sample_alert))
