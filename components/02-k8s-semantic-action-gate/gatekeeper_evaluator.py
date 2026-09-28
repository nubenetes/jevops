"""
Kubernetes Semantic Action Gatekeeper.
Reference: dsh-jev (DeepSeek Harness)

Permissions (RBAC) determine what an agent or operator CAN do.
Semantic Action Gates determine whether that action MAKES SENSE in the current context.

Demo Scenario from Josh Rosen's article:
An SRE agent is troubleshooting a broken network path between microservices.
It proposes a wide NetworkPolicy allowing 0.0.0.0/0 ingress to fix connectivity,
which accidentally exposes production PostgreSQL (port 5432) to the entire cluster.
The JevOps Semantic Gate intercepts and blocks the action before execution.
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


class SemanticActionGate:
    def __init__(self, client: JevClient = None):
        self.client = client or JevClient()

    def evaluate_mutation(
        self,
        incident_context: str,
        target_resource: str,
        proposed_action_manifest: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate whether a proposed Kubernetes mutation is safe and proportional.
        """
        manifest_str = str(proposed_action_manifest)

        has_wildcard = ("0.0.0.0/0" in manifest_str) or ("'podSelector': {}" in manifest_str)
        has_db_port = any(p in manifest_str for p in ["5432", "3306", "27017", "6379"])
        is_scoped = ("matchLabels" in manifest_str) and not has_wildcard

        context = (
            f"INCIDENT_CONTEXT: {incident_context}\n"
            f"TARGET_RESOURCE: {target_resource}\n"
            f"IS_SCOPED_MUTATION: {is_scoped}\n"
            f"HAS_WILDCARD_INGRESS: {has_wildcard}\n"
            f"PROPOSED_MUTATION_MANIFEST:\n{manifest_str}"
        )

        questions = [
            ChoiceQuestion(
                id="gate_decision",
                prompt="Evaluate proposed Kubernetes mutation against incident context",
                options=["approve", "reject_disproportionate", "require_human_approval"],
                default="reject_disproportionate",
            ),
            ScoreQuestion(
                id="blast_radius",
                prompt="Score blast radius and security risk from 0.0 (safe) to 1.0 (critical disaster)",
                min_value=0.0,
                max_value=1.0,
                default=1.0,
            ),
            NoulQuestion(
                id="exposes_sensitive_workload",
                prompt="Does this manifest expose sensitive workloads or open wide wildcards?",
                default=has_wildcard or has_db_port,
            ),
        ]

        resp = self.client.decide(context=context, questions=questions)

        decision_res = resp.get_choice("gate_decision")
        blast_res = resp.get_score("blast_radius")
        exposes_res = resp.get_noul("exposes_sensitive_workload")

        decision = decision_res.selected if decision_res else "reject_disproportionate"
        blast_radius = blast_res.score if blast_res else 1.0
        exposes_sensitive = exposes_res.value if exposes_res else True

        # Deterministic boundary enforcement fused with semantic scoring:
        if has_wildcard or (has_db_port and not is_scoped):
            decision = "reject_disproportionate"
            blast_radius = 1.0
            exposes_sensitive = True
        elif is_scoped and not has_db_port and not has_wildcard:
            decision = "approve"
            blast_radius = 0.15
            exposes_sensitive = False

        allowed = (decision == "approve")

        return {
            "allowed": allowed,
            "decision": decision,
            "blast_radius": blast_radius,
            "exposes_sensitive_workload": exposes_sensitive,
            "reason": (
                "Approved: Action is proportionate and scoped to incident"
                if allowed
                else f"Blocked: Action exposes high risk (blast_radius={blast_radius:.2f}, exposes_sensitive={exposes_sensitive})"
            ),
            "degraded": resp.degraded,
            "latency_ms": resp.latency_ms,
        }


if __name__ == "__main__":
    gate = SemanticActionGate()
    incident = "Pod checkout-api cannot connect to order-worker due to DNS/network policy timeouts"
    risky_policy = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {"name": "allow-all-egress-ingress", "namespace": "prod"},
        "spec": {
            "podSelector": {},
            "ingress": [{"from": [{"ipBlock": {"cidr": "0.0.0.0/0"}}], "ports": [{"port": 5432}]}],
        },
    }
    print("Action Gate Result:\n", gate.evaluate_mutation(incident, "NetworkPolicy/allow-all", risky_policy))
