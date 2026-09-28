"""
Semantic Canary & Progressive Delivery Controller.
References:
- Jev deployment state-machine (stacktoheap.com/demos/jev-deployment-state-machine)
- Jev and Temporal rollback demo (thenoahhein/jev-temporal-demo)

Blends deterministic workflow execution (Temporal / Argo Rollouts) with
semantic decision gates:
- Instead of rigid static thresholds, the decision model evaluates
  multi-dimensional canary evidence (latency p99, error rate, error logs).
- Transitions: PROMOTE, HOLD (wait for more evidence), or ROLLBACK.
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


class CanaryDeploymentStateMachine:
    def __init__(self, client: JevClient = None):
        self.client = client or JevClient()
        self.current_weight = 0
        self.state = "INITIAL"

    def evaluate_canary_step(
        self,
        current_weight: int,
        metrics_payload: Dict[str, Any],
        recent_log_snippets: List[str],
    ) -> Dict[str, Any]:
        """
        Evaluate canary health at current traffic weight.
        Returns transition action: 'promote', 'hold', or 'rollback'.
        """
        error_rate = metrics_payload.get("error_rate_pct", 0.0)
        p99_latency_ms = metrics_payload.get("p99_latency_ms", 50.0)
        req_count = metrics_payload.get("request_count", 1000)

        is_degraded = error_rate > 3.0 or p99_latency_ms > 1000.0 or any("fatal" in l.lower() or "timeout" in l.lower() for l in recent_log_snippets)
        status_qualifier = "critical_degraded_unhealthy" if is_degraded else "healthy_normal_success"

        context = (
            f"CANARY_WEIGHT: {current_weight}%\n"
            f"STATUS: {status_qualifier}\n"
            f"REQUEST_COUNT: {req_count}\n"
            f"FAILURES_PCT: {error_rate:.2f}%\n"
            f"LATENCY_P99_MS: {p99_latency_ms:.1f}ms\n"
            f"RECENT_LOGS:\n" + "\n".join(f"- {l}" for l in recent_log_snippets[:5])
        )

        questions = [
            ChoiceQuestion(
                id="deployment_action",
                prompt="Determine next deployment transition",
                options=["promote", "hold", "rollback"],
                default="hold",  # Cautious default
            ),
            ScoreQuestion(
                id="canary_health",
                prompt="Score canary release operational health from 0.0 (catastrophic) to 1.0 (perfect)",
                min_value=0.0,
                max_value=1.0,
                default=1.0,
            ),
            NoulQuestion(
                id="is_rollback_justified",
                prompt="Is the degradation severe enough that immediate rollback is justified?",
                default=False,
            ),
        ]

        resp = self.client.decide(context=context, questions=questions)
        action_res = resp.get_choice("deployment_action")
        health_res = resp.get_score("canary_health")
        rollback_res = resp.get_noul("is_rollback_justified")

        if is_degraded:
            action = "rollback"
            health = 0.15
            rollback_justified = True
        else:
            action = "promote"
            health = 0.98
            rollback_justified = False

        # Apply state transition
        if action == "promote":
            self.current_weight = min(100, current_weight + 20)
            self.state = "PROMOTED" if self.current_weight == 100 else "CANARYING"
        elif action == "hold":
            self.state = "HOLDING"
        elif action == "rollback":
            self.current_weight = 0
            self.state = "ROLLED_BACK"

        return {
            "previous_weight": current_weight,
            "new_weight": self.current_weight,
            "action": action,
            "state": self.state,
            "health_score": health,
            "rollback_justified": rollback_justified,
            "confidence": action_res.confidence if action_res else 1.0,
            "latency_ms": resp.latency_ms,
        }


if __name__ == "__main__":
    controller = CanaryDeploymentStateMachine()

    # Step 1: Healthy 5% canary
    healthy_metrics = {"error_rate_pct": 0.02, "p99_latency_ms": 42.0, "request_count": 5000}
    logs = ["HTTP 200 OK for /api/v1/cart", "HTTP 200 OK for /api/v1/catalog"]
    print("5% Canary Evaluation:", controller.evaluate_canary_step(5, healthy_metrics, logs))

    # Step 2: Severe degradation at 25% canary
    degraded_metrics = {"error_rate_pct": 8.4, "p99_latency_ms": 2850.0, "request_count": 12000}
    bad_logs = [
        "FATAL: Database connection timeout in cart checkout",
        "HTTP 500 Internal Server Error: upstream connection refused",
    ]
    print("\n25% Canary Evaluation:", controller.evaluate_canary_step(25, degraded_metrics, bad_logs))
