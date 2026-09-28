import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from jevops_core import (
    LocalDecisionEngine,
    DecisionBatchRequest,
    ChoiceQuestion,
    ScoreQuestion,
    NoulQuestion,
)

class TestAirgapLocalEngine(unittest.TestCase):
    def test_local_engine_batch_execution(self):
        engine = LocalDecisionEngine()
        req = DecisionBatchRequest(
            context="Database deadlocked on row lock in PostgreSQL pod",
            questions=[
                ChoiceQuestion("action", "Action", ["investigate", "archive"]),
                ScoreQuestion("severity", "Severity", min_value=0.0, max_value=1.0),
                NoulQuestion("is_critical", "Is critical failure?"),
            ]
        )
        resp = engine.execute_batch(req)
        self.assertFalse(resp.degraded)
        self.assertGreaterEqual(resp.latency_ms, 0.0)
        self.assertEqual(resp.get_choice("action").selected, "investigate")
        self.assertTrue(resp.get_noul("is_critical").value)
        self.assertGreater(resp.get_score("severity").score, 0.5)

if __name__ == "__main__":
    unittest.main()
