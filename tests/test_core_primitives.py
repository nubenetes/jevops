import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from jevops_core import (
    ChoiceQuestion,
    ChoiceResult,
    ScoreQuestion,
    ScoreResult,
    NoulQuestion,
    NoulResult,
    DecisionBatchRequest,
    LocalDecisionEngine,
)

class TestCorePrimitives(unittest.TestCase):
    def test_choice_question_serialization(self):
        q = ChoiceQuestion(
            id="triage",
            prompt="Determine triage level",
            options=["p1", "p2", "p3"],
            default="p1",
        )
        d = q.to_dict()
        self.assertEqual(d["type"], "choice")
        self.assertEqual(d["id"], "triage")
        self.assertEqual(len(d["options"]), 3)
        self.assertEqual(d["default"], "p1")

    def test_score_question_bounds(self):
        q = ScoreQuestion(id="confidence", prompt="Rate confidence", min_value=0.0, max_value=5.0)
        d = q.to_dict()
        self.assertEqual(d["type"], "score")
        self.assertEqual(d["min_value"], 0.0)
        self.assertEqual(d["max_value"], 5.0)

    def test_noul_question_boolean(self):
        q = NoulQuestion(id="is_risk", prompt="Is there security risk?", default=True)
        d = q.to_dict()
        self.assertEqual(d["type"], "noul")
        self.assertTrue(d["default"])

if __name__ == "__main__":
    unittest.main()
