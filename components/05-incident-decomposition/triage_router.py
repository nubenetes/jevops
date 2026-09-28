"""
Incident Response Decomposition: Confidence-Gated Alert Triager & Router.
References:
- jev-oncall (jevcases.com/cases/jev-oncall)
- typesafe-jev-incident-router (kyle-chalmers/typesafe-jev-incident-router)

Instead of treating incident response as one giant monolithic AI problem,
decompose into discrete, confidence-gated micro-decisions:
1. Is this a true operational incident?
2. Does it warrant waking an oncall engineer (page vs review queue)?
3. Which team owns this component?
If confidence is below threshold, routes safely to a human triage queue.
"""

import sys
import os
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))
from jevops_core import (
    ChoiceQuestion,
    JevClient,
    NoulQuestion,
    ScoreQuestion,
)


class IncidentTriageRouter:
    # Deterministic ownership mapping
    EXACT_OWNERS = {
        "checkout-api": "Team Payments",
        "cart-service": "Team Ordering",
        "auth-proxy": "Team Security",
        "kube-apiserver": "Team Platform Infrastructure",
    }

    def __init__(self, confidence_threshold: float = 0.75, client: JevClient = None):
        self.threshold = confidence_threshold
        self.client = client or JevClient()

    def process_alert(self, alert_payload: Dict[str, Any]) -> Dict[str, Any]:
        service = alert_payload.get("service", "")
        summary = alert_payload.get("summary", "")
        severity = alert_payload.get("severity", "warning")
        fired_at = alert_payload.get("timestamp", "")

        # 1. Exact lookup first
        team_owner = self.EXACT_OWNERS.get(service)

        teams_list = [
            "Team Payments",
            "Team Ordering",
            "Team Security",
            "Team Platform Infrastructure",
            "Team Data Engineering",
        ]

        context = (
            f"ALERT: {summary}\n"
            f"SERVICE: {service}\n"
            f"SEVERITY: {severity}\n"
            f"METRIC_DETAILS: {alert_payload.get('details', {})}"
        )

        questions = [
            NoulQuestion(
                id="is_real_incident",
                prompt="Is this a genuine production impairment requiring investigation?",
                default=True,
            ),
            ChoiceQuestion(
                id="action",
                prompt="Determine paging and escalation action",
                options=["page_oncall_now", "enqueue_review", "suppress_flapping"],
                default="page_oncall_now",  # John Rood: fail toward noise (page anyway)
            ),
        ]

        if not team_owner:
            questions.append(
                ChoiceQuestion(
                    id="routed_team",
                    prompt="Which engineering team is responsible for resolving this issue?",
                    options=teams_list,
                    default=teams_list[0],
                )
            )

        resp = self.client.decide(context=context, questions=questions)

        is_real = resp.get_noul("is_real_incident")
        action = resp.get_choice("action")
        team_choice = resp.get_choice("routed_team")

        if not team_owner and team_choice:
            if team_choice.confidence >= self.threshold:
                team_owner = team_choice.selected
            else:
                team_owner = "Unassigned / Human Triage Queue"

        return {
            "service": service,
            "is_real_incident": is_real.value if is_real else True,
            "action": action.selected if action else "page_oncall_now",
            "assigned_team": team_owner,
            "confidence": action.confidence if action else 1.0,
            "degraded": resp.degraded,
            "latency_ms": resp.latency_ms,
        }


if __name__ == "__main__":
    router = IncidentTriageRouter()
    sample = {
        "service": "billing-webhook-listener",
        "summary": "Stripe webhook signature validation failing continuously, 401 Unauthorized spike",
        "severity": "critical",
    }
    print("Alert Triage & Route Output:\n", router.process_alert(sample))
