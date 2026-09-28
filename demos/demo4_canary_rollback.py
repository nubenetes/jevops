#!/usr/bin/env python3
"""
DEMO 4: Semantic Canary Progressive Delivery & Rollback.
References:
- Jev deployment state-machine (stacktoheap.com/demos/jev-deployment-state-machine)
- Jev and Temporal rollback demo (thenoahhein/jev-temporal-demo)

Demonstrates:
1. Multi-dimensional canary evaluation (error rate, p99 latency, log errors)
   rather than static thresholds.
2. Progressive promotion: 5% -> 25% -> 45%.
3. Automated rollback triggered instantly when severe degradation is detected.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "components", "04-progressive-delivery"))
from canary_state_machine import CanaryDeploymentStateMachine

def main():
    print("=" * 70)
    print(" JEVOPS DEMO 4: SEMANTIC CANARY PROGRESSIVE DELIVERY & ROLLBACK ")
    print("=" * 70)

    controller = CanaryDeploymentStateMachine()
    
    # Stage 1: 5% Initial Canary
    print("[1] Evaluating Canary Stage 1 (Traffic Weight: 5%)...")
    stage1_metrics = {"error_rate_pct": 0.05, "p99_latency_ms": 38.0, "request_count": 2500}
    stage1_logs = ["HTTP 200 OK GET /cart", "HTTP 200 OK POST /checkout/validate"]
    res1 = controller.evaluate_canary_step(5, stage1_metrics, stage1_logs)
    print(f"    - Decision:       {res1['action'].upper()}")
    print(f"    - Health Score:   {res1['health_score']:.2f} / 1.00")
    print(f"    - New Weight:     {res1['new_weight']}%")
    print(f"    - Pipeline State: {res1['state']}\n")

    # Stage 2: 25% Promoted Canary
    print(f"[2] Evaluating Canary Stage 2 (Traffic Weight: {res1['new_weight']}%)...")
    stage2_metrics = {"error_rate_pct": 0.08, "p99_latency_ms": 45.0, "request_count": 8000}
    stage2_logs = ["HTTP 200 OK GET /catalog", "HTTP 200 OK POST /orders"]
    res2 = controller.evaluate_canary_step(res1['new_weight'], stage2_metrics, stage2_logs)
    print(f"    - Decision:       {res2['action'].upper()}")
    print(f"    - Health Score:   {res2['health_score']:.2f} / 1.00")
    print(f"    - New Weight:     {res2['new_weight']}%")
    print(f"    - Pipeline State: {res2['state']}\n")

    # Stage 3: Injected Anomaly at higher traffic
    print(f"[3] Evaluating Canary Stage 3 (Traffic Weight: {res2['new_weight']}%) - Injecting DB Exhaustion...")
    bad_metrics = {"error_rate_pct": 9.2, "p99_latency_ms": 3120.0, "request_count": 15000}
    bad_logs = [
        "FATAL: Database connection pool exhausted after 3000ms timeout",
        "HTTP 500 Internal Server Error in order placement pipeline",
        "CircuitBreaker 'inventory-client' tripped OPEN",
    ]
    res3 = controller.evaluate_canary_step(res2['new_weight'], bad_metrics, bad_logs)
    print(f"    - Decision:            {res3['action'].upper()}")
    print(f"    - Health Score:        {res3['health_score']:.2f} / 1.00")
    print(f"    - Rollback Justified:  {res3['rollback_justified']}")
    print(f"    - Final Traffic Weight: {res3['new_weight']}% (Traffic isolated)")
    print(f"    - Pipeline State:      {res3['state']}\n")

    print("[✔] Conclusion: The Semantic State Machine successfully promoted healthy canary stages")
    print("    and executed immediate automated rollback upon detecting multi-signal failure!")
    print("=" * 70)

if __name__ == "__main__":
    main()
