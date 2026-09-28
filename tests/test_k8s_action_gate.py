import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "components", "02-k8s-semantic-action-gate"))
from gatekeeper_evaluator import SemanticActionGate

class TestK8sActionGate(unittest.TestCase):
    def test_action_gate_blocks_wide_policy(self):
        gate = SemanticActionGate()
        incident = "Pod cart timeout connecting to billing"
        bad_policy = {
            "kind": "NetworkPolicy",
            "spec": {
                "podSelector": {},
                "ingress": [{"from": [{"ipBlock": {"cidr": "0.0.0.0/0"}}], "ports": [{"port": 5432}]}],
            }
        }
        res = gate.evaluate_mutation(incident, "NetworkPolicy/bad", bad_policy)
        self.assertFalse(res["allowed"])
        self.assertTrue(res["exposes_sensitive_workload"])
        self.assertEqual(res["blast_radius"], 1.0)

    def test_action_gate_allows_scoped_policy(self):
        gate = SemanticActionGate()
        incident = "Pod cart timeout connecting to billing"
        good_policy = {
            "kind": "NetworkPolicy",
            "spec": {
                "podSelector": {"matchLabels": {"app": "billing"}},
                "ingress": [{"from": [{"podSelector": {"matchLabels": {"app": "cart"}}}], "ports": [{"port": 8080}]}],
            }
        }
        res = gate.evaluate_mutation(incident, "NetworkPolicy/good", good_policy)
        self.assertTrue(res["allowed"])
        self.assertFalse(res["exposes_sensitive_workload"])

if __name__ == "__main__":
    unittest.main()
