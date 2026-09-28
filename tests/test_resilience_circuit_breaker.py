import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from jevops_core import (
    CircuitBreaker,
    CircuitState,
    DegradedFallbackHandler,
    DecisionBatchRequest,
    ChoiceQuestion,
    NoulQuestion,
    ScoreQuestion,
)

class TestResilienceCircuitBreaker(unittest.TestCase):
    def test_circuit_breaker_state_transitions(self):
        cb = CircuitBreaker(max_failures=2, latency_sla_ms=250.0, reset_timeout_sec=0.1)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())

        # Record 1 failure
        cb.record_failure("error 1")
        self.assertEqual(cb.state, CircuitState.CLOSED)

        # Record 2nd failure -> trips OPEN
        cb.record_failure("error 2")
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.can_execute())

    def test_john_rood_fail_toward_noise(self):
        req = DecisionBatchRequest(
            context="System alert",
            questions=[
                ChoiceQuestion("log_action", "Action", ["warm_analysis", "cold_archive"]),
                NoulQuestion("page_oncall", "Page?"),
                ScoreQuestion("retention_score", "Score"),
            ]
        )
        resp = DegradedFallbackHandler.resolve_degraded_response(req, reason="Simulated Outage")
        self.assertTrue(resp.degraded)
        self.assertTrue(resp.get_noul("page_oncall").value)
        self.assertEqual(resp.get_score("retention_score").score, 1.0)

if __name__ == "__main__":
    unittest.main()
