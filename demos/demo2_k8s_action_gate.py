#!/usr/bin/env python3
"""
DEMO 2: Kubernetes Semantic Action Gate.
Reference: dsh-jev (DeepSeek Harness)

Demonstrates runtime safety gating on autonomous SRE agent mutations:
- Scenario: Agent attempts to fix microservice network timeout.
- Attempt 1: Overly broad NetworkPolicy (0.0.0.0/0 ingress) exposing PostgreSQL (port 5432) -> BLOCKED.
- Attempt 2: Properly scoped Pod-to-Pod NetworkPolicy -> APPROVED.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "components", "02-k8s-semantic-action-gate"))
from gatekeeper_evaluator import SemanticActionGate

def main():
    print("=" * 70)
    print(" JEVOPS DEMO 2: KUBERNETES SEMANTIC ACTION GATE ")
    print("=" * 70)

    gate = SemanticActionGate()
    incident_context = (
        "Incident #4092: Cart microservice experiencing intermittent HTTP 504 timeouts "
        "when communicating with billing-service pod over internal Kubernetes ClusterIP."
    )

    print(f"[*] Active Incident Context:\n    \"{incident_context}\"\n")

    # Attempt 1: Over-permissive, dangerous remediation
    print("[1] Autonomous Agent proposes Action 1: Wide NetworkPolicy...")
    action1 = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {"name": "fix-cart-network", "namespace": "prod"},
        "spec": {
            "podSelector": {},  # Catches all pods including Postgres & Secrets!
            "ingress": [
                {
                    "from": [{"ipBlock": {"cidr": "0.0.0.0/0"}}],
                    "ports": [{"port": 5432, "protocol": "TCP"}],  # Exposes Database!
                }
            ],
            "policyTypes": ["Ingress"],
        },
    }

    result1 = gate.evaluate_mutation(incident_context, "NetworkPolicy/fix-cart-network", action1)
    print(f"    - Decision:          {result1['decision'].upper()}")
    print(f"    - Allowed:           {result1['allowed']}")
    print(f"    - Blast Radius:      {result1['blast_radius']:.2f} / 1.00")
    print(f"    - Exposes Sensitive: {result1['exposes_sensitive_workload']}")
    print(f"    - Admission Verdict: {result1['reason']}\n")

    # Attempt 2: Scoped, secure remediation
    print("[2] Autonomous Agent proposes Action 2: Scoped Pod-to-Pod Policy...")
    action2 = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {"name": "allow-cart-to-billing", "namespace": "prod"},
        "spec": {
            "podSelector": {"matchLabels": {"app": "billing-service"}},
            "ingress": [
                {
                    "from": [
                        {"podSelector": {"matchLabels": {"app": "cart"}}}
                    ],
                    "ports": [{"port": 8080, "protocol": "TCP"}],
                }
            ],
            "policyTypes": ["Ingress"],
        },
    }

    result2 = gate.evaluate_mutation(incident_context, "NetworkPolicy/allow-cart-to-billing", action2)
    print(f"    - Decision:          {result2['decision'].upper()}")
    print(f"    - Allowed:           {result2['allowed']}")
    print(f"    - Blast Radius:      {result2['blast_radius']:.2f} / 1.00")
    print(f"    - Exposes Sensitive: {result2['exposes_sensitive_workload']}")
    print(f"    - Admission Verdict: {result2['reason']}\n")

    print("[✔] Conclusion: The Semantic Gate prevented an accidental production vulnerability")
    print("    while authorizing the safe, targeted remediation without slowing down operations!")
    print("=" * 70)

if __name__ == "__main__":
    main()
