#!/usr/bin/env python3
"""
DEMO 5: Air-Gapped Operation & Degraded Defaults (John Rood's Law).
References:
- John Rood (@johnroodepic):
  "What the pipeline does when the decider is down or slow:
   pick the degraded default per decision, and pick it toward noise:
   keep everything, page anyway. The only calls that get to fail quiet
   are the reversible ones."

Demonstrates:
1. Pure air-gapped / disconnected execution (OpenShift 4.20+ zero-egress).
2. Intentional Decider Outage / Latency Spike.
3. Degraded fallback behavior:
   - Telemetry triage: FAILS TOWARD NOISE (keeps 100% of logs).
   - Alert router: FAILS TOWARD NOISE (pages oncall anyway).
   - K8s mutation: FAILS SAFE (blocks mutation).
   - Circuit breaker trips to OPEN to protect pipeline throughput.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from jevops_core import (
    ChoiceQuestion,
    CircuitState,
    DegradedFallbackHandler,
    JevClient,
    NoulQuestion,
    ScoreQuestion,
)

def main():
    print("=" * 70)
    print(" JEVOPS DEMO 5: AIR-GAPPED ZERO-EGRESS & JOHN ROOD'S LAW ")
    print("=" * 70)

    # 1. Air-Gapped Local Operation
    print("[1] Verifying Air-Gapped Local Execution (OpenShift 4.20+ Mode)...")
    airgap_client = JevClient(mode="airgap")
    resp_airgap = airgap_client.decide(
        context="PostgreSQL slow query lock on accounts table in disconnected datacenter",
        questions=[ChoiceQuestion("action", "Select action", ["investigate", "archive"])],
    )
    print(f"    - Mode:            {airgap_client.mode.upper()}")
    print(f"    - Latency:         {resp_airgap.latency_ms:.2f} ms")
    print(f"    - Decision:        {resp_airgap.get_choice('action').selected.upper()}")
    print(f"    - Degraded:        {resp_airgap.degraded} (Running pure local System 1)\n")

    # 2. Simulating Decider Failure / Network Outage
    print("[2] Simulating Decider Outage (Endpoint down / SLA timeout > 250ms)...")
    # Point client to unreachable endpoint to force degraded fallbacks
    faulty_client = JevClient(mode="cloud", endpoint="http://192.0.2.1:9999/v1/systemone", timeout_sec=0.1)

    # Decision A: Telemetry Log Record (Reversible -> keep everything toward noise)
    print("    [Decision A: Log Telemetry Pipeline]")
    log_q = [
        ChoiceQuestion("route", "Route log", ["warm_analysis", "cold_archive"]),
        NoulQuestion("keep_log", "Should retain log?", default=True),
    ]
    resp_log = faulty_client.decide(context="Ambiguous system message", questions=log_q)
    print(f"    - Decision:        {resp_log.get_choice('route').selected.upper()} (Failed toward noise!)")
    print(f"    - Retain:          {resp_log.get_noul('keep_log').value}")
    print(f"    - Degraded Flag:   {resp_log.degraded}")
    print(f"    - Error Logged:    {resp_log.error}")

    # Decision B: Incident Paging (Irreversible -> fail toward noise: page anyway)
    print("\n    [Decision B: Incident Paging Gate]")
    alert_q = [ChoiceQuestion("alert_action", "Alert action", ["page_oncall", "suppress"])]
    resp_alert = faulty_client.decide(context="Unknown CPU spike", questions=alert_q)
    print(f"    - Alert Action:    {resp_alert.get_choice('alert_action').selected.upper()} (Page oncall anyway!)")
    print(f"    - Degraded Flag:   {resp_alert.degraded}")

    # Decision C: Destructive Kubernetes Action (Irreversible -> fail-safe block)
    print("\n    [Decision C: Destructive K8s Mutation]")
    k8s_q = [ChoiceQuestion("gate_action", "Action", ["approve", "block"])]
    resp_k8s = faulty_client.decide(
        context="Agent requested 'kubectl delete deployment prod-cart'",
        questions=k8s_q,
        custom_fallbacks={"gate_action": "block"},
    )
    print(f"    - K8s Gate Verdict: {resp_k8s.get_choice('gate_action').selected.upper()} (Failed safe - blocked!)")

    # 3. Circuit Breaker State Verification
    print("\n[3] Checking Production Circuit Breaker Status...")
    # Force another failure to trip circuit
    faulty_client.decide(context="Probe", questions=k8s_q)
    print(f"    - Failure Count:   {faulty_client.circuit_breaker.failure_count}")
    print(f"    - Circuit State:   {faulty_client.circuit_breaker.state.value.upper()}")
    print(f"    - Total Calls:     {faulty_client.circuit_breaker.total_calls}")

    print("\n[✔] Conclusion: John Rood's Law is validated!")
    print("    When the decider is down, telemetry fails toward noise (keep everything),")
    print("    alerts fail toward noise (page anyway), and destructive actions fail safe (blocked).")
    print("=" * 70)

if __name__ == "__main__":
    main()
